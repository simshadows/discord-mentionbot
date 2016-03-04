import asyncio
import datetime
import traceback
import random
import os
import csv

import discord
import plotly.plotly as py
import plotly.graph_objs as go

import utils
import errors
from enums import PrivilegeLevel
from servermodule import ServerModule
import cmd

class ServerActivityStatistics(ServerModule):

   MODULE_NAME = "Server Activity Statistics"
   MODULE_SHORT_DESCRIPTION = "Generates server activity graphs."
   RECOMMENDED_CMD_NAMES = ["stats", "serverstats"]

   _SECRET_TOKEN = utils.SecretToken()
   _cmd_dict = {}
   _cmd_prep_factory = cmd.CMDPreprocessorFactory()

   _HELP_SUMMARY = """
PLACEHOLDER FOR {mod}
   """.strip()

   DEFAULT_SHARED_SETTINGS = {
      "login username": "PLACEHOLDER",
      "api key": "PLACEHOLDER",
   }

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client

      self._log_in_from_file()
      return

   def get_help_detail(self, substr, privilege_level):
      return self._get_usage_info()

   async def process_cmd(self, substr, msg, privilege_level):
      (left, right) = utils.separate_left_word(substr)
      execute_regular_cmd = False
      try:
         cmd_to_execute = cmd.get(self._cmd_dict, left, privilege_level)
         execute_regular_cmd = True
      except (errors.InvalidCommandArgumentsError, errors.CommandPrivilegeError):
         pass
      if execute_regular_cmd:
         await cmd_to_execute(self, right, msg, privilege_level)
      else: # Now, let's process 

         if privilege_level < PrivilegeLevel.ADMIN:
            raise errors.CommandPrivilegeError

         if len(substr) == 0:
            buf = "**How to use this command:**"
            buf += "\n\n" + self._get_usage_info()
            await self._client.send_msg(msg, buf)
            raise errors.OperationAborted

         eval_obj = None
         try:
            eval_obj = self._sg_argument1[left]
         except KeyError:
            buf = "Error: Unknown evaluation function."
            buf += "\n\n" + self._get_usage_info()
            await self._client.send_msg(msg, buf)
            raise errors.OperationAborted
         eval_obj = eval_obj(self) # Get the eval function

         bin_obj = None
         (left2, right2) = utils.separate_left_word(right)
         try:
            bin_obj = self._sg_argument2[left2]
         except KeyError:
            buf = "Error: Unknown binning function."
            buf += "\n\n" + self._get_usage_info()
            await self._client.send_msg(msg, buf)
            raise errors.OperationAborted
         bin_obj = bin_obj(self) # Get the bin function

         graph_fn = None
         (left3, right3) = utils.separate_left_word(right2)
         try:
            graph_fn = self._sg_argument3[left3]
         except KeyError:
            buf = "Error: Unknown graphing function."
            buf += "\n\n" + self._get_usage_info()
            await self._client.send_msg(msg, buf)
            raise errors.OperationAborted
         graph_fn = graph_fn(self) # Get the graphing function

         filter_fn = None
         (left4, right4) = utils.separate_left_word(right3)
         try:
            filter_fn = self._sg_argument4[left4]
         except KeyError:
            buf = "Error: Unknown filter function."
            buf += "\n\n" + self._get_usage_info()
            await self._client.send_msg(msg, buf)
            raise errors.OperationAborted
         filter_fn = filter_fn(self, substr, msg) # Get the graphing function

         # right3 can be used for other things if need be...

         await self._client.send_msg(msg, "Generating `plotly` graph/raw values. Please wait...")
         (data, x_vals) = await self._sg4_generate_graph_data(msg.channel, eval_obj["fn"], bin_obj["fn"], filter_fn["fn"])
         
         # Compile graph function kwargs
         graph_kwargs = {
            "title": filter_fn["title"] + " " + eval_obj["title"] + " " + bin_obj["title"],

            "x_vals": x_vals,
            "y_vals": data,

            "x_axis_title": bin_obj["axis"],

            "y_axis_title": eval_obj["axis"],
         }

         await graph_fn(msg.channel, **graph_kwargs)

      return

   @cmd.add(_cmd_dict, "login")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_login(self, substr, msg, privilege_level):
      self._log_in_from_file()
      await self._client.send_msg(msg, "Login details have been loaded.")
      return

   ###############################################
   ### SIMPLE GRAPHING - STEP 1 (GRAPH VALUES) ###
   ###############################################

   # These return value evaluation functions.
   # Sees every message once with parameter "d" to evaluate.
   # Returned value accumulates, and this cumulative value is passed in with parameter "p".
   # Associated bin value is parameter "b".

   # You can think of this as the function that generates the y-value.

   # This factory method must return a dict where:
   #     fn    -> The value evaluation function.
   #     axis  -> Axis title
   #     title -> Customized text to use in the graph title.

   _sg_argument1 = {} # Command Dictionary
   _sg_arghelp1 = []

   _sg_arghelp1.append("`chars` - Total characters in messages.")
   @cmd.add(_sg_argument1, "chars")
   def _sg1_chars(self):
      ret = {
         "fn": lambda p, d, b: p + len(d["c"]),
         "axis": "total characters typed into messages",
         "title": "Characters Typed",
      }
      return ret

   _sg_arghelp1.append("`words` - Total words in messages (delimited by whitespace).")
   @cmd.add(_sg_argument1, "words")
   def _sg1_words(self):
      ret = {
         "fn": lambda p, d, b: p + len(d["c"].split()),
         "axis": "total words typed into messages",
         "title": "Words Typed",
      }
      return ret

   _sg_arghelp1.append("`msgs` - Total messages sent.")
   @cmd.add(_sg_argument1, "msgs")
   def _sg1_msgs(self):
      ret = {
         "fn": lambda p, d, b: p + 1,
         "axis": "total messages sent",
         "title": "Messages Sent",
      }
      return ret

   _sg_arghelp1.append("`uuser` - Number of unique users that sent a message.")
   @cmd.add(_sg_argument1, "uuser")
   def _sg1_uuser(self):
      bins_dict = {} # Maps bin value -> user id -> literally any possible value
      def new_fn(p, d, b):
         user_id = d["a"]
         try:
            users_dict = bins_dict[b]
            try:
               temp = users_dict[user_id]
               return p
            except KeyError:
               users_dict[user_id] = None
               return p + 1
         except KeyError:
            bins_dict[b] = {user_id:None}
            return p + 1
      ret = {
         "fn": new_fn,
         "axis": "unique users that sent a message",
         "title": "Unique Users",
      }
      return ret

   buf = " (Sorry, what this one does is difficult to explain...)"
   _sg_arghelp1.append("`euser` - Number of newly encountered users that sent a message." + buf)
   @cmd.add(_sg_argument1, "euser")
   def _sg1_euser(self):
      users_dict = {} # Maps user id -> literally any possible value
      def new_fn(p, d, b):
         user_id = d["a"]
         try:
            temp = users_dict[user_id]
            return p
         except KeyError:
            users_dict[user_id] = None
            return p + 1
      ret = {
         "fn": new_fn,
         "axis": "newly encountered users that sent a message",
         "title": "Newly Encountered Users",
      }
      return ret

   _sg_arghelp1.append("`avgmsglen` - Average message length.")
   @cmd.add(_sg_argument1, "avgmsglen")
   def _sg1_avgmsglen(self):
      bins_dict = {} # Maps bin value -> (msg count, char count)
      def new_fn(p, d, b):
         msg_len = len(d["c"])
         try:
            prev_tuple = bins_dict[b] # Previous number of messages encountered
            new_tuple = (prev_tuple[0] + 1, prev_tuple[1] + msg_len)
         except KeyError:
            new_tuple = (1, msg_len)
         bins_dict[b] = new_tuple
         try:
            return new_tuple[1] / new_tuple[0] # RETURNS FLOAT!!!
         except ZeroDivisionError:
            return 0
      ret = {
         "fn": new_fn,
         "axis": "average message length",
         "title": "Average Message Length",
      }
      return ret

   _sg_arghelp1.append("`avgwordlen` - Average word length (delimited by whitespace).")
   @cmd.add(_sg_argument1, "avgwordlen")
   def _sg1_avgwordlen(self):
      bins_dict = {} # Maps bin value -> (word count, char count)
      def new_fn(p, d, b):
         split_text = d["c"].split()
         text_words = len(split_text) # Note that this doesn't count whitespace.
         text_len = 0
         for word in split_text:
            text_len += len(word)
         try:
            prev_tuple = bins_dict[b] # Previous number of messages encountered
            new_tuple = (prev_tuple[0] + text_words, prev_tuple[1] + text_len)
         except KeyError:
            new_tuple = (text_words, text_len)
         bins_dict[b] = new_tuple
         try:
            return new_tuple[1] / new_tuple[0] # RETURNS FLOAT!!!
         except ZeroDivisionError:
            return 0
      ret = {
         "fn": new_fn,
         "axis": "average word length",
         "title": "Average Word Length",
      }
      return ret

   #############################################
   ### SIMPLE GRAPHING - STEP 2 (GRAPH BINS) ###
   #############################################

   # These return binning functions, which determines which x-value a message will be binned in.

   # This factory method must return a dict where:
   #     fn    -> The bin evaluation function.
   #     axis  -> Axis title
   #     title -> Customized text to use in the graph title.

   _sg_argument2 = {} # Command Dictionary
   _sg_arghelp2 = []

   _sg_arghelp2.append("`eachday` - Each day of the server's life.")
   @cmd.add(_sg_argument2, "eachday")
   def _sg2_eachday(self):
      now = utils.datetime_rounddown_to_day(datetime.datetime.utcnow())
      now += datetime.timedelta(days=1)
      ret = {
         "fn": lambda d: (now - d["t"]).days,
         "axis": "Each day of the server's life (left = earliest)",
         "title": "Each Day",
      }
      return ret

   _sg_arghelp2.append("`eachhour` - Each hour of the server's life.")
   @cmd.add(_sg_argument2, "eachhour")
   def _sg2_eachhour(self):
      now = utils.datetime_rounddown_to_hour(datetime.datetime.utcnow())
      now += datetime.timedelta(hours=1)
      def new_fn(d):
         delta = now - d["t"]
         return (delta.days * 24) + int(delta.seconds/3600) # Rounds down.
      ret = {
         "fn": new_fn,
         "axis": "Each hour of the server's life (left = earliest)",
         "title": "Each Hour",
      }
      return ret

   buf = " **Important note**: This is a total, making the graph misleading. This will be addressed soon."
   _sg_arghelp2.append("`weekday` - Day of the week (e.g. all Mondays bin together)." + buf)
   @cmd.add(_sg_argument2, "weekday")
   def _sg2_weekday(self):
      ret = {
         "fn": lambda d: 6 - d["t"].weekday(),
         "axis": "Each day of the week (0 = Mon, 1 = Tue, etc.)",
         "title": "Each Day Of The Week",
      }
      return ret

   _sg_arghelp2.append("`dayhour` - Hour of the day (similar idea to *weekday*)." + buf)
   @cmd.add(_sg_argument2, "dayhour")
   def _sg2_dayhour(self):
      ret = {
         "fn": lambda d: 23 - d["t"].hour,
         "axis": "Each hour of the day (0 to 23, UTC) ",
         "title": "Each Hour Of The Day",
      }
      return ret

   _sg_arghelp2.append("`day15min` - Each 15 minute interval of the day (similar idea to *weekday*)." + buf)
   @cmd.add(_sg_argument2, "day15min")
   def _sg2_day15min(self):
      def new_fn(d):
         t = d["t"]
         return 95 - (t.hour * 4) + int(t.minute/15)
      ret = {
         "fn": new_fn,
         "axis": "Each 15 minute interval of the day (Leftmost = 0:00-0:15 UTC) ",
         "title": "Each 15 Minute Interval Of The Day",
      }
      return ret

   #########################################
   ### SIMPLE GRAPHING - STEP 3 (FILTER) ###
   #########################################

   _sg_argument4 = {} # Command Dictionary
   _sg_arghelp4 = []

   _sg_arghelp4.append("`wholeserver` - All messages in the server are analyzed.")
   @cmd.add(_sg_argument4, "wholeserver")
   def _sg3_wholeserver(self, substr, msg):
      ret = {
         "fn": lambda d, ch_id: True,
         "title": "Server -",
      }
      return ret

   _sg_arghelp4.append("`thischannel` - Only this channel is analyzed.")
   @cmd.add(_sg_argument4, "thischannel")
   def _sg3_thischannel(self, substr, msg):
      filt_ch_id = msg.channel.id
      def new_fn(d, ch_id):
         if ch_id == filt_ch_id:
            return True
         return False
      ret = {
         "fn": new_fn,
         "title": "#" + msg.channel.name + " -",
      }
      return ret
   
   ########################################################
   ### SIMPLE GRAPHING - STEP 4 (GENERATING GRAPH DATA) ###
   ########################################################

   # This function generates graph data based on the value evaluation
   # and binning functions.

   async def _sg4_generate_graph_data(self, channel, measured, bins, sfilter):
      data_temp = {} # Maps day delta -> chars sent
      for ch in self._res.server.channels:
         for msg_dict in self._res.message_cache_read(self._res.server.id, ch.id):
            if not sfilter(msg_dict, ch.id):
               continue
            bin_value = bins(msg_dict)
            prev = 0
            try:
               prev = data_temp[bin_value]
            except KeyError: # May also catch msg_dict keyerror...
               pass
            data_temp[bin_value] = measured(prev, msg_dict, bin_value)
      bin_val = 0
      data = []
      while bool(data_temp): # While dictionary still has data
         content_len = 0
         try:
            content_len = data_temp[bin_val]
            del data_temp[bin_val]
         except KeyError:
            pass
         data.insert(0, content_len)
         bin_val += 1

      x_vals = []
      i = 1
      for point in data:
         x_vals.append(i)
         i += 1

      return (data, x_vals)

   ##############################################
   ### SIMPLE GRAPHING - STEP 5 (DATA OUTPUT) ###
   ##############################################

   # This determines what form the output takes.

   _sg_argument3 = {} # Command Dictionary
   _sg_arghelp3 = []

   _sg_arghelp3.append("`line` - Line graph.")
   @cmd.add(_sg_argument3, "line")
   def _sg5_line(self):
      async def function(channel, **kwargs):
         plotly_data = [
            go.Scatter(
               x = kwargs["x_vals"],
               y = kwargs["y_vals"]
            )
         ]
         plotly_layout = self._kwargs_to_plotly_layout(**kwargs)
         await self._send_plotly_graph_object(channel, plotly_data, plotly_layout)
         return
      return function

   _sg_arghelp3.append("`vbar` - Vertical bar graph.")
   @cmd.add(_sg_argument3, "vbar")
   def _sg5_vbar(self):
      async def function(channel, **kwargs):
         plotly_data = [
            go.Bar(
               x = kwargs["x_vals"],
               y = kwargs["y_vals"]
            )
         ]
         plotly_layout = self._kwargs_to_plotly_layout(**kwargs)
         await self._send_plotly_graph_object(channel, plotly_data, plotly_layout)
         return
      return function

   _sg_arghelp3.append("`inchannel` - Outputs raw numbers as a message. (Might be really long...)")
   @cmd.add(_sg_argument3, "inchannel")
   def _sg5_inchannel(self):
      async def function(channel, **kwargs):
         data = kwargs["y_vals"]
         buf = "{} bins in order from lowest to highest:\n```\n".format(str(len(data)))
         for point in data:
            buf += str(point) + ", "
         await self._client.send_msg(channel, buf[:-2] + "\n```")
         return
      return function

   _sg_arghelp3.append("`csv` - Outputs raw numbers in a csv file (excel dialect).")
   @cmd.add(_sg_argument3, "csv")
   def _sg5_csv(self):
      CSV_DIALECT = "excel"
      async def function(channel, **kwargs):
         temp_filename = "temp" + str(random.getrandbits(128)) + ".csv"
         with open(temp_filename, "w", newline="") as f:
            csv_obj = csv.writer(f, dialect=CSV_DIALECT)
            for (x, y) in zip(kwargs["x_vals"], kwargs["y_vals"]):
               csv_obj.writerow([x, y])
         await self._client.perm_send_file(channel, temp_filename)
         os.remove(temp_filename)
         return
      return function

   # (Utility functions used for this step)

   @classmethod
   def _kwargs_to_plotly_layout(cls, **kwargs):
      return go.Layout( 
         title = kwargs["title"],
         xaxis = dict(
            title = kwargs["x_axis_title"],
         ),
         yaxis = dict(
            title = kwargs["y_axis_title"],
         ),
      )

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
   async def _send_plotly_graph_object(self, channel, data, layout):
      temp_filename = "temp" + str(random.getrandbits(128))
      temp_file_ext = ".png"
      try:
         py.image.save_as({'data':data, 'layout':layout}, temp_filename, format='png')
      except:
         print(traceback.format_exc())
         buf = "Unknown error occurred. Maybe you forgot to sign in..."
         buf += "\n(Bot owner must manually enter plotly login details in settings files,"
         buf += " and use `/stats login` for it take effect.)"
         await self._client.send_msg(msg, buf)
         raise errors.OperationAborted
      await self._client.perm_send_file(channel, temp_filename + temp_file_ext)
      os.remove(temp_filename + temp_file_ext)
      print("GRAPH SENT!")
      return

   def _get_usage_info(self):
      buf = "**Argument 1 (Message Evaluation) is one of:**"
      for line in self._sg_arghelp1:
         buf += "\n" + line
      buf += "\n\n**Argument 2 (Binning) is one of:**"
      for line in self._sg_arghelp2:
         buf += "\n" + line
      buf += "\n\n**Argument 3 (Graph Type) is one of:**"
      for line in self._sg_arghelp3:
         buf += "\n" + line
      buf += "\n\n**Argument 4 (Filter) is one of:**"
      for line in self._sg_arghelp4:
         buf += "\n" + line
      buf += "\n\n**Example:** `" + self._res.cmd_prefix + self._cmd_names[0]
      buf += " chars eachday vbar wholeserver` - Bar graph of all characters"
      buf += " received by the server each day."
      return buf

