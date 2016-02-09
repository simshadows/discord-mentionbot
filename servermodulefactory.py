# Modules
from servermodules.mentions.mentions import Mentions

class ServerModuleFactory:

   def __init__(self, client):
      self._client = client
      self._modules = {}

      # Please hard-code every module class into this list.
      modules = [
         Mentions,
      ]

      for module in modules:
         self._modules[module.MODULE_NAME] = module
      return

   # Generator for iterating through all modules.
   def module_list_gen(self):
      for (name, module) in self._modules:
         yield (name, module.MODULE_SHORT_DESCRIPTION)

   def module_exists(self, module_name):
      try:
         self._modules[module_name]
         return True
      except KeyError:
         return False

   # PRECONDITION: self.module_exists(module_name) == True
   def new_module_instance(self, module_name):
      module = self._modules[module_name]
      return module.get_instance(module.RECOMMENDED_CMD_NAMES, self._client)






