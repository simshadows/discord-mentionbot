import asyncio
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

from . import utils, errors, clientextended

from .serverbotinstance import ServerBotInstance
from .messagecache import MessageCache

discord_logger = logging.getLogger('discord')
discord_logger.setLevel(logging.CRITICAL)
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)
handler = logging.FileHandler(filename='mentionbot.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

LOGIN_DETAILS_FILENAME = "bot_user_token" # This file is used to login. Only contains two lines. Line 1 is email, line 2 is password.

class MentionBot(clientextended.ClientExtended):
   BOTOWNER_ID = "119384097473822727"
   INITIAL_GAME_STATUS = "bot is running"
   INITIALIZING_GAME_STATUS = "bot is initializing"
   CACHE_DIRECTORY = "cache/" # This MUST end with a forward-slash. e.g. "cache/"
   
   def __init__(self, **kwargs):
      super(MentionBot, self).__init__(**kwargs)

      self.on_message_lock = asyncio.Lock()

      print("BOTOWNER_ID = '{}'".format(MentionBot.BOTOWNER_ID))
      print("INITIAL_GAME_STATUS = '{}'".format(MentionBot.INITIAL_GAME_STATUS))
      print("CACHE_DIRECTORY = '{}'".format(MentionBot.CACHE_DIRECTORY))

      self.botowner = None

      self._bot_instances = None
      return

   async def on_ready(self):
      try:
         await self.set_game_status(MentionBot.INITIALIZING_GAME_STATUS)
         self.botowner = self.search_for_user(MentionBot.BOTOWNER_ID)

         self._bot_instances = {}
         for server in self.servers:
            self._bot_instances[server] = await ServerBotInstance.get_instance(self, server)

         self.message_cache = await MessageCache.get_instance(self, self.CACHE_DIRECTORY)

         await self.set_game_status(MentionBot.INITIAL_GAME_STATUS)
         try:
            botowner = self.search_for_user(MentionBot.BOTOWNER_ID)
            print("Bot owner: " + self.botowner.name)
         except:
            print("Bot owner: (NOT FOUND. UNKNOWN ERROR.)")
            print("Bot owner ID: " + MentionBot.BOTOWNER_ID)
         print("Bot name: " + self.user.name)
         print("")
         self.on_message_lock.release()
         logging.info("MentionBot initialization complete.")
         print("Initialization complete.")
      except (SystemExit, KeyboardInterrupt):
         raise
      except BaseException as e:
         print(traceback.format_exc())
         sys.exit(1)
      return

   # General routine for uncaught exceptions from events (called by the API).
   # However, event handler routines should ideally implement their own.
   async def on_error(self, event, *args, **kwargs):
      buf = "MentionBot.on_error() called. \n\n"
      buf += "```\n" + traceback.format_exc() + "\n```"
      buf += "\nEVENT:\n" + str(event)
      buf += "\nARGS:\n"
      if len(args) == 0:
         buf += "(none)\n"
      else:
         for arg in args:
            buf += str(arg) + "\n"
      buf += "KWARGS:\n"
      if not kwargs:
         buf += "(none)\n"
      else:
         for (kwarg, item) in kwargs.items():
            buf += "{0}: {1}\n".format(str(kwarg), str(item))
      buf += "\n**Attempting to exit with code 1.**"
      print(buf, file=sys.stderr)
      try:
         await self.send_msg(self.botowner, buf)
      except:
         print("FAILED TO SEND BOTOWNER STACKTRACE.")
      logging.critical(buf)
      sys.exit(1)

   async def on_message(self, msg):
      await self.on_message_lock.acquire()
      try:
         await self._on_message(msg)
      finally:
         self.on_message_lock.release()
      return

   # TODO: Ensure this method actually lets in messages in a queued fashion...
   async def _on_message(self, msg):
      await self.message_cache.record_message(msg)
      if msg.author == self.user:
         return # Should no longer process own messages.

      # Common code for exception handling in _on_message().
      async def handle_general_error(e, msg, *, close_bot=True):
         # This is only for feedback. Exception will continue to propagate.
         print(traceback.format_exc())
         buf = "**EXCEPTION**"
         buf += "\n**From:** <#" + msg.channel.id + "> **in** " + msg.server.name
         buf += "\n**Command issued by:** <@" + msg.author.id + ">"
         buf += "\n**Full message:**"
         buf += "\n" + msg.content
         buf += "\n**Stack Trace:**"
         buf += "\n```" + traceback.format_exc() + "```"
         try:
            await self.send_msg(self.botowner, buf)
         except:
            print("FAILED TO SEND BOTOWNER STACKTRACE.")
         buf = "**EXCEPTION:** " + type(e).__name__
         buf += "\n" + str(e)
         buf += "\n<@" + MentionBot.BOTOWNER_ID + "> Check it out, will ya?"
         if close_bot:
            buf += "\n\n**THIS BOT WILL NOW RESTART.**"
         try:
            await self.send_msg(msg, buf)
         except:
            print("FAILED TO MESSAGE BOT TERMINATION BACK TO THE CHANNEL.")
         if close_bot:
            sys.exit(1)
         return

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
         await self.send_msg(msg, "Error: Unknown command.")
      except errors.InvalidCommandArgumentsError as e:
         print("Caught InvalidCommandArgumentsError.")
         if str(e) == "":
            buf = "Error: Invalid command arguments."
         else:
            buf = str(e)
         await self.send_msg(msg, buf)
      except errors.CommandPrivilegeError:
         print("Caught CommandPrivilegeError.")
         await self.send_msg(msg, "Error: Permission denied.")
      except errors.NoHelpContentExists:
         print("Caught NoHelpContentExists.")
         await self.send_msg(msg, "No help content exists.")
      except errors.OperationAborted:
         print("Caught OperationAborted.")
      except Exception as e:
         await handle_general_error(e, msg, close_bot=True)
      except (SystemExit, KeyboardInterrupt):
         raise
      except BaseException as e:
         await handle_general_error(e, msg, close_bot=True)
      return

   async def on_server_join(self, server):
      raise RuntimeError("Undefined behaviour on server join. Must restart.")

   async def on_server_remove(self, server):
      raise RuntimeError("Undefined behaviour on server leave. Must restart.")

   ##################
   # Other Services #
   ##################

   def message_cache_read(self, server_id, ch_id):
      return self.message_cache.read_messages(server_id, ch_id)

   def message_cache_debug_str(self):
      return self.message_cache.get_debugging_info()

async def _client_login(client, token):
   await client.on_message_lock.acquire() # To be released when ready.
   # TODO: Acquire the lock elsewhere. It's a little out-of-place here...
   await client.login(token)
   await client.connect()
   return

def run():
   loop = asyncio.get_event_loop()

   # Log in to discord
   client = MentionBot()
   print("\nAttempting to log in using file '" + LOGIN_DETAILS_FILENAME + "'.")
   if not os.path.isfile(LOGIN_DETAILS_FILENAME):
      login_file = open(LOGIN_DETAILS_FILENAME, "w")
      login_file.write("TOKEN")
      login_file.close()
      print("File does not exist. Please edit the file {} with your login details.")
      sys.exit()
   login_file = open(LOGIN_DETAILS_FILENAME, "r")
   email = "(No email. This variable is depreciated.)"
   password = "(No password. This variable is depreciated.)"
   bot_user_token = login_file.readline().strip()
   login_file.close()
   print("Token found.")
   print("Logging in...") # print("Logging in...", end="")

   try:
      loop.run_until_complete(_client_login(client, bot_user_token))
   except Exception as e:
      loop.run_until_complete(client.logout())
      print("Error launching client!")
      print(traceback.format_exc())
   finally:
      try:
         loop.close()
      except:
         print(traceback.format_exc())
   sys.exit(1) # Should only return on error.

if __name__ == '__main__':
   run()
