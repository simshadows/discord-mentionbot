from . import utils, errors

class ServerModuleWrapper:

   _SECRET_TOKEN = NotImplemented

   @property
   def module_name(self):
      return self._module_instance.MODULE_NAME

   @property
   def module_short_description(self):
      return self._module_instance.MODULE_SHORT_DESCRIPTION

   @property
   def cmd_aliases(self):
      return self._cmd_aliases

   @classmethod
   async def get_instance(cls, module_instance, *args):
      self = cls(cls._SECRET_TOKEN)

      # Arguments
      cmd_aliases = None
      if len(args) == 1:
         cmd_aliases = list(args[0])
      else:
         cmd_aliases = module_instance.RECOMMENDED_CMD_NAMES
      
      self._module_instance = module_instance
      self._cmd_aliases = cmd_aliases

      return self

   def __init__(self, token):
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
      return

   def get_help_summary(self, privilege_level):
      return self._module_instance.get_help_summary(privilege_level)

   def get_help_detail(self, substr, privilege_level):
      return self._module_instance.get_help_detail(substr, privilege_level)

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      return await self._module_instance.msg_preprocessor(content, msg, default_cmd_prefix)

   async def process_cmd(self, substr, msg, privilege_level):
      return await self._module_instance.process_cmd(substr, msg, privilege_level)

   async def on_message(self, msg):
      return await self._module_instance.on_message(msg)
