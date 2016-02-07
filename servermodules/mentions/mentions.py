import asyncio

import discord
import utils
from modularizedservermodule import ModularizedServerModule

# Sub-modules
from servermodules.mentions.notify import Notify
from servermodules.mentions.search import Search
from servermodules.mentions.summary import Summary

class Mentions(ModularizedServerModule):

   RECOMMENDED_CMD_NAMES = ["mentions", "mb", "mentionbot"]

   def _get_initial_submodules(self):
      initial_submodules = [
         Notify(Notify.RECOMMENDED_CMD_NAMES, self._client, enabled=False), # TODO: Fix enabled.
         Search(Search.RECOMMENDED_CMD_NAMES, self._client),
         Summary(Summary.RECOMMENDED_CMD_NAMES, self._client)
      ]
      return initial_submodules
