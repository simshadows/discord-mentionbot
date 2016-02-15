import asyncio
import threading
import copy
import time

import discord

import utils
import errors
from enums import PrivilegeLevel
from servermodule import ServerModule

class DynamicChannels(ServerModule):

   RECOMMENDED_CMD_NAMES = ["dchannel"]

   MODULE_NAME = "Dynamic Channels"
   MODULE_SHORT_DESCRIPTION = "Allows users to create temporary channels."

   _HELP_SUMMARY_LINES = """
(DYNAMIC CHANNELS HAS NOT YET BEEN IMPLEMENTED!)
`+` - See list of hidden channels. (Will cut off at 2000 chars.)
`+[string]` - Search list of hidden channels.
`++[string]` - Create/unhide channel.
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
(DYNAMIC CHANNELS HAS NOT YET BEEN IMPLEMENTED!)
`+` - See list of hidden channels. (Will cut off at 2000 chars.)
`+[string]` - Search list of hidden channels.
`++[string]` - Create/unhide channel.
   """.strip().splitlines()

# >>> PRIVILEGE LEVEL 8000 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
# `{pf}dchannel enacreation [true|false]` - Enables/disables channel creation.
# `{pf}dchannel enaautohide [true|false]` - Enables/disables channel auto-hide.
# `{pf}dchannel enatopicedit [true|false]` - Enables/disables topic editing.
# `{pf}dchannel autohidetimer [integer]` - Set auto-hide time-out (in minutes).

   DEFAULT_SETTINGS = {
      "default channels": [],
      "channel timeout": 10,
      "max active temp channels": 5
   }

   # THIS METHOD SHOULD NOT BE USED TO INSTANTIATE THIS MODULE NORMALLY.
   # PLEASE USE THE STATIC FACTORY METHOD WHICH CONTAINS THE NECESSARY ASYNCHRONOUS
   # FUNCTIONS TO PROPERLY INITIALIZE THIS MODULE.
   def __init__(self, cmd_names, resources):
      self._res = resources

      self._client = self._res.client
      self._server = self._res.server
      self._cmd_names = cmd_names
      self._default_role = self._server.default_role

      self._is_initialized = False

      self._timeout_thread = None
      self._default_channels = None
      self._temp_channel_dict = None
      self._max_active_temp_channels = None # If <0, then there's no limit.
      self._channel_timeout = None # Channel timeout in minutes.
      # Timeout is not exact. The actual timeout of a channel is somewhere
      # between _channel_timeout minutes and _channel_timeout + 1 minutes.
      return

   @property
   def default_channels(self):
      return self._default_channels
   

   def _load_settings(self):
      # Server Settings
      settings = self._res.get_settings()
      if settings is None:
         self._res.save_settings(self.DEFAULT_SETTINGS)
      else:
         
         self._default_channels = []
         default_ch_data = []
         try:
            default_ch_data = settings["default channels"]
         except KeyError:
            settings["default channels"] = []
            self._res.save_settings(settings)
         for item in default_ch_data:
            try:
               ch_id = item["id"]
               ch = self._client.search_for_channel(ch_id, serverrestriction=self._server)
               if not ch is None:
                  self._default_channels.append(ch)
            except KeyError:
               continue

         self._channel_timeout = 10
         try:
            self._channel_timeout = int(settings["channel timeout"])
         except (KeyError, ValueError):
            settings["channel timeout"] = self._channel_timeout
            self._res.save_settings(settings)

         self._max_active_temp_channels = 5
         try:
            self._max_active_temp_channels = int(settings["max active temp channels"])
            if self._max_active_temp_channels < 0:
               self._max_active_temp_channels = 5
         except (KeyError, ValueError):
            settings["max active temp channels"] = self._max_active_temp_channels
            self._res.save_settings(settings)

      return

   def _save_settings(self):
      settings = self._res.get_settings()
      settings["channel timeout"] = self._channel_timeout
      settings["max active temp channels"] = self._max_active_temp_channels

      default_channels = []
      for ch in self._default_channels:
         save_object = {}
         save_object["id"] = ch.id
         save_object["name"] = ch.name
         default_channels.append(save_object)
      settings["default channels"] = default_channels

      self._res.save_settings(settings)

   @classmethod
   async def get_instance_async(cls, cmd_names, resources):
      inst = DynamicChannels(cmd_names, resources)
      inst._load_settings()
      await inst._load_channel_dict()
      # fut = asyncio.ensure_future(inst._load_channel_dict)
      # fut.add_done_callback(_awaitable)
      inst._timeout_thread = ChannelTimeoutAndClosure(inst._client, inst)
      for (name, ch) in inst._temp_channel_dict.items():
         inst._timeout_thread.schedule_ch_timeout(ch, inst._channel_timeout)
      inst._timeout_thread.start()
      return inst

   @property
   def cmd_names(self):
      return self._cmd_names

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      if content.startswith("++"):
         content = default_cmd_prefix + self._cmd_names[0] + " open " + content[2:]
      elif content.startswith("+"):
         content = default_cmd_prefix + self._cmd_names[0] + " search " + content[1:]
      return content

   def get_help_summary(self, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_SUMMARY_LINES, cmd_prefix, privilegelevel)

   def get_help_detail(self, substr, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_DETAIL_LINES, cmd_prefix, privilegelevel)

   async def on_message(self, msg):
      ch = msg.channel
      if not ch in self._default_channels:
         self._timeout_thread.schedule_ch_timeout(ch, self._channel_timeout)
      return

   async def process_cmd(self, substr, msg, privilegelevel=0):

      # Command pre-processing
      if substr == "":
         substr = "settings"
      
      # Process the command itself
      # Here, each query command has a different format, as a way of
      # documenting old formats I tried using.
      (left, right) = utils.separate_left_word(substr)
      if left == "search":
         right = utils.convert_to_legal_channel_name(right.strip())
         open_channels = []
         for (ch, close_on_tick) in self._timeout_thread.gen_scheduled_timeouts():
            open_channels.append(ch)
         if right == "":
            buf = "**The following channels are available for re-opening:**"
            buf2 = ""
            for (name, ch) in self._temp_channel_dict.items():
               if not ch in open_channels:
                  buf2 += "\n" + name
            if buf2 == "":
               buf = "Sorry, no channels are available for re-opening."
            else:
               buf += buf2
            await self._client.send_msg(msg, buf)
         else:
            buf = "**The following channels matching `{}`".format(right)
            buf += " are available for re-opening:**"
            buf2 = ""
            for (name, ch) in self._temp_channel_dict.items():
               if (not ch in open_channels) and (right in name):
                  buf2 += "\n" + name
            if buf2 == "":
               buf = "Sorry, no channels matching `{}`".format(right)
               buf += " are available for re-opening."
            else:
               buf += buf2
            await self._client.send_msg(msg, buf)


      elif (left == "open") or (left == "create"):
         right = utils.convert_to_legal_channel_name(right.strip())
         is_default_channel = False
         for ch in self._default_channels:
            if ch.name == right:
               is_default_channel = True
               break
         if is_default_channel:
            buf = "Sorry, `{}` is not available for opening."
            await self._client.send_msg(msg, buf)
         else:
            ch = None
            try:
               ch = self._temp_channel_dict[right]
            except KeyError:
               ch = self._client.create_channel(self._server, right)
               await self._ensure_bot_permissions(ch)
            
            if self._timeout_thread.channel_name_is_scheduled(ch.name):
               await self._client.send_msg(msg, "Channel `" + right + "` is already open.")
            else:
               await self._set_channel_open(ch)
               buf = "Channel opened by user <@{}>.".format(msg.author.id)
               buf += "\nThis will be scheduled to close "
               buf += "{} minutes after detected inactivity.".format(str(self._channel_timeout))
               await self._client.send_msg(msg, buf)
               self._timeout_thread.schedule_ch_timeout(ch, self._channel_timeout)

      elif left == "settings":
         buf = "**Timeout**: " + str(self._channel_timeout) + " minutes"
         if self._max_active_temp_channels < 0:
            buf += "\n**Max Active**: unlimited channels"
         else:
            buf += "\n**Max Active**: " + str(self._max_active_temp_channels) + " channels"
         buf += "\n**Default Channels**:"
         if len(self._default_channels) == 0:
            buf += "\nNONE."
         else:
            for ch in self._default_channels:
               buf += "\n<#{0}> (ID: {0})".format(ch.id)
         if privilegelevel >= PrivilegeLevel.ADMIN:
            pf = self._res.cmd_prefix
            base_cmd = self._cmd_names[0]
            buf += "\n\nChange settings using the following commands:"
            buf += "\n`{} adddefault [channel]`".format(pf + base_cmd)
            buf += "\n`{} removedefault [channel]`".format(pf + base_cmd)
            buf += "\n`{} settimeout [int]`".format(pf + base_cmd)
            buf += "\n`{} setmaxactive [int]`".format(pf + base_cmd)
            buf += " (for unlimited max active, enter `-1`.)"
         await self._client.send_msg(msg, buf)

      elif left == "adddefault":
         new_default = self._client.search_for_channel(right, serverrestriction=self._server)
         if new_default is None:
            await self._client.send_msg(msg, "Error: Channel not found.")
         else:
            self._default_channels.append(new_default)
            self._save_settings()
            await self._client.send_msg(msg, "<#{}> successfully added to default list.".format(new_default.id))

      elif left == "removedefault":
         to_remove = self._client.search_for_channel(right, serverrestriction=self._server)
         if to_remove is None:
            await self._client.send_msg(msg, "Error: Channel not found.")
         if to_remove in self._default_channels:
            self._default_channels.remove(to_remove)
            self._save_settings()
            await self._client.send_msg(msg, "<#{}> successfully removed to default list.".format(to_remove.id))
         else:
            await self._client.send_msg(msg, "Error: Channel is not default.")

      elif left == "settimeout":
         if privilegelevel < PrivilegeLevel.ADMIN:
            raise errors.CommandPrivilegeError
         try:
            new_timeout = int(right)
            if new_timeout < 0:
               await self._client.send_msg(msg, "Error: Timeout value must be >=0 minutes.")
            else:
               self._channel_timeout = new_timeout
               self._save_settings()
               buf = "Timeout set to {} minutes.".format(str(self._channel_timeout))
               buf += "\n\n(Note: Timeout is precise only by the minute. "
               buf += "This means the timeout actually happens anywhere "
               buf += "between {0} and {1} minutes.)".format(str(self._channel_timeout), str(self._channel_timeout + 1))
               await self._client.send_msg(msg, buf)
         except ValueError:
            await self._client.send_msg(msg, "Error: Must enter an integer.")

      elif left == "setmaxactive":
         if privilegelevel < PrivilegeLevel.ADMIN:
            raise errors.CommandPrivilegeError
         try:
            self._max_active_temp_channels = int(right)
            self._save_settings()
            if self._max_active_temp_channels < 0:
               await self._client.send_msg(msg, "Max active channels set to unlimited.")
            else:
               await self._client.send_msg(msg, "Max active channels set to {}.".format(str(self._max_active_temp_channels)))
         except ValueError:
            await self._client.send_msg(msg, "Error: Must enter an integer.")

      else:
         raise errors.InvalidCommandArgumentsError

      return

   async def on_s_channel_delete(self, ch):
      try:
         self._timeout_thread.unschedule_ch_timeout(ch)
      except errors.DoesNotExist:
         pass
      del self._temp_channel_dict[ch.name]
      return

   async def on_s_channel_create(self, ch):
      buf = "TODO: Write this response message."
      await self._client.send_msg(ch, buf)
      self._temp_channel_dict[ch.name] = ch
      self._timeout_thread.schedule_ch_timeout(ch, self._channel_timeout)
      await self._ensure_bot_permissions(ch)
      return

   async def _load_channel_dict(self):
      self._temp_channel_dict = {}
      for ch in self._server.channels:
         self._temp_channel_dict[ch.name] = ch
         await self._ensure_bot_permissions(ch)
      return

   async def _set_channel_open(self, ch):
      await self._client.delete_channel_permissions(ch, self._server.default_role)
      self._client.send_msg(ch, "Verifying that this channel is now open.")
      return

   async def _set_channel_closed(self, ch):
      everyone = self._server.default_role
      allow = discord.Permissions.none()
      deny = discord.Permissions.all()
      await self._client.edit_channel_permissions(ch, everyone, allow=allow, deny=deny)
      self._client.send_msg(ch, "Verifying that this channel is now closed.")
      return

   # Generator, yields all temporary channels.
   def _gen_temp_channels(self):
      for ch in self._server.channels:
         if ch in self._default_channels:
            continue
         yield ch

   async def _ensure_bot_permissions(self, ch):
      me = self._res.me
      allow = discord.Permissions.all()
      deny = discord.Permissions.none()
      await self._client.edit_channel_permissions(ch, me, allow=allow, deny=deny)
      return
   
   


