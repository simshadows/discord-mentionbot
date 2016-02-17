import asyncio

import discord

import utils
import errors
from servermodule import ServerModule

class MentionsNotify(ServerModule):
   
   _SECRET_TOKEN = utils.SecretToken()

   RECOMMENDED_CMD_NAMES = ["mnotify", "mentionsnotify", "mn"]

   MODULE_NAME = "Mentions Notify"
   MODULE_SHORT_DESCRIPTION = "PMs offline users when mentioned."

   _HELP_SUMMARY_LINES = """
`{pf}mnotify` - View and change settings of PM notification system.
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
**The mentions notification system:**

This module notifies users of mentions via PM when they're offline.

`{pf}mnotify` - View and change settings of PM notification system.
   """.strip().splitlines()

   @classmethod
   async def get_instance(cls, cmd_names, resources):
      inst = cls(cls._SECRET_TOKEN, cmd_names)
      inst._client = resources.client
      return inst

   # Call this every time a message is received.
   async def on_message(self, msg):
      for member in msg.mentions:
         if str(member.status) != "offline":
            continue
         buf = "Hello! <@" + msg.author.id + "> mentioned you in <#" + msg.channel.id + "> while you were offline."
         buf += "\n**Message contents are as follows:**"
         buf += "\n" + msg.content
         await self._client.send_msg(member, buf)
         print("MentionNotifyModule: A notification was sent!")
      return

   # Call this to process a command.
   async def process_cmd(self, substr, msg, privilegelevel=0):
      await self._client.send_msg(member, "The notify module currently has no commands. Sorry!")
      return




