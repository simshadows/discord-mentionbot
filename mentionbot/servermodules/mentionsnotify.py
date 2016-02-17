import asyncio

import discord

import utils
import errors
from servermodule import ServerModule

class MentionsNotify(ServerModule):
   
   # _SECRET_TOKEN = utils.SecretToken()

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
   def get_instance(cls, cmd_names, resources):
      inst = cls(cls._SECRET_TOKEN)
      inst._client = resources.client
      inst._cmd_names = cmd_names
      return inst

   def __init__(self, token):
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
      return

   @property
   def cmd_names(self):
      return self._cmd_names

   def get_help_summary(self, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_SUMMARY_LINES, cmd_prefix, privilegelevel)

   def get_help_detail(self, substr, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_DETAIL_LINES, cmd_prefix, privilegelevel)

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




