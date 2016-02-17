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

   @classmethod
   async def get_instance(cls, cmd_names, resources):
      inst = cls(cls._SECRET_TOKEN, cmd_names)
      inst._res = resources
      inst._client = inst._res.client
      return inst

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      print("DEBUGGING: self.msg_preprocessor(): with content = " + content)
      return content

   async def on_message(self, msg):
      print("DEBUGGING: self.on_message(): with msg.content = " + msg.content)
      return

   async def process_cmd(self, substr, msg, privilegelevel=0):
      print("DEBUGGING: self.process_cmd(): with substr = " + substr)
      await self._client.send_msg(msg, "**Sub-command received:** " + substr)
      return

   

