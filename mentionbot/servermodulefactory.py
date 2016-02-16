from servermoduleresources import ServerModuleResources

# Modules
from servermodules.basicinfo import BasicInfo
from servermodules.dynamicchannels import DynamicChannels
from servermodules.mentions.mentions import Mentions
from servermodules.random import Random
from servermodules.wolframalpha import WolframAlpha
from servermodules.jcfdiscord import JCFDiscord
from servermodules.bsistarkravingmadbot import BsiStarkRavingMadBot

class ServerModuleFactory:

   # Please hard-code every module class into this list.
   _MODULE_LIST = [
      BasicInfo,
      DynamicChannels,
      Mentions,
      Random,
      WolframAlpha,
      JCFDiscord,
      BsiStarkRavingMadBot,
   ]

   def __init__(self, client, server):
      self._client = client
      self._server = server
      self._modules = {}

      for module in self._MODULE_LIST:
         self._modules[module.MODULE_NAME] = module
      return

   # Generator for iterating through all modules.
   def module_list_gen(self):
      for (name, module) in self._modules.items():
         yield (name, module.MODULE_SHORT_DESCRIPTION)

   def module_exists(self, module_name):
      try:
         self._modules[module_name]
         return True
      except KeyError:
         return False

   # PRECONDITION: self.module_exists(module_name) == True
   def new_module_instance(self, module_name, server_bot_instance):
      module = self._modules[module_name]
      resources = ServerModuleResources(module_name, server_bot_instance)
      return module.get_instance(module.RECOMMENDED_CMD_NAMES, resources)