# IMPORTANT: This class is not responsible for checking if a channel
#            is part of the default channels list.
# IMPORTANT: This class also allows for scheduling multiple
class ChannelTimeoutAndClosure(threading.Thread):

   def __init__(self, client, module):
      super(ChannelTimeoutAndClosure, self).__init__()
      self._running = True
      self._client = client
      self._module = module

      self._tick = 0
      self._scheduled = {} # TYPE: Dict<Server: Int>
      return

   def stop(self):
      self._running = False
      return

   # NOTE: This overwrites any previous schedule.
   # TODO: Find out if there are race condition problems.
   def schedule_ch_timeout(self, ch, timeout):
      self._scheduled[ch] = self._tick + timeout + 1
      return

   # TODO: Find out if there are race condition problems.
   def unschedule_ch_timeout(self, ch):
      try:
         del self._scheduled[ch]
      except KeyError:
         raise errors.DoesNotExist
      return

   def run(self):
      print("ENTERING RUN!!!")
      while self._running:
         no_wait_period_set = True
         wait_period = 10080 # wait_period will arbitrarily never exceed 1 week.
         keys_to_remove = []
         for (ch, close_on_tick) in self._scheduled.items():
            close_on_tick -= self._tick
            if close_on_tick <= 0:
               # TODO: This is accessing a private method. FIX IT!!!
               utils.loop.run_until_complete(self._module._set_channel_closed(ch))
               utils.loop.run_forever()
               # fut = asyncio.async(self._module._set_channel_closed, ch)
               # fut.add_done_callback(_awaitable)
               keys_to_remove.append(ch)
               if close_on_tick < 0:
                  print("WARNING: close_on_tick reached <0.") # TODO: Use logging.
            else:
               self._scheduled[ch] = close_on_tick
               if close_on_tick < wait_period:
                  no_wait_period_set = False
         if no_wait_period_set:
            wait_period = 1
         # Keys removed after dict iteration.
         for key in keys_to_remove:
            del self._scheduled[key]

         self._tick = 0
         while self._tick < wait_period:
            print("TICK... " + str(self._tick))
            time.sleep(60) # 60 seconds
            self._tick += 1
      return

   # (Generator) Yields all scheduled timeouts.
   # YIELDS: channel, minutes_until_closure
   def gen_scheduled_timeouts(self):
      for (ch, close_on_tick) in self._scheduled.items():
         yield (ch, close_on_tick)

   def channel_name_is_scheduled(self, ch_name):
      for (ch, close_on_tick) in self._scheduled.items():
         if ch.name == ch_name:
            return True
      return False

