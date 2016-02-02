import asyncio

import discord

import servermodules.servermodule as servermodule

class MentionNotifyModule(servermodule.ServerModule):

   _HELP_SUMMARY_LINES = """
`{pf}mentions notify` or `{pf}mb n` - View and change settings of PM notification system.
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
**The mentions notification system:**

This module notifies users of mentions via PM when they're offline.

`{pf}mentions notify` or `{pf}mb n` - View and change settings of PM notification system.
>>> PRIVILEGE LEVEL 1 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

`{pf}a toggle mentions notify`
   """.strip().splitlines()

   # PARAMETER: enabled - If false, the module is disabled.
   def __init__(self, client, enabled=True):
      self._client = client
      self._command_names = ["n","notify"]

      self._enabled = enabled
      return

   @property
   def command_names(self):
      return self._command_names

   @command_names.setter
   def command_names(self, value):
      self._command_names = value

   def get_help_summary(self, cmd_prefix, privilegelevel=0):
      return self._prepare_help_content(self._HELP_SUMMARY_LINES, cmd_prefix, privilegelevel)

   def get_help_detail(self, substr, cmd_prefix, privilegelevel=0):
      return self._prepare_help_content(self._HELP_DETAIL_LINES, cmd_prefix, privilegelevel)

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



