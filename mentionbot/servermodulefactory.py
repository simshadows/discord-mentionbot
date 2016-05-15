from . import utils
from .servermodulewrapper import ServerModuleWrapper

# Modules
from .servermodule import module_list
from .servermodules import *

class ServerModuleFactory:
   
   _SECRET_TOKEN = utils.SecretToken()

   _module_list = list(module_list)

   @classmethod
   async def get_instance(cls, client, server):
      inst = cls(cls._SECRET_TOKEN)
      inst._client = client
      inst._server = server
      inst._modules = {}

      for module in inst._module_list:
         inst._modules[module.MODULE_NAME] = module
      return inst

   def __init__(self, token):
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
      return

   # Generator for iterating through all modules.
   def gen_available_modules(self):
      for (name, module) in self._modules.items():
         yield (name, module.MODULE_SHORT_DESCRIPTION)

   def module_exists(self, module_name):
      try:
         self._modules[module_name]
         return True
      except KeyError:
         return False

   # PRECONDITION: self.module_exists(module_name) == True
   async def new_module_instance(self, module_name, server_bot_instance):
      module_class = self._modules[module_name]
      wrapped_module = await ServerModuleWrapper.get_instance(module_class, server_bot_instance)
      return wrapped_module



