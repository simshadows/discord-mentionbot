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
      measured = self._g1_total_chars()
      bins = self._g2_each_day_bins()
      (data, x_vals) = await self._g3_generate_graph_data(msg.channel, measured, bins)
      await self._g4_bar_graph(msg.channel, data, x_vals)
      return

   ###############################################
   ### SIMPLE GRAPHING - STEP 1 (GRAPH VALUES) ###
   ###############################################

   # These return value evaluation functions.
   # Sees every message once with parameter "d" to evaluate.
   # Returned value accumulates, and this cumulative value is passed in with parameter "p".

   # You can think of this as the function that generates the y-value.

   def _g1_total_chars(self):
      return lambda p, d: p + len(d["c"])

   #############################################
   ### SIMPLE GRAPHING - STEP 2 (GRAPH BINS) ###
   #############################################

   # These return binning functions, which determines which x-value a message will be binned in.

   def _g2_each_day_bins(self):
      now = utils.datetime_rounddown_to_day(datetime.datetime.utcnow())
      now += datetime.timedelta(days=1)
      return lambda d: (now - d["t"]).days
   
   ########################################################
   ### SIMPLE GRAPHING - STEP 3 (GENERATING GRAPH DATA) ###
   ########################################################

   # This function generates graph data based on the value evaluation
   # and binning functions.

   async def _g3_generate_graph_data(self, channel, measured, bins):
      await self._client.send_msg(channel, "Generating graph. Please wait...")
      data_temp = {} # Maps day delta -> chars sent
      for ch in self._res.server.channels:
         for msg_dict in self._res.message_cache_read(self._res.server.id, ch.id):
            bin_value = bins(msg_dict)
            prev = 0
            try:
               prev = data_temp[bin_value]
            except KeyError: # May also catch msg_dict keyerror...
               pass
            data_temp[bin_value] = measured(prev, msg_dict)
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

      x_vals = []
      i = 1
      for point in data:
         x_vals.append(i)
         i += 1

      return (data, x_vals)

   ##############################################
   ### SIMPLE GRAPHING - STEP 4 (DATA OUTPUT) ###
   ##############################################

   async def _g4_bar_graph(self, channel, data, x_vals, **kwargs):
      plotly_data = [
         go.Bar(
               x = x_vals,
               y = data
            )
      ]
      await self._send_plotly_graph_object(channel, plotly_data)
      return

   ######################
   ### OTHER SERVICES ###
   ######################

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

   # This is a utility function used by graph generating functions.
   async def _send_plotly_graph_object(self, channel, plotly_data):
      temp_filename = "temp" + str(random.getrandbits(128))
      temp_file_ext = ".png"
      try:
         py.image.save_as({'data':plotly_data}, temp_filename, format='png')
      except:
         print(traceback.format_exc())
         await self._client.send_msg(msg, "Unknown error occurred. Maybe you forgot to sign in...")
         raise errors.OperationAborted
      await self._client.perm_send_file(channel, temp_filename + temp_file_ext)
      os.remove(temp_filename + temp_file_ext)
      print("GRAPH SENT!")
      return

