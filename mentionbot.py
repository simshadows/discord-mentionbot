import datetime
import sys
import copy
import time
import re
import os

import discord # pip install git+https://github.com/Rapptz/discord.py@async

import utils
import errors
import clientextended

import serverbotinstance
import mentions.notify
import mentions.search
import mentions.summary
import helpmessages.helpmessages

LOGIN_DETAILS_FILENAME = "login_details" # This file is used to login. Only contains two lines. Line 1 is email, line 2 is password.
BOTOWNER_ID = str(119384097473822727) # User ID of the owner of this bot
INITIAL_GAME_STATUS = "hello thar"

client = clientextended.ClientExtended()

def initialize_global_variables():

   global server_bot_instances
   server_bot_instances = {}
   for server in client.servers:
      server_bot_instances[server] = serverbotinstance.ServerBotInstance(client, server)

   # The others
   global bot_mention
   global bot_name
   global botowner_mention
   global botowner
   global initialization_timestamp   
   bot_mention = "<@{}>".format(client.user.id)
   bot_name = client.user.name
   botowner_mention = "<@{}>".format(BOTOWNER_ID)
   botowner = client.search_for_user(BOTOWNER_ID)
   initialization_timestamp = datetime.datetime.utcnow()
   
   return

###########################################################################################


@client.async_event
async def on_ready():
   initialize_global_variables()
   await client.set_game_status(INITIAL_GAME_STATUS)
   print("")
   print("LOGIN_DETAILS_FILENAME = '{}'".format(LOGIN_DETAILS_FILENAME))
   print("INITIAL_GAME_STATUS = '{}'".format(INITIAL_GAME_STATUS))
   print("")
   print("Bot owner: " + botowner.name)
   print("Bot name: " + bot_name)
   print("")
   print("Initialization complete.")
   print("")

   
@client.async_event
async def on_message(msg):
   global bot_mention

   if msg.author == client.user:
      return # never process own messages.

   for (server, server_bot_instance) in server_bot_instances.items():
      server_bot_instance.on_message(msg)

   try:
      text = msg.content.strip()
      (left, right) = utils.separate_left_word(text)
      if msg.channel.__class__.__name__ is "Channel":
         try:
            print("msg rcv #" + msg.channel.name + ": " + str(text.encode("unicode_escape")))
         except Exception:
            print("msg rcv (UNKNOWN DISPLAY ERROR)")

         if text.startswith("/"):
            await server_bot_instances[msg.server].process_cmd(text[1:].strip(), msg, no_default=True)

         elif left == "$mb":
            # TODO: Make a better way of calling.
            await server_bot_instances[msg.server]._cmd1_mentions(right, msg, no_default=False)

         # EASTER EGG REPLY.
         elif (left == "$blame") and (bot_mention in text):
            await client.send_msg(msg, "no fk u")

         elif (bot_mention in text or text == client.user.name + " pls"):
            # TODO: Make a better way of calling.
            await server_bot_instances[msg.server]._mbSummaryModule.process_cmd("", msg, add_extra_help=True)
         
         # EASTER EGG REPLY
         elif msg.content.startswith("$blame " + botowner_mention) or msg.content.startswith("$blame " + botowner.name):
            await client.send_msg(msg, "he didnt do shit m8")

      else:
         await client.send_msg(msg, "sry m8 im not programmed to do anything fancy with pms yet")
         print("private msg rcv from" + msg.author.name + ": " + text)
   
   except errors.UnknownCommandError:
      print("Caught UnknownCommandError.")
      await client.send_msg(msg, "sry m8 idk what ur asking") # intentional typos. pls don't lynch me.
   except errors.InvalidCommandArgumentsError:
      print("Caught InvalidCommandArgumentsError.")
      await client.send_msg(msg, "soz m8 one or more (or 8) arguments are invalid")
   except errors.CommandPrivilegeError:
      print("Caught CommandPrivilegeError.")
      await client.send_msg(msg, "im afraid im not allowed to do that for you m8")
   
   return 


# Log in to discord
print("\nAttempting to log in using file '" + LOGIN_DETAILS_FILENAME + "'.")
if not os.path.isfile(LOGIN_DETAILS_FILENAME):
   print("File does not exist. Terminating.")
   sys.exit()
login_file = open(LOGIN_DETAILS_FILENAME, "r")
email = login_file.readline().strip()
password = login_file.readline().strip()
login_file.close()
print("Email: " + email)
print("Password: " + len(password) * "*")
print("Logging in...", end="")

client.run(email, password)
print(" success.")

