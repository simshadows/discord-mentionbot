import utils
from servermoduleresources import ServerModuleResources

# Modules
from servermodules.basicinfo import BasicInfo
from servermodules.dynamicchannels import DynamicChannels
from servermodules.mentionsnotify import MentionsNotify
from servermodules.random import Random
from servermodules.wolframalpha import WolframAlpha
from servermodules.jcfdiscord import JCFDiscord
from servermodules.bsistarkravingmadbot import BsiStarkRavingMadBot

class ServerModuleFactory:
   
   _SECRET_TOKEN = utils.SecretToken()

   # Please hard-code every module class into this list.
   _MODULE_LIST = [
      BasicInfo,
      DynamicChannels,
      MentionsNotify,
      Random,
      WolframAlpha,
      JCFDiscord,
      BsiStarkRavingMadBot,
   ]

   @classmethod
   async def get_instance(cls, client, server):
      inst = cls(cls._SECRET_TOKEN)
      inst._client = client
      inst._server = server
      inst._modules = {}

      for module in inst._MODULE_LIST:
         inst._modules[module.MODULE_NAME] = module
      return inst

   def __init__(self, token):
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
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
   async def new_module_instance(self, module_name, server_bot_instance):
      module = self._modules[module_name]
      resources = ServerModuleResources(module_name, server_bot_instance)
      return await module.get_instance(module.RECOMMENDED_CMD_NAMES, resources)



