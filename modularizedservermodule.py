import asyncio

from servermodule import ServerModule
from servermodulegroup import ServerModuleGroup # For holding submodules

# Abstract Class
# All server modules are subclasses of ServerModule.
class ModularizedServerModule:

   RECOMMENDED_CMD_NAMES = NotImplemented

   # This must be overwritten to return a list of initialized submodules.
   def _get_initial_submodules(self):
      raise NotImplementedError

   # Feel free to extend, but pls call super-constructor. thx!
   def __init__(self, cmd_names, client):
      self._client = client
      self._cmd_names = cmd_names

      self._submodules = ServerModuleGroup(self._get_initial_submodules())
      return

   # pls no overwriterino thx
   @property
   def cmd_names(self):
      return self._cmd_names

   # pls no overwriterino thx
   def get_help_summary(self, cmd_prefix, privilegelevel=0):
      cmd_prefix = cmd_prefix + self.cmd_names[0] + " "
      return self._submodules.get_help_content("", cmd_prefix, privilege_level=privilegelevel)

   # pls no overwriterino thx
   def get_help_detail(self, substr, cmd_prefix, privilegelevel=0):
      cmd_prefix = cmd_prefix + self.cmd_names[0] + " "
      return self._submodules.get_help_content(substr, cmd_prefix, privilege_level=privilegelevel)

   # pls no overwriterino thx
   async def on_message(self, msg):
      await self._submodules.on_message(msg)
      return

   # pls no overwriterino thx
   async def process_cmd(self, substr, msg, privilegelevel=0):
      await self._submodules.process_cmd(substr, msg, privilegelevel=privilegelevel)
      return




