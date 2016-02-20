import asyncio
import datetime

import discord
# import plotly.plotly as py
# import plotly.graph_objs as go

import utils
import errors
from enums import PrivilegeLevel
from servermodule import ServerModule
import cmd

class ServerActivityStatistics(ServerModule):

   _SECRET_TOKEN = utils.SecretToken()

   RECOMMENDED_CMD_NAMES = ["stats", "serverstats"]

   MODULE_NAME = "Server Activity Statistics"
   MODULE_SHORT_DESCRIPTION = "Bot debugging tools."

   _HELP_SUMMARY_LINES = """
(NOT WRITTEN)
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
(NOT WRITTEN)
   """.strip().splitlines()

   _cmd_dict = {} # Command Dictionary

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client
      return

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      return content

   async def process_cmd(self, substr, msg, privilege_level):
      (left, right) = utils.separate_left_word(substr)
      cmd_to_execute = cmd.get(self._cmd_dict, left, privilege_level)
      await cmd_to_execute(self, right, msg, privilege_level)
      return

   @cmd.add(_cmd_dict, "daychars")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_uptime(self, substr, msg, privilege_level):
      now = utils.datetime_rounddown_to_day(datetime.datetime.utcnow())
      now += datetime.timedelta(days=1)
      data_temp = {} # Maps day delta -> chars sent
      for ch in self._res.server.channels:
         for msg_dict in self._res.message_cache_read(self._res.server.id, ch.id):
            delta = now - msg_dict["t"]
            days_ago = delta.days
            try:
               data_temp[days_ago] += len(msg_dict["c"])
            except KeyError: # May also catch msg_dict keyerror...
               data_temp[days_ago] = len(msg_dict["c"])
      days_ago = 0
      data = []
      while bool(data_temp): # While dictionary still has data
         content_len = 0
         try:
            content_len = data_temp[days_ago]
            del data_temp[days_ago]
         except KeyError:
            pass
         data.insert(0, content_len)
         print(str(days_ago))
         days_ago += 1

      # Front of the list is number of chars from the
      # earliest day.

      buf = "Number of characters entered on this server:\n"

      day_index = 0
      for point in data:
         buf += "(day{0}:{1}), ".format(day_index, point)
         day_index += 1

      if day_index == 0:
         buf = "NONE."
      else:
         buf = buf[:-2]

      return await self._client.send_msg(msg, buf)
   

