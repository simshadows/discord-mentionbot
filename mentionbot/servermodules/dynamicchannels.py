import asyncio
import threading
import copy
import re
import traceback

import discord

import utils
import errors
from enums import PrivilegeLevel
from servermodule import ServerModule
import cmd

class DynamicChannels(ServerModule):
   
   _SECRET_TOKEN = utils.SecretToken()

   RECOMMENDED_CMD_NAMES = ["dchannel"]

   MODULE_NAME = "Dynamic Channels"
   MODULE_SHORT_DESCRIPTION = "Allows users to create temporary channels. (NOT YET FUNCTIONAL.)"

   _HELP_SUMMARY_LINES = """
`+` - See list of hidden channels. (Will cut off at 2000 chars.)
`+[string]` - Search list of hidden channels.
`++[string]` - Create/unhide channel.
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
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

   _re_non_alnum_or_dash = re.compile("[^-0-9a-zA-Z]")

   _cmd_dict = {} # Command Dictionary

   async def _initialize(self, resources):
      self._res = resources

      self._client = self._res.client
      self._server = self._res.server
      self._default_role = self._server.default_role

      self._default_channels = None
      self._channel_timeout = None # Channel timeout in seconds.
      self._max_active_temp_channels = None # If <0, then there's no limit.
      self._bot_flairs = None

      self._load_settings()

      self._scheduler = ChannelCloseScheduler(self._client, self._server, self)
      loop = asyncio.get_event_loop()
      loop.create_task(self._scheduler.run())
      return

   @property
   def bot_flairs(self):
      return self._bot_flairs

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

         self._bot_flairs = []
         try:
            self._bot_flairs = settings["bot flairs"]
            if not isinstance(self._bot_flairs, list):
               raise ValueError
            for e in self._bot_flairs:
               if not isinstance(e, str):
                  raise ValueError
         except (KeyError, ValueError):
            settings["bot flairs"] = self._bot_flairs = []
            self._res.save_settings(settings)

      return

   def _save_settings(self):
      settings = self._res.get_settings()
      settings["channel timeout"] = self._channel_timeout
      settings["max active temp channels"] = self._max_active_temp_channels
      settings["bot flairs"] = self._bot_flairs

      default_channels = []
      for ch in self._default_channels:
         save_object = {}
         save_object["id"] = ch.id
         save_object["name"] = ch.name
         default_channels.append(save_object)
      settings["default channels"] = default_channels

      self._res.save_settings(settings)

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      if content.startswith("++"):
         content = default_cmd_prefix + self._cmd_names[0] + " open " + content[2:]
      elif content.startswith("+"):
         content = default_cmd_prefix + self._cmd_names[0] + " search " + content[1:]
      return content

   async def process_cmd(self, substr, msg, privilege_level):
      if substr == "":
         substr = "status"
      (left, right) = utils.separate_left_word(substr)
      cmd_to_execute = cmd.get(self._cmd_dict, left, privilege_level)
      await cmd_to_execute(self, right, msg, privilege_level)
      return

   async def on_message(self, msg):
      if self._name_is_default_channel(msg.channel.name):
         try:
            self._scheduler.unschedule_closure(msg.channel)
         except KeyError:
            pass
      else:
         self._scheduler.schedule_closure(msg.channel, self._channel_timeout)
      return

   @cmd.add(_cmd_dict, "search")
   async def _cmdf_search(self, substr, msg, privilege_level):
      ch_name = utils.convert_to_legal_channel_name(substr)
      available_channels = []
      restrict = (len(ch_name) != 0)
      for ch in self._server.channels:
         if restrict and (self._name_is_default_channel(ch.name) or (ch.type != discord.ChannelType.text)):
            continue
         if ch_name in ch.name:
            available_channels.append(ch)
      buf = None
      if len(available_channels) == 0:
         buf = "No channels meet the search criteria."
      else:
         buf = "**The following channels are available for re-opening:**"
         for ch in available_channels:
            buf += "\n" + ch.name
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "open", "create")
   async def _cmdf_open(self, substr, msg, privilege_level):
      if len(self._scheduler.get_scheduled()) >= self._max_active_temp_channels >= 0:
         buf = "No more than {}".format(str(self._max_active_temp_channels))
         buf += " active temporary channels are allowed."
         await self._client.send_msg(msg.channel, buf)
         raise errors.OperationAborted

      ch_name = substr.strip().replace(" ", "-").lower()
      await self._chopen_name_check(msg, ch_name)
      ch = self._client.search_for_channel_by_name(ch_name, self._server)
      if ch is None:
         ch = await self._client.create_channel(self._server, ch_name)
      try:
         await utils.open_channel(self._client, ch, self._server, self._bot_flairs)
      except discord.errors.Forbidden:
         await self._client.send_msg(msg.channel, "Bot is not allowed to open that.")
         raise errors.OperationAborted
      self._scheduler.schedule_closure(ch, self._channel_timeout)
      
      buf = "Channel opened by <@{}>.".format(msg.author.id)
      buf += " Closing after {} minutes of inactivity.".format(str(self._channel_timeout))
      await self._client.send_msg(ch, buf)
      await self._client.send_msg(msg, "Channel <#{}> successfully opened.".format(ch.id))
      return

   # @cmd.add(_cmd_dict, "forceopen")
   # @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   # async def _cmdf_forceopen(self, substr, msg, privilege_level):
   #    ch_name = substr.strip().replace(" ", "-")
   #    self._chopen_name_check(msg, ch_name)

   #    await self._client.send_msg(msg, "Scheduled closure list is cleared.")
   #    return

   @cmd.add(_cmd_dict, "status", "admin", "s", "stat", "settings")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_status(self, substr, msg, privilege_level):
      buf = "**Timeout**: " + str(self._channel_timeout) + " minutes"
      if self._max_active_temp_channels < 0:
         buf += "\n**Max Active**: unlimited channels"
      else:
         buf += "\n**Max Active**: " + str(self._max_active_temp_channels) + " channels"
      if len(self._bot_flairs) == 0:
         buf += "\n\n**No bot flairs have been assigned.**"
      else:
         buf += "\n\n**Bot flairs**: "
         for flair_name in self._bot_flairs:
            buf += flair_name + ", "
         buf = buf[:-2]
      buf += "\n\n**Default Channels**:"
      if len(self._default_channels) == 0:
         buf += "\nNONE."
      else:
         for ch in self._default_channels:
            buf += "\n<#{0}> (ID: {0})".format(ch.id)
      if privilege_level >= PrivilegeLevel.ADMIN:
         pf = self._res.cmd_prefix
         base = pf + self._cmd_names[0]
         buf += "\n\n`{} scheduled` to view what's scheduled for closure.".format(base)
         buf += "\n\nOther management commands:"
         buf += "\n`{} adddefault [channel]`".format(base)
         buf += "\n`{} removedefault [channel]`".format(base)
         buf += "\n`{} addbotflair [flair name]`".format(base)
         buf += "\n`{} removebotflair [flair name]`".format(base)
         buf += "\n`{} settimeout [int]`".format(base)
         buf += "\n`{} setmaxactive [int]`".format(base)
         buf += " (for unlimited max active, enter `-1`.)"
         buf += "\n`{} clearscheduled`".format(base)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "scheduled")
   async def _cmdf_debug(self, substr, msg, privilege_level):
      scheduled = self._scheduler.get_scheduled()
      if len(scheduled) == 0:
         await self._client.send_msg(msg, "No channels are scheduled.")
      else:
         buf = "**The following channels are currently scheduled:**"
         for (ch, timeout) in self._scheduler.get_scheduled():
            buf += "\n<#" + ch.id + "> in " + str(timeout) + " minutes"
         await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "clearscheduled")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_debug(self, substr, msg, privilege_level):
      self._scheduler.unschedule_all()
      await self._client.send_msg(msg, "Scheduled closure list is cleared.")
      return

   @cmd.add(_cmd_dict, "addbotflair")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_addbotflair(self, substr, msg, privilege_level):
      if len(substr) == 0:
         raise errors.InvalidCommandArgumentsError
      elif len(utils.flair_names_to_object(self._server, [substr])) == 0:
         await self._client.send_msg(msg, "`{}` is not an existing flair.".format(substr))
         raise errors.OperationAborted

      if not substr in self._bot_flairs:
         self._bot_flairs.append(substr)
         await self._client.send_msg(msg, "`{}` added as a bot flair.".format(substr))
      else:
         await self._client.send_msg(msg, "`{}` is already a bot flair.".format(substr))
      self._save_settings()
      return

   @cmd.add(_cmd_dict, "removebotflair")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_addbotflair(self, substr, msg, privilege_level):
      try:
         self._bot_flairs.remove(substr)
         await self._client.send_msg(msg, "`{}` removed as a bot flair.".format(substr))
      except ValueError:
         await self._client.send_msg(msg, "`{}` is not a bot flair.".format(substr))
      self._save_settings()
      return

   @cmd.add(_cmd_dict, "adddefault")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_adddefault(self, substr, msg, privilege_level):
      new_default = None
      if len(substr) == 0:
         new_default = msg.channel
      else:
         new_default = self._client.search_for_channel(substr, serverrestriction=self._server)
      
      try:
         self._scheduler.unschedule_closure(new_default)
      except KeyError:
         pass

      if new_default is None:
         await self._client.send_msg(msg, "Error: Channel not found.")
      else:
         self._default_channels.append(new_default)
         self._save_settings()
         await self._client.send_msg(msg, "<#{}> successfully added to default list.".format(new_default.id))
      return

   @cmd.add(_cmd_dict, "removedefault")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_removedefault(self, substr, msg, privilege_level):
      to_remove = self._client.search_for_channel(substr, serverrestriction=self._server)
      if to_remove is None:
         await self._client.send_msg(msg, "Error: Channel not found.")
      if to_remove in self._default_channels:
         self._default_channels.remove(to_remove)
         self._save_settings()
         await self._client.send_msg(msg, "<#{}> successfully removed to default list.".format(to_remove.id))
      else:
         await self._client.send_msg(msg, "Error: Channel is not default.")
      return

   @cmd.add(_cmd_dict, "settimeout")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_settimeout(self, substr, msg, privilege_level):
      try:
         new_timeout = int(substr)
         if new_timeout < 1:
            await self._client.send_msg(msg, "Error: Timeout must be >0 minutes.")
         else:
            self._channel_timeout = new_timeout
            self._save_settings()
            await self._client.send_msg(msg, "Timeout set to {} minutes.".format(str(self._channel_timeout)))
      except ValueError:
         await self._client.send_msg(msg, "Error: Must enter an integer.")
      return

   @cmd.add(_cmd_dict, "setmaxactive")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_setmaxactive(self, substr, msg, privilege_level):
      try:
         self._max_active_temp_channels = int(substr)
         self._save_settings()
         if self._max_active_temp_channels < 0:
            await self._client.send_msg(msg, "Max active channels set to unlimited.")
         else:
            await self._client.send_msg(msg, "Max active channels set to {}.".format(str(self._max_active_temp_channels)))
      except ValueError:
         await self._client.send_msg(msg, "Error: Must enter an integer.")
      return

   async def _chopen_name_check(self, msg, ch_name):
      if len(ch_name) < 2:
         await self._client.send_msg(msg, "Channel name must be at least 2 characters long.")
         raise errors.OperationAborted
      elif (ch_name[:1] == "-") or self._re_non_alnum_or_dash.search(ch_name):
         await self._client.send_msg(msg, "`{}` is an illegal channel name.".format(ch_name))
         raise errors.OperationAborted
      elif len(ch_name) > 100:
         await self._client.send_msg(msg, "Channel name can't be larger than 100 characters.")
         raise errors.OperationAborted
      elif self._name_is_default_channel(ch_name):
         await self._client.send_msg(msg, "Can't open a default channel.")
         raise errors.OperationAborted
      return

   def _name_is_default_channel(self, ch_name):
      for ch in self._default_channels:
         if ch.name == ch_name:
            return True
      return False

   # # Generator, yields all temporary channels.
   # def _gen_temp_channels(self):
   #    for channel in self._server.channels:
   #       if channel in self._default_channels:
   #          continue
   #       yield channel

class ChannelCloseScheduler:

   def __init__(self, client, server, module):
      self._client = client
      self._server = server
      self._module = module
      self._scheduled = {} # Maps channel name -> time until closure
      self._running = True
      return

   def schedule_closure(self, channel, timeout_min):
      self._scheduled[channel] = timeout_min + 1
      return

   def unschedule_closure(self, channel):
      del self._scheduled[channel]
      return

   def unschedule_all(self):
      self._scheduled = {}
      return

   def get_scheduled(self):
      return self._scheduled.items()

   def terminate(self):
      self._running = False
      return

   # Run this indefinitely.
   async def run(self):
      while self._running:
         try: 
            print(">>>>>>>>>>>>>>>>>>> TICK!!!")
            to_close = []
            for (ch_name, timeout_min) in self._scheduled.items():
               if timeout_min <= 1:
                  to_close.append(ch_name)
               else:
                  self._scheduled[ch_name] = timeout_min - 1
            for ch_name in to_close:
               del self._scheduled[ch_name]
               ch = self._client.search_for_channel_by_name(ch_name, self._server)
               try:
                  await utils.close_channel(self._client, ch, self._module.bot_flairs)
               except discord.errors.Forbidden:
                  print("!!!!!!!! FAILED TO CLOSE #{}.".format(ch_name))
               except:
                  print(traceback.format_exc())
            await asyncio.sleep(60)
         except Exception:
            print(traceback.format_exc())

