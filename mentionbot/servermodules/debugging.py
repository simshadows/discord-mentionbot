import asyncio
import concurrent

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered
from ..enums import PrivilegeLevel

@registered
class Debugging(ServerModule):

   MODULE_NAME = "Debugging"
   MODULE_SHORT_DESCRIPTION = "Bot debugging tools."
   RECOMMENDED_CMD_NAMES = ["debugging", "debug", "db"]

   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {} # Empty dict should work...

   _HELP_SUMMARY = """
      DEBUGGING: _HELP_SUMMARY CONTENTS.
      """

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client

      async def nonreturning_coro():
         while True:
            print("DEBUGGING: Printing from nonreturning_coro.")
            await asyncio.sleep(2)
      await self._res.start_nonreturning_coro(nonreturning_coro())

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

   async def on_member_join(self, member):
      print("DEBUGGING: self.on_member_join(). New member: " + member.name)
      return

   async def on_member_remove(self, member):
      print("DEBUGGING: self.on_member_remove(). Removed member: " + member.name)
      return

   async def get_extra_user_info(self, member):
      return ("DEBUGGING: User name: " + member.name, "DEBUGGING: Second string.")
