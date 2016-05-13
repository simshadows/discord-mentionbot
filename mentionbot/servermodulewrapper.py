import asyncio

from . import utils, errors, cmd
from .servermoduleresources import ServerModuleResources

class ServerModuleWrapper:
   """
   Wraps the operations of a server module.

   Has two states:
      Active
         The module instance is running as intended.
      Inactive
         The module is not running. The wrapper holds no reference to the
         module. Calls to methods that would've been served by the module
         instance vary. This behaviour is found at the beginning of function
         definitions.
   """

   _SECRET_TOKEN = NotImplemented

   # Note that the initial state of ServerModuleWrapper is deactivated.
   @classmethod
   async def get_instance(cls, module_class, server_bot_instance, *args):
      self = cls(cls._SECRET_TOKEN)

      # Arguments
      module_cmd_aliases = None
      if len(args) == 1:
         module_cmd_aliases = list(args[0])
      else:
         module_cmd_aliases = module_class.RECOMMENDED_CMD_NAMES

      self._client = server_bot_instance.client
      self._sbi = server_bot_instance
      
      self._module_class = module_class
      self._module_cmd_aliases = module_cmd_aliases
      self._shortcut_cmd_aliases = None # Maps top-level command alias to module command alias.

      self._module_instance = None

      # Initialize self._shortcut_cmd_aliases
      self._shortcut_cmd_aliases = {}
      for cmd_fn in self._module_class.get_cmd_functions():
         if not hasattr(cmd_fn, "top_level_alias_type"):
            continue
         module_cmd_alias = cmd_fn.cmd_names[0]
         top_level_aliases = None
         if cmd_fn.top_level_alias_type is cmd.TopLevelAliasAction.USE_EXISTING_ALIASES:
            top_level_aliases = cmd_fn.cmd_names
         elif cmd_fn.top_level_alias_type is cmd.TopLevelAliasAction.USE_NEW_ALIASES:
            top_level_aliases = cmd_fn.top_level_aliases
         else:
            raise RuntimeError("Not a recognized enum value.")
         for top_level_alias in top_level_aliases:
            self._shortcut_cmd_aliases[top_level_alias] = module_cmd_alias

      await self.activate() # TODO: TEMPORARY
      return self

   def __init__(self, token):
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
      return

   @property
   def module_name(self):
      return self._module_class.MODULE_NAME

   @property
   def module_short_description(self):
      return self._module_class.MODULE_SHORT_DESCRIPTION

   @property
   def module_cmd_aliases(self):
      return self._module_cmd_aliases

   # Returns all top-level commands that are to be directed to this module.
   # This includes all aliases from self.module_cmd_aliases, and the other
   # "shortcut" aliases.
   @property
   def all_cmd_aliases(self):
      aliases = list(self._module_cmd_aliases)
      for (alias, transformation) in self._shortcut_cmd_aliases.items():
         aliases.append(alias)
      return aliases

   def is_active(self):
      return not self._module_instance is None

   async def activate(self):
      res = ServerModuleResources(self._module_class.MODULE_NAME, self._sbi, self)
      self._module_instance = await self._module_class.get_instance(self._module_cmd_aliases, res)
      return

   async def kill(self):
      self._module_instance = None
      return

   ########################################################################################
   # METHODS SERVED BY THE MODULE #########################################################
   ########################################################################################

   def get_help_summary(self, privilege_level):
      if not self.is_active():
         return "(The `{}` module is not active.)".format(self.module_name)
      return self._module_instance.get_help_summary(privilege_level, self._module_cmd_aliases[0])

   def get_help_detail(self, substr, privilege_level):
      if not self.is_active():
         return "The `{}` module is not active.".format(self.module_name)
      return self._module_instance.get_help_detail(substr, privilege_level, self._module_cmd_aliases[0])

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      if not self.is_active():
         return content
      return await self._module_instance.msg_preprocessor(content, msg, default_cmd_prefix)

   # PARAMETER: upper_cmd_alias is the command alias that was split off before
   #            the substring was passed into this function.
   #            E.g. if the full command was `/random choice A;B;C`, ServerBotInstance
   #            would pass in substr="choice A;B;C" and upper_cmd_alias="random".
   async def process_cmd(self, substr, msg, privilege_level, upper_cmd_alias):
      if not self.is_active():
         buf = "Error: The `{}` server module is not active."
         buf += "\n(Automatic deactivation is usually caused by an unhandled error within"
         buf += " the module. This is done as a security measure to prevent further damage,"
         buf += " especially from exploitable bugs.)"
         await self._client.send_msg(msg, buf)
         return
      if upper_cmd_alias in self._shortcut_cmd_aliases:
         substr = self._shortcut_cmd_aliases[upper_cmd_alias] + " " + substr
      try:
         await self._module_instance.process_cmd(substr, msg, privilege_level)
      except Exception as e:
         # print(traceback.format_exc())
         raise # TODO: TEMPORARY
      return

   async def on_message(self, msg):
      if not self.is_active():
         return
      return await self._module_instance.on_message(msg)
