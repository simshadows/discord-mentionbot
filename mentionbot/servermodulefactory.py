from . import utils
from .servermodulewrapper import ServerModuleWrapper

# Modules
from .servermodule import module_list, core_module_list
from .servermodulescore import *
from .servermodules import *

class ServerModuleFactory:
   
   _SECRET_TOKEN = utils.SecretToken()

   _module_list = list(module_list)
   _core_module_list = list(core_module_list)

   _modules_dict = {} # No core modules are in here.
   for i in _module_list:
      _modules_dict[i.MODULE_NAME] = i

   @classmethod
   async def get_instance(cls, client, server):
      inst = cls(cls._SECRET_TOKEN)
      inst._client = client
      inst._server = server
      return inst

   def __init__(self, token):
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
      return

   # Generator for iterating through all modules.
   def gen_available_modules(self):
      for (name, module) in self._modules_dict.items():
         yield (name, module.MODULE_SHORT_DESCRIPTION)

   # This only checks regular modules, not core modules.
   def module_exists(self, module_name):
      try:
         self._modules_dict[module_name]
         return True
      except KeyError:
         return False

   # This only allows you to make regular modules, not core modules.
   # PRECONDITION: self.module_exists(module_name) == True
   async def new_module_instance(self, module_name, server_bot_instance):
      module_class = self._modules_dict[module_name]
      wrapped_module = await ServerModuleWrapper.get_instance(module_class, server_bot_instance)
      return wrapped_module

   # Get a list containing an instance of each core module.
   async def get_core_module_instances(self, server_bot_instance):
      wrapped_modules = []
      for module_class in self._core_module_list:
         wrapped_modules.append(await ServerModuleWrapper.get_instance(module_class, server_bot_instance, core=True))
      return wrapped_modules



