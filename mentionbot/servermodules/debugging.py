import asyncio

import discord

import utils
import errors
from enums import PrivilegeLevel
from servermodule import ServerModule

class Debugging(ServerModule):

   _SECRET_TOKEN = utils.SecretToken()

   RECOMMENDED_CMD_NAMES = ["debugging", "debug", "db"]

   MODULE_NAME = "Debugging"
   MODULE_SHORT_DESCRIPTION = "Bot debugging tools."

   _HELP_SUMMARY_LINES = """
(DEBUGGING) self._HELP_SUMMARY_LINES
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
(DEBUGGING) self._HELP_DETAIL_LINES
   """.strip().splitlines()

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client
      return

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      print("DEBUGGING: self.msg_preprocessor(): with content = " + content)
      return content

   async def on_message(self, msg):
      print("DEBUGGING: self.on_message(): with msg.content = " + msg.content)
      return

   async def process_cmd(self, substr, msg, privilege_level):
      print("DEBUGGING: self.process_cmd(): with substr = " + substr)
      print("PRIVILEGE LEVEL = " + privilege_level.to_string())
      await self._client.send_msg(msg, "**Sub-command received:** " + substr)
      return

   

