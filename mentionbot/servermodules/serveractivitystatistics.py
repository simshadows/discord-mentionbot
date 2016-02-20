import asyncio
import datetime
import traceback
import random
import os

import discord
import plotly.plotly as py
import plotly.graph_objs as go

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

   DEFAULT_SHARED_SETTINGS = {
      "login username": "PLACEHOLDER",
      "api key": "PLACEHOLDER",
   }

   _cmd_dict = {} # Command Dictionary

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client

      self._log_in_from_file()
      return

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      return content

   async def process_cmd(self, substr, msg, privilege_level):
      (left, right) = utils.separate_left_word(substr)
      cmd_to_execute = cmd.get(self._cmd_dict, left, privilege_level)
      await cmd_to_execute(self, right, msg, privilege_level)
      return

   @cmd.add(_cmd_dict, "login")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_login(self, substr, msg, privilege_level):
      self._log_in_from_file()
      await self._client.send_msg(msg, "Login details have been loaded.")
      return

   @cmd.add(_cmd_dict, "daychars")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_daychars(self, substr, msg, privilege_level):
      await self._client.send_msg(msg, "Generating graph. Please wait...")
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

      # buf = "Number of characters entered on this server:\n"

      # day_index = 0
      # for point in data:
      #    buf += "(day{0}:{1}), ".format(day_index, point)
      #    day_index += 1

      # if day_index == 0:
      #    buf = "NONE."
      # else:
      #    buf = buf[:-2]

      temp_filename = "temp" + str(random.getrandbits(128))
      temp_file_ext = ".png"

      x_vals = []
      i = 1
      for point in data:
         x_vals.append(i)
         i += 1

      plotly_data = [
         go.Bar(
               x = x_vals,
               y = data
            )
      ]

      try:
         py.image.save_as({'data':plotly_data}, temp_filename, format='png')
      except:
         print(traceback.format_exc())
         await self._client.send_msg(msg, "Unknown error occurred. Maybe you forgot to sign in...")
         raise errors.OperationAborted

      await self._client.perm_send_file(msg.channel, temp_filename + temp_file_ext)

      os.remove(temp_filename + temp_file_ext)

      print("GRAPH SENT!")

      return
   
   ##################
   # OTHER SERVICES #
   ##################

   def _log_in_from_file(self):
      shared_settings = self._res.get_shared_settings()

      if shared_settings is None:
         shared_settings = self.DEFAULT_SHARED_SETTINGS
         self._res.save_shared_settings(shared_settings)

      try:
         username = shared_settings["login username"]
      except KeyError:
         username = self.DEFAULT_SHARED_SETTINGS["login username"]
         shared_settings["login username"] = username

      try:
         api_key = shared_settings["api key"]
      except KeyError:
         api_key = self.DEFAULT_SHARED_SETTINGS["api key"]
         shared_settings["api key"] = api_key

      py.sign_in(username, api_key)

      self._res.save_shared_settings(shared_settings)
      return

