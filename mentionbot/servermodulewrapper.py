from . import utils, errors, cmd
from .servermoduleresources import ServerModuleResources

class ServerModuleWrapper:

   _SECRET_TOKEN = NotImplemented

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

   @classmethod
   async def get_instance(cls, module_class, server_bot_instance, *args):
      self = cls(cls._SECRET_TOKEN)

      # Arguments
      module_cmd_aliases = None
      if len(args) == 1:
         module_cmd_aliases = list(args[0])
      else:
         module_cmd_aliases = module_class.RECOMMENDED_CMD_NAMES
      
      self._module_class = module_class
      self._module_instance = None
      self._sbi = server_bot_instance
      self._module_cmd_aliases = module_cmd_aliases
      self._shortcut_cmd_aliases = None # Maps top-level command alias to module command alias.

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

      # Initialize the module instance
      module_resources = ServerModuleResources(module_class.MODULE_NAME, server_bot_instance, self)
      self._module_instance = await module_class.get_instance(module_cmd_aliases, module_resources)

      return self

   def __init__(self, token):
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
      return

   def get_help_summary(self, privilege_level):
      return self._module_instance.get_help_summary(privilege_level, self._module_cmd_aliases[0])

   def get_help_detail(self, substr, privilege_level):
      return self._module_instance.get_help_detail(substr, privilege_level, self._module_cmd_aliases[0])

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      return await self._module_instance.msg_preprocessor(content, msg, default_cmd_prefix)

   # PARAMETER: upper_cmd_alias is the command alias that was split off before
   #            the substring was passed into this function.
   #            E.g. if the full command was `/random choice A;B;C`, ServerBotInstance
   #            would pass in substr="choice A;B;C" and upper_cmd_alias="random".
   async def process_cmd(self, substr, msg, privilege_level, upper_cmd_alias):
      if upper_cmd_alias in self._shortcut_cmd_aliases:
         substr = self._shortcut_cmd_aliases[upper_cmd_alias] + " " + substr
      return await self._module_instance.process_cmd(substr, msg, privilege_level)

   async def on_message(self, msg):
      return await self._module_instance.on_message(msg)
