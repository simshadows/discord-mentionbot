import asyncio

import discord
import utils
from servermodule import ServerModule
from servermodulegroup import ServerModuleGroup # For holding submodules

# Sub-modules
from servermodules.mentions.notify import Notify
from servermodules.mentions.search import Search
from servermodules.mentions.summary import Summary

class Mentions(ServerModule):

   RECOMMENDED_CMD_NAMES = ["mentions", "mb", "mentionbot"]

   # PARAMETER: enabled - If false, the module is disabled.
   def __init__(self, cmd_names, client):
      self._client = client
      self._cmd_names = cmd_names

      initial_submodules = [
         Notify(Notify.RECOMMENDED_CMD_NAMES, client, enabled=False), # TODO: Fix enabled.
         Search(Search.RECOMMENDED_CMD_NAMES, client),
         Summary(Summary.RECOMMENDED_CMD_NAMES, client)
      ]
      self._submodules = ServerModuleGroup(initial_submodules)
      return

   @property
   def cmd_names(self):
      return self._cmd_names

   def get_help_summary(self, cmd_prefix, privilegelevel=0):
      cmd_prefix = cmd_prefix + self.cmd_names[0] + " "
      return self._submodules.get_help_content("", cmd_prefix, privilege_level=privilegelevel)

   def get_help_detail(self, substr, cmd_prefix, privilegelevel=0):
      cmd_prefix = cmd_prefix + self.cmd_names[0] + " "
      return self._submodules.get_help_content(substr, cmd_prefix, privilege_level=privilegelevel)

   # Call this every time a message is received.
   async def on_message(self, msg):
      await self._submodules.on_message(msg)
      return

   # Call this to process a command.
   async def process_cmd(self, substr, msg, privilegelevel=0):
      await self._submodules.process_cmd(substr, msg, privilegelevel=privilegelevel)
      return



