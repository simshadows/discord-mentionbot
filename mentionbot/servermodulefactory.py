from . import utils
from .servermoduleresources import ServerModuleResources
from .servermodulewrapper import ServerModuleWrapper

# Modules
from .servermodules.basicinfo import BasicInfo
from .servermodules.dynamicchannels import DynamicChannels
from .servermodules.mentionsnotify import MentionsNotify
from .servermodules.serveractivitystatistics import ServerActivityStatistics
from .servermodules.random import Random
from .servermodules.wolframalpha import WolframAlpha
from .servermodules.jcfdiscord import JCFDiscord
from .servermodules.bsistarkravingmadbot import BsiStarkRavingMadBot
from .servermodules.debugging import Debugging
from .servermodules.selfservecolours import SelfServeColours
from .servermodules.truthgame import TruthGame

class ServerModuleFactory:
   
   _SECRET_TOKEN = utils.SecretToken()

   # Please hard-code every module class into this list.
   _MODULE_LIST = [
      BasicInfo,
      DynamicChannels,
      MentionsNotify,
      ServerActivityStatistics,
      Random,
      WolframAlpha,
      JCFDiscord,
      BsiStarkRavingMadBot,
      Debugging,
      SelfServeColours,
      TruthGame,
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
      resources = ServerModuleResources(module_name, server_bot_instance)
      module = await module_class.get_instance(module_class.RECOMMENDED_CMD_NAMES, resources)
      wrapped_module = await ServerModuleWrapper.get_instance(module)
      return wrapped_module



