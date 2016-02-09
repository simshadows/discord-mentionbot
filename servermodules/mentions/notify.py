import asyncio

import discord

import utils
import errors
from servermodule import ServerModule

class Notify(ServerModule):

   RECOMMENDED_CMD_NAMES = ["notify", "n"]

   MODULE_NAME = "Notify"
   MODULE_SHORT_DESCRIPTION = "PMs offline users when mentioned."

   _HELP_SUMMARY_LINES = """
`{pf}notify` - View and change settings of PM notification system.
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
**The mentions notification system:**

This module notifies users of mentions via PM when they're offline.

`{pf}notify` - View and change settings of PM notification system.
>>> PRIVILEGE LEVEL 1 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

TODO: PLS ADD HELP FOR TOGGLE FEATURE. THX M8
   """.strip().splitlines()

   # PARAMETER: enabled - If false, the module is disabled.
   def __init__(self, cmd_names, client, enabled=True):
      self._client = client
      self._cmd_names = cmd_names

      self._enabled = enabled
      return

   @classmethod
   def get_instance(cls, cmd_names, client):
      return Notify(cmd_names, client, enabled=False)

   @property
   def cmd_names(self):
      return self._cmd_names

   def get_help_summary(self, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_SUMMARY_LINES, cmd_prefix, privilegelevel)

   def get_help_detail(self, substr, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_DETAIL_LINES, cmd_prefix, privilegelevel)

   # Call this every time a message is received.
   async def on_message(self, msg):
      if not self._enabled:
         return
      
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
      await self._client.send_msg(member, "The notify module is still under development. Sorry!")
      return

   # True if notifications is enabled, False otherwise.
   def is_enabled(self):
      return self._enabled

   # Enable notifications.
   def enable(self):
      self._enabled = True
      return

   # Disable notifications.
   def disable(self):
      self._enabled = False
      return



