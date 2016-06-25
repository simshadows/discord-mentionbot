import asyncio
import datetime
import traceback
import random
import os
import csv
import collections
import threading

import discord
import plotly.plotly as py
import plotly.graph_objs as go

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered
from ..enums import PrivilegeLevel

@registered
class ServerActivityStatistics(ServerModule):

   MODULE_NAME = "Server Activity Statistics"
   MODULE_SHORT_DESCRIPTION = "Generates server activity graphs."
   RECOMMENDED_CMD_NAMES = ["stats", "serverstats"]

   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {}

   _HELP_SUMMARY = """
      `{modhelp}` - Generates user activity statistics.
      """

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client
      self._conf = self._res.get_config_ini_copy()

      self._plotly_api_key = self._conf["api_keys"]["plotly_api_key"]
      self._plotly_username = self._conf["api_keys"]["plotly_username"]

      py.sign_in(self._plotly_username, self._plotly_api_key)

      self._res.suppress_autokill(True)
      return

   async def get_help_detail(self, locator_string, entry_string, privilege_level):
      return self._get_usage_info()

   async def process_cmd(self, substr, msg, privilege_level):
      (left, right) = utils.separate_left_word(substr)
      execute_regular_cmd = False
      try:
         cmd_to_execute = await cmd.get(self._cmdd, left, privilege_level)
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
         
         # Prepare for execution in process pool.
         fn_args = [msg.channel, eval_obj["fn"], bin_obj["fn"], filter_fn["fn"]]
         loop = asyncio.get_event_loop()
         (data, x_vals) = await loop.run_in_executor(None, self._sg4_generate_graph_data, *fn_args)
         
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

   @cmd.add(_cmdd, "zipf", "wordrank", top=True)
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_zipf(self, substr, msg, privilege_level):
      """
      `{cmd}` - Generate word rank statistics. (EXPERIMENTAL)

      Additionally, it dumps a bunch more files of data locally.
      For access to these files, ask the bot owner.
      """
      # 
      buf = "Hang on, generating your data."
      buf += "\n*Note that this is a highly experimental command, and may be broken.*"
      await self._client.send_msg(msg, buf)

      ignore_colour_roles = True
      send_debugging_messages = True

      replace_with_space = [
         '!','@','#','$','%','^','&','*','(',')','=','+','[',']','{','}',';',
         ':','"',',','.','<','>','/','?','\\','|'
      ]
      
      server = self._res.server
      channel_ids = [x.id for x in server.channels]
      default_role_name = server.default_role.name

      totals = {}
      # totals is a dict of defaultdicts.
      # totals[role][word.lower()] = count
      totals_sorted = {}
      # totals_sorted is instead a dict of sorted lists.
      # We'll fill this later.
      role_totals = {}
      # role_totals[role] = the complete total of words said by the role.
      member_roles = {}
      # member_roles maps member IDs to lists of role names.
      loop = asyncio.get_event_loop()

      # Initialize a dict for every role.
      # Note: Duplicate role names are treated as the same role.
      for role in server.roles:
         role_name = role.name
         if not role_name in totals:
            totals[role_name] = collections.defaultdict(lambda: 0)

      # Initialize a list for every member.
      for member in server.members:
         role_set = set()
         for role in member.roles:
            role_set.add(role.name)
         member_roles[member.id] = list(role_set)

      # TODO: Pipeline this!
      if send_debugging_messages:
         await self._client.send_msg(msg, "Phase 1: Reading cache...")
      print("(DEBUGGING) Reading cache.")
      def cache_read():
         server_id = server.id
         for ch_id in channel_ids:
            for msg_dict in self._res.message_cache_read(server_id, ch_id):
               author_id = msg_dict["a"]
               content = msg_dict["c"]
               # Process the content before adding to totals.
               for char_to_replace in replace_with_space:
                  content = content.replace(char_to_replace, " ")
               word_list = content.lower().split()
               # word_list is all lowercase now.
               if author_id in member_roles:
                  for role in member_roles[author_id]:
                     for word in word_list:
                        totals[role][word] += 1
               else:
                  role = default_role_name
                  for word in word_list:
                     totals[role][word] += 1
         return
      await loop.run_in_executor(None, cache_read)

      if send_debugging_messages:
         await self._client.send_msg(msg, "Phase 2: Sorting totals...")
      print("(DEBUGGING) Sorting totals.")
      def sort_totals():
         for (role, words) in totals.items():
            totals_sorted[role] = sorted(words.items(), key=lambda x: -x[1])
            role_total = 0
            for (word, count) in totals_sorted[role]:
               role_total += count
            role_totals[role] = role_total
         return
      await loop.run_in_executor(None, sort_totals)

      if send_debugging_messages:
         await self._client.send_msg(msg, "Phase 3: Writing to files...")
      print("(DEBUGGING) Writing to files.")
      def write_to_files():
         for (role, words) in totals_sorted.items():
            role_total = role_totals[role]
            lines_to_write = []
            rank = 1
            for (word, count) in words:
               freq = count / role_total
               buf = "\t".join([str(rank), word, str(count), str(freq)])
               lines_to_write.append(buf)
               rank += 1
            buf = "\n".join(lines_to_write)
            if len(buf) > 0:
               filename = "wordcount_" + utils.str_asciionly(role) + ".txt"
               self._dump_to_file(buf, filename=filename)
         return
      await loop.run_in_executor(None, write_to_files)

      if send_debugging_messages:
         await self._client.send_msg(msg, "Phase 4: Generating zipf data...")
      print("(DEBUGGING) Getting zipf graph.")
      x_data = []
      y_data = []
      def get_zipf_data():
         word_rank = totals_sorted[default_role_name]
         count_total = role_totals[default_role_name]
         rank = 1
         for (word, count) in word_rank:
            x_data.append(rank)
            y_data.append(count/count_total)
            rank += 1
         return
      await loop.run_in_executor(None, get_zipf_data)

      if send_debugging_messages:
         await self._client.send_msg(msg, "Phase 5: Getting zipf graph...")
      plotly_layout = None
      plotly_data = None
      def get_plotly_objects():
         plotly_layout = go.Layout( 
            title = "Word rank vs Word Frequency",
            xaxis = dict(
               title = "rank of each word",
               type = "log",
            ),
            yaxis = dict(
               title = "word frequency",
               type = "log",
            ),
         )
         plotly_data = [
            go.Scatter(
               x = x_data,
               y = y_data,
            )
         ]
         return
      await loop.run_in_executor(None, get_plotly_objects)

      if send_debugging_messages:
         await self._client.send_msg(msg, "Phase 6: Attempting to send zipf graph...")
      await self._send_plotly_graph_object(msg.channel, plotly_data, plotly_layout)
      return

   @cmd.add(_cmdd, "convstats", top=True)
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_conv(self, substr, msg, privilege_level):
      """
      `{cmd}` - Generate conversation statistics. (EXPERIMENTAL)

      <<Write an explanation here>>
      """
      thread_num = 8
      timeframe = datetime.timedelta(minutes=5)
      mention_multiplier = 3 # Interaction rating multiplier for mentions.
      attachments_flat = 15 # Flat interaction rating added if an attachment is found.

      buf = "Hang on, generating your data."
      buf += "\n*Note that this is a highly experimental command, and may be broken.*"
      await self._client.send_msg(msg, buf)

      loop = asyncio.get_event_loop()
      assert thread_num > 1
      jobs = [None for x in range(thread_num)]
      server = self._res.server
      all_channels = list(server.channels)
      jobs_per_thread = int(len(all_channels)/thread_num)
      assert jobs_per_thread > 0
      assert len(all_channels) > thread_num
      for i in range(thread_num - 1):
         jobs[i] = all_channels[:jobs_per_thread]
         all_channels = all_channels[jobs_per_thread:]
      jobs[thread_num - 1] = all_channels # Gets the remaining channels
      # Now, all the channels are roughly evenly distributed among each
      # thread.

      interactions = collections.defaultdict(lambda: collections.defaultdict(lambda: 0))
      interactions_lock = threading.Lock()
      # interactions[uid1][uid2] = interaction_rating
      def add_to_interactions(uid1, uid2, interaction_rating):
         interactions_lock.acquire()
         i = interactions[uid1][uid2] = interactions[uid1][uid2] + interaction_rating
         j = interactions[uid2][uid1] = interactions[uid2][uid1] + interaction_rating
         interactions_lock.release()
         assert i == j
         return

      warnings_buf = []
      warnings_lock = threading.Lock()

      def read_channel(channels):
         server_id = server.id
         for ch in channels:
            print("READING INTERACTIONS IN #" + ch.name)
            last = [] # Tuples of (member_id, last_post_datetime)
            for_deletion = [] # elements of last to be deleted. Reinitialize only as necessary.
            debug_prev = datetime.datetime(datetime.MINYEAR, 1, 1) # This exists entirely for ensuring correctness.
            for msg_dict in self._res.message_cache_read(server_id, ch.id):
               author_id = msg_dict["a"]
               content = msg_dict["c"]
               timestamp = msg_dict["t"]
               has_media = (len(msg_dict["h"]) + len(msg_dict["e"])) > 0
               
               # assert debug_prev <= timestamp
               if debug_prev > timestamp:
                  warnings_lock.acquire()
                  warnings_buf.append("WARNING: debug_prev > timestamp.\n")
                  warnings_buf.append("timestamp - debug_prev = " + utils.timedelta_to_string(timestamp - debug_prev) + "\n")
                  warnings_buf.append("channel " + ch.id + "\n")
                  warnings_buf.append("author " + author_id + "\n")
                  warnings_buf.append("content " + content + "\n")
                  warnings_lock.release()
               debug_prev = timestamp
               
               interaction_rating = len(content)
               if has_media:
                  interaction_rating += attachments_flat
               mentions = set(utils.get_all_mentions(content))
               mentions.discard(author_id)

               assert isinstance(for_deletion, list) and (len(for_deletion) == 0)
               # for_deletion = [] # Optimized by only reinitializing when necessary.
               seen = set() # This exists almost entirely for ensuring correctness.
               for x in last:
                  (last_uid, last_time) = (x[0], x[1])
                  
                  assert not last_uid in seen
                  seen.add(last_uid)
                  
                  if (last_uid != author_id) and (timestamp - last_time <= timeframe):
                     multiplier = 1
                     if last_uid in mentions:
                        multiplier = mention_multiplier
                     add_to_interactions(author_id, last_uid, interaction_rating * multiplier)
                  else:
                     for_deletion.append(x)
               if len(for_deletion) > 0:
                  for x in for_deletion:
                     last.remove(x)
                  for_deletion = []
               # Now we add the current message back in.
               last.append((author_id, timestamp))
               # Anyone else who was mentioned now gets interaction rating added as well.
               for uid in mentions:
                  if not uid in seen:
                     add_to_interactions(author_id, uid, interaction_rating * mention_multiplier)
         return
      async def read_channel_wrapped(channels):
         await loop.run_in_executor(None, read_channel, channels)
         return
      futures = []
      for x in jobs:
         # fn_args = [x]
         # assert isinstance(fn_args[0], list)
         futures.append(loop.create_task(read_channel_wrapped(x)))
      await asyncio.gather(*futures)
      if not len(warnings_buf) != 0:
         print("ISSUES:\n" + "".join(warnings_buf))
      
      # Get uid to uname mapping
      uid_to_uname = {x.id: x.name for x in server.members}

      def cpu_bound_work():
         all_members = [k for (k, v) in interactions.items()]

         ################################
         # PHASE 1: Spit out raw scores #
         ################################

         print("WRITING INTERACTION RATINGS TO FILES.")
         buf = [] # List of strings to be joined later.

         # Top header row
         buf.append("Raw Scores")
         for uid in all_members:
            buf.append("\t")
            if uid in uid_to_uname:
               buf.append(uid_to_uname[uid])
            else:
               buf.append(uid)
         # All the other rows
         for uid1 in all_members: # uid1 for each row
            buf.append("\n")
            # First print the member.
            if uid1 in uid_to_uname:
               buf.append(uid_to_uname[uid1])
            else:
               buf.append(uid1)
            # Now we print the matrix.
            for uid2 in all_members: # uid2 for each column
               buf.append("\t")
               buf.append(str(interactions[uid1][uid2]))
         buf = "".join(buf)
         filename = "interactions_1_raw_scores.txt"
         self._dump_to_file(buf, filename=filename)

         ################################################
         # PHASE 2: Convert to a portion average matrix #
         ################################################

         portion_tables = collections.defaultdict(lambda: {})
         # portion_tables[uid1][uid2] = portion
         # This is the portion of the sum of uid1's total interactions in which
         # uid1 spends on uid2.

         # First, we build each table of portions.
         for uid in all_members:
            interactions_sum = 0
            for uid2 in all_members:
               interactions_sum += interactions[uid][uid2]
            for uid2 in all_members:
               portion_tables[uid][uid2] = float(interactions[uid][uid2]/interactions_sum) * 100

         portion_matrix = collections.defaultdict(lambda: {})

         # Then, we construct the matrix of portion averages.
         for uid1 in all_members:
            for uid2 in all_members:
               value = (portion_tables[uid1][uid2] + portion_tables[uid2][uid1])/2
               portion_matrix[uid1][uid2] = portion_matrix[uid2][uid1] = value

         # And we spit it out into a file.
         buf = [] # List of strings to be joined later.

         # Top header row
         buf.append("Portion Averages")
         for uid in all_members:
            buf.append("\t")
            if uid in uid_to_uname:
               buf.append(uid_to_uname[uid])
            else:
               buf.append(uid)
         # All the other rows
         for uid1 in all_members: # uid1 for each row
            buf.append("\n")
            # First print the member.
            if uid1 in uid_to_uname:
               buf.append(uid_to_uname[uid1])
            else:
               buf.append(uid1)
            # Now we print the matrix.
            for uid2 in all_members: # uid2 for each column
               buf.append("\t")
               buf.append(str(portion_matrix[uid1][uid2]))
         buf = "".join(buf)
         filename = "interactions_2_portion_avgs.txt"
         self._dump_to_file(buf, filename=filename)

         return
      await loop.run_in_executor(None, cpu_bound_work)

      await self._client.send_msg(msg, "Done. Please check the files.")
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

   # THIS FUNCTION IS BUGGED.
   # buf = " (Sorry, what this one does is difficult to explain...)"
   # _sg_arghelp1.append("`euser` - Number of newly encountered users that sent a message." + buf)
   # @cmd.add(_sg_argument1, "euser")
   # def _sg1_euser(self):
   #    users_dict = {} # Maps user id -> literally any possible value
   #    def new_fn(p, d, b):
   #       user_id = d["a"]
   #       try:
   #          temp = users_dict[user_id]
   #          return p
   #       except KeyError:
   #          users_dict[user_id] = None
   #          return p + 1
   #    ret = {
   #       "fn": new_fn,
   #       "axis": "newly encountered users that sent a message",
   #       "title": "Newly Encountered Users",
   #    }
   #    return ret

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
         "axis": "Each day of the week (1 = Mon, 2 = Tue, etc.)",
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

   def _sg4_generate_graph_data(self, channel, measured, bins, sfilter):
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
         temp_filename = utils.generate_temp_filename() + ".csv"
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

   def _dump_to_file(self, text, filename=None):
      data_dir = self._res.data_directory
      if filename is None:
         filename = utils.generate_temp_filename()
      filepath = data_dir + filename
      with open(filepath, encoding="utf-8", mode="w") as f:
         f.write(text)
      return

   # This is a utility function used by graph generating functions.
   async def _send_plotly_graph_object(self, channel, data, layout):
      loop = asyncio.get_event_loop()
      temp_filename = utils.generate_temp_filename()
      temp_file_ext = ".png"
      def get_plotly_objects():
         py.image.save_as({'data':data, 'layout':layout}, temp_filename, format='png')
         return
      try:
         await loop.run_in_executor(None, get_plotly_objects)
      except:
         print(traceback.format_exc())
         buf = "**Unknown error occurred. Maybe my plotly login details are"
         buf += " incorrect...**"
         buf += "\n(Bot owner must manually enter a plotly username and API"
         buf += " key in `config.ini` and relaunch the bot.)"
         await self._client.send_msg(channel, buf)
         raise errors.OperationAborted
      try:
         await self._client.perm_send_file(channel, temp_filename + temp_file_ext)
         os.remove(temp_filename + temp_file_ext)
      except:
         print("Hopefully this allows us to identify the bug.")
         print(traceback.format_exc())
         await self._client.send_msg(channel, "Oops! Something went wrong that would've crashed me... but it didn't!")
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
      buf += "\n\n**Example:** `" + self._res.cmd_prefix + self._res.module_cmd_aliases[0]
      buf += " chars eachday vbar wholeserver` - Bar graph of all characters"
      buf += " received by the server each day."
      return buf

