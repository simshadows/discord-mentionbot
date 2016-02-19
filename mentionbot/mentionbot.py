import logging
import datetime
import sys
import copy
import time
import re
import os
import traceback

import discord # pip install git+https://github.com/Rapptz/discord.py@async
# pip install git+https://github.com/Julian/jsonschema

import utils
import errors
import clientextended

from serverbotinstance import ServerBotInstance
from messagecache import MessageCache

logger = logging.getLogger('mentionbot')
logger.setLevel(logging.CRITICAL)
handler = logging.FileHandler(filename='mentionbot.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

LOGIN_DETAILS_FILENAME = "login_details" # This file is used to login. Only contains two lines. Line 1 is email, line 2 is password.

class MentionBot(clientextended.ClientExtended):
   BOTOWNER_ID = "119384097473822727"
   INITIAL_GAME_STATUS = "bot is running"
   CACHE_DIRECTORY = "cache/" # This MUST end with a forward-slash. e.g. "cache/"
   
   def __init__(self, **kwargs):
      super(MentionBot, self).__init__(**kwargs)

      print("BOTOWNER_ID = '{}'".format(MentionBot.BOTOWNER_ID))
      print("INITIAL_GAME_STATUS = '{}'".format(MentionBot.INITIAL_GAME_STATUS))
      print("CACHE_DIRECTORY = '{}'".format(MentionBot.CACHE_DIRECTORY))

      self.bot_mention = None
      self.bot_name = None
      self.botowner_mention = None
      self.botowner = None

      self._bot_instances = None
      return


   async def on_ready(self):
      self.bot_mention = "<@{}>".format(self.user.id)
      self.bot_name = self.user.name
      self.botowner_mention = "<@{}>".format(MentionBot.BOTOWNER_ID)
      self.botowner = self.search_for_user(MentionBot.BOTOWNER_ID)

      self._bot_instances = {}
      for server in self.servers:
         self._bot_instances[server] = await ServerBotInstance.get_instance(self, server)

      self.message_cache = await MessageCache.get_instance(self, self.CACHE_DIRECTORY)

      await self.set_game_status(MentionBot.INITIAL_GAME_STATUS)
      print("Bot owner: " + self.botowner.name)
      print("Bot name: " + self.bot_name)
      print("")
      print("Initialization complete.")


   async def on_message(self, msg):
      if msg.author == self.user:
         return # never process own messages.

      try:
         text = msg.content.strip()
         if isinstance(msg.channel, discord.Channel):
            await self._bot_instances[msg.server].process_text(text, msg)
            try:
               print("msg rcv #" + msg.channel.name + ": " + utils.str_asciionly(text))
            except Exception:
               print("msg rcv (CAUGHT EXCEPTION; UNKNOWN DISPLAY ERROR)")
         else: # Assumed to be a private message.
            await self.send_msg(msg, "sry m8 im not programmed to do anything fancy with pms yet")
            try:
               print("private msg rcv from" + utils.str_asciionly(msg.author.name) + ": " + utils.str_asciionly(text))
            except Exception:
               print("private msg rcv (CAUGHT EXCEPTION; UNKNOWN DISPLAY ERROR)")
      
      except errors.SilentUnknownCommandError:
         print("Caught SilentUnknownCommandError.")
      except errors.UnknownCommandError:
         print("Caught UnknownCommandError.")
         await self.send_msg(msg, "sry m8 idk what ur asking") # intentional typos. pls don't lynch me.
      except errors.InvalidCommandArgumentsError as e:
         print("Caught InvalidCommandArgumentsError.")
         if str(e) == "":
            buf = "soz m8 one or more (or 8) arguments are invalid"
         else:
            buf = str(e)
         await self.send_msg(msg, buf)
      except errors.CommandPrivilegeError:
         print("Caught CommandPrivilegeError.")
         await self.send_msg(msg, "Permission denied.")
      except errors.NoHelpContentExists:
         print("Caught NoHelpContentExists.")
         await self.send_msg(msg, "No help content exists.")
      except errors.OperationAborted:
         print("Caught OperationAborted.")
      except Exception as e:
         # This is only for feedback. Exception will continue to propagate.
         buf = "**EXCEPTION**"
         buf += "\n**From:** <#" + msg.channel.id + "> **in** " + msg.server.name
         buf += "\n**Command issued by:** <@" + msg.author.id + ">"
         buf += "\n**Full message:**"
         buf += "\n" + msg.content
         buf += "\n**Stack Trace:**"
         buf += "\n```" + traceback.format_exc() + "```"
         await self.send_msg(self.botowner, buf)
         buf = "**EXCEPTION:** " + type(e).__name__
         buf += "\n" + str(e)
         buf += "\n" + self.botowner_mention + " m8, fix this. I PM'd you the traceback."
         buf += "\n\n**THIS BOT WILL NOW TERMINATE. Please fix the bug before relaunching.**"
         await self.send_msg(msg, buf)
         sys.exit(0)
      
      return

   def get_server_bot_instance(self, server):
      return self._bot_instances[server]

# Log in to discord
client = MentionBot()
print("\nAttempting to log in using file '" + LOGIN_DETAILS_FILENAME + "'.")
if not os.path.isfile(LOGIN_DETAILS_FILENAME):
   login_file = open(LOGIN_DETAILS_FILENAME, "w")
   login_file.write("USERNAME\nPASSWORD")
   login_file.close()
   print("File does not exist. Please edit the file {} with your login details.")
   sys.exit()
login_file = open(LOGIN_DETAILS_FILENAME, "r")
email = login_file.readline().strip()
password = login_file.readline().strip()
login_file.close()
print("Email: " + email)
print("Password: " + len(password) * "*")
print("Logging in...") # print("Logging in...", end="")

try:
   client.run(email, password)
except Exception as e:
   print("Error launching client!")
   print("Details are below.\n\n")
   print(traceback.format_exc())
   print("\n\nClosing in 30 seconds.")
   time.sleep(30)