async def _awaitable(fut):
   print("done awaiting!")
   return
   




# BACKUP COPY
# # IMPORTANT: This class is not responsible for checking if a channel
# #            is part of the default channels list.
# # IMPORTANT: This class also allows for scheduling multiple
# class ChannelTimeoutAndHandling(threading.Thread):

#    def __init__(self, client, module):
#       self._running = True
#       self._client = client
#       self._module = module

#       self._tick = 0
#       self._scheduled = {} # TYPE: Dict<Server: Int>
#       return

#    def stop(self):
#       self._running = False
#       return

#    # TODO: Find out if there are race condition problems.
#    def schedule_ch_timeout(self, ch, timeout):
#       self._scheduled[ch] = self._tick + timeout + 1
#       return

#    # TODO: Find out if there are race condition problems.
#    # PRECONDITION: assert(self.channel_is_scheduled(ch))
#    def quick_channel_close(self, ch):
#       self._close_channel(ch)
#       del self._scheduled[ch]

#    def run(self):
#       while self._running:
#          no_wait_period_set = True
#          wait_period = 10080 # wait_period will arbitrarily never exceed 1 week.
#          keys_to_remove = []
#          for (ch, close_on_tick) in self._scheduled.items():
#             close_on_tick -= self._tick
#             if close_on_tick <= 0:
#                self.close_channel(ch)
#                keys_to_remove.append(ch)
#                if close_on_tick < 0:
#                   print("WARNING: close_on_tick reached <0.") # TODO: Use logging.
#             else:
#                self._scheduled[ch] = close_on_tick
#                if close_on_tick < wait_period:
#                   no_wait_period_set = False
#          if no_wait_period_set:
#             wait_period = 1
#          # Keys removed after dict iteration.
#          for key in keys_to_remove:
#             del self._scheduled[key]

#          self._tick = 0
#          while self._tick < wait_period:
#             time.sleep(60) # 60 seconds
#             self._tick += 1
#       return

#    # (Generator) Yields all scheduled timeouts.
#    # YIELDS: channel, minutes_until_closure
#    def gen_scheduled_timeouts(self):
#       for (ch, close_on_tick) in self._scheduled.items():
#          yield (ch, close_on_tick)

#    def channel_is_scheduled(self, ch):
#       try:
#          self._scheduled[ch]
#          return True
#       except KeyError
#          return False

#    def channel_name_is_scheduled(self, ch_name):
#       for (ch, close_on_tick) in self._scheduled.items():
#          if ch.name == ch_name:
#             return True
#       return False

#    @classmethod
#    def open_channel(cls, ch):
#       buf = "This channel should be **OPEN** now, but that isn't *fully* implemented yet."
#       self._client.send_msg(ch, buf)
#       return

#    # While this metho
#    @classmethod
#    def close_channel(cls, ch):
#       buf = "This channel should be **CLOSED** now, but that isn't implemented yet."
#       self._client.send_msg(ch, buf)
#       return


