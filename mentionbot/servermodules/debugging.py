import asyncio

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule
from ..enums import PrivilegeLevel

class Debugging(ServerModule):

   MODULE_NAME = "Debugging"
   MODULE_SHORT_DESCRIPTION = "Bot debugging tools."
   RECOMMENDED_CMD_NAMES = ["debugging", "debug", "db"]

   _SECRET_TOKEN = utils.SecretToken()
   _cmd_dict = {} # Empty dict should work...

   _HELP_SUMMARY = """
DEBUGGING: _HELP_SUMMARY CONTENTS.
   """.strip()

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client

      self._res.suppress_autokill(True)
      return

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      print("DEBUGGING: self.msg_preprocessor(): with content = " + content)
      return content

   async def process_cmd(self, substr, msg, privilege_level):
      print("DEBUGGING: self.process_cmd(): with substr = " + substr)
      print("PRIVILEGE LEVEL = " + privilege_level.to_string())
      await self._client.send_msg(msg, "**Sub-command received:** " + substr)
      return

   async def on_message(self, msg):
      print("DEBUGGING: self.on_message(): with msg.content = " + msg.content)
      return
