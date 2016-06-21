import sys
import asyncio
import threading
from copy import deepcopy
import re
import traceback
import concurrent
import textwrap

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered
from ..enums import PrivilegeLevel

from ..attributedictwrapper import AttributeDictWrapper

@registered
class DynamicChannels(ServerModule):

   MODULE_NAME = "Dynamic Channels"
   MODULE_SHORT_DESCRIPTION = "Allows users to create temporary channels. (NOT YET FUNCTIONAL.)"
   RECOMMENDED_CMD_NAMES = ["dchannel", "dchannels", "dynamicchannels"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {}

   _HELP_SUMMARY = """
      `{modhelp}` - Temporary channels.
      """

   _default_settings = {
      "default channels": [],
      "channel timeout": 10,
      "max active temp channels": 5,
      "bot flairs": [],
      "max stored last opened": 10,
      "last opened": [], # List of channel IDs
   }

   _re_non_alnum_or_dash = re.compile("[^-0-9a-zA-Z]")

   async def _initialize(self, resources):
      self._res = resources

      self._client = self._res.client
      self._server = self._res.server
      self._default_role = self._server.default_role

      self._default_channels = None
      self._channel_timeout = None # Channel timeout in seconds.
      self._max_active_temp_channels = None # If <0, then there's no limit.
      self._bot_flairs = None
      self._max_stored_last_opened = None
      self._last_opened = None

      await self._load_settings()

      self._scheduler = ChannelCloseScheduler(self._client, self._server, self)
      loop = asyncio.get_event_loop()
      await self._res.start_nonreturning_coro(self._scheduler.run())

      self._res.suppress_autokill(True)
      return

   @property
   def bot_flairs(self):
      return self._bot_flairs

   async def _load_settings(self):
      settings_dict = self._res.get_settings(default=self._default_settings)
      settings = AttributeDictWrapper(settings_dict, self._default_settings)

      self._default_channels = []
      default_ch_data = settings.get("default channels")
      for item in default_ch_data:
         if not "id" in item:
            continue
         ch_id = item["id"]
         if not isinstance(ch_id, str):
            continue
         ch = self._client.search_for_channel(ch_id, serverrestriction=self._server)
         if not ch is None:
            # Missed channels are simply skipped.
            self._default_channels.append(ch)

      self._channel_timeout = settings.get("channel timeout", accept_if=lambda x: 100000 >= x > 0)
      self._max_active_temp_channels = settings.get("max active temp channels", accept_if=lambda x: x <= 100000)

      def no_issues_in_bot_flairs(x):
         if not isinstance(x, list):
            return False
         for i in x:
            if not isinstance(i, str):
               return False
         return True
      self._bot_flairs = settings.get("bot flairs", accept_if=no_issues_in_bot_flairs)

      self._max_stored_last_opened = settings.get("max stored last opened", accept_if=lambda x: 200 >= x > 0)

      self._last_opened = []
      last_opened_data = settings.get("last opened")
      for ch_id in last_opened_data:
         if not isinstance(ch_id, str):
            continue
         ch = self._client.search_for_channel(ch_id, serverrestriction=self._server)
         if not ch is None:
            # Missed channels are simply skipped.
            self._last_opened.append(ch)

      await settings.report_if_changed(self._client, self, server=self._server)
      self._save_settings()
      return

   def _save_settings(self):
      settings = {}
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

      settings["max stored last opened"] = self._max_stored_last_opened
      settings["last opened"] = [x.id for x in self._last_opened]

      self._res.save_settings(settings)
      return

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      if content.startswith("+++"):
         content = default_cmd_prefix + self._res.module_cmd_aliases[0] + " open " + content[3:]
      elif content.startswith("++"):
         content = default_cmd_prefix + self._res.module_cmd_aliases[0] + " search " + content[2:]
      return content

   async def process_cmd(self, substr, msg, privilege_level):
      if substr == "":
         substr = "status"
      return await super(DynamicChannels, self).process_cmd(substr, msg, privilege_level)

   async def on_message(self, msg):
      if self._name_is_default_channel(msg.channel.name):
         try:
            self._scheduler.unschedule_closure(msg.channel)
         except KeyError:
            pass
      else:
         self._scheduler.schedule_closure(msg.channel, self._channel_timeout)
      return

   @cmd.add(_cmdd, "search")
   async def _cmdf_search(self, substr, msg, privilege_level):
      """
      `++` - See a list of the last opened channels.
      `++[string]` - Search list of hidden channels.
      """
      ch_name = utils.convert_to_legal_channel_name(substr)

      if len(ch_name) == 0:
         buf = "**Last {} channels opened:**".format(str(self._max_stored_last_opened))
         listed = 0
         for ch in self._last_opened:
            if listed == self._max_stored_last_opened:
               break
            buf += "\n" + ch.name
            listed += 1
         if listed == 0:
            buf = "No channels were recently opened."
         await self._client.send_msg(msg, buf)
         return

      available_channels = []
      for ch in self._server.channels:
         if self._name_is_default_channel(ch.name) or (ch.type != discord.ChannelType.text):
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
      buf += "\n\nReopen a channel with the command `+++[channel name]`."
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "open", "create")
   async def _cmdf_open(self, substr, msg, privilege_level):
      """`+++[string]` - Create/unhide channel."""
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
      self._add_to_last_opened(ch)
      return

   @cmd.add(_cmdd, "status", "admin", "s", "stat", "settings", default=True)
   @cmd.category("Status")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_status(self, substr, msg, privilege_level):
      """`{cmd}` - A summary of the module's settings."""
      buf = textwrap.dedent("""\
         **Timeout**: {timeout}
         **Max Active**: {max_active}
         **Max Stored Last-Opened Channels**: {max_stored_last_opened}

         **Bot flairs**: {bot_flairs}

         **Default Channels**:
         {default_channels}
         """).strip()

      format_kwargs = {
         "timeout": str(self._channel_timeout) + " minutes",
         "max_active": None, # Placeholder
         "max_stored_last_opened": str(self._max_stored_last_opened),
         "bot_flairs": None, # Placeholder
         "default_channels": None, # Placeholder
      }

      if self._max_active_temp_channels < 0:
         format_kwargs["max_active"] = "unlimited channels"
      else:
         format_kwargs["max_active"] = str(self._max_active_temp_channels) + " channels"

      bot_flairs = ""
      if len(self._bot_flairs) == 0:
         bot_flairs = "*(none)*"
      else:
         for flair_name in self._bot_flairs:
            bot_flairs += flair_name + ", "
         bot_flairs = bot_flairs[:-2]
      format_kwargs["bot_flairs"] = bot_flairs

      default_channels = ""
      if len(self._default_channels) == 0:
         default_channels = "*(none)*"
      else:
         for ch in self._default_channels:
            default_channels += "\n<#{0}> (ID: {0})".format(ch.id)
         default_channels = default_channels[1:]

      buf = buf.format(**format_kwargs)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "scheduled")
   @cmd.category("Status")
   async def _cmdf_debug(self, substr, msg, privilege_level):
      """
      `{cmd}` - View what's scheduled for closure.

      This command gives you the time for closure for each channel, rounded UP to the nearest minute. (i.e. 20 minutes and 1 second will round up to 21 minutes.)
      """
      scheduled = self._scheduler.get_scheduled()
      if len(scheduled) == 0:
         await self._client.send_msg(msg, "No channels are scheduled.")
      else:
         buf = "**The following channels are currently scheduled:**"
         for (ch, timeout) in self._scheduler.get_scheduled():
            buf += "\n<#" + ch.id + "> in " + str(timeout) + " minutes"
         await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "clearscheduled")
   @cmd.category("Admin - Misc")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_debug(self, substr, msg, privilege_level):
      """
      `{cmd}` - Reset the scheduled-for-closure list.

      Each temporary channel has an associated countdown timer which is reset every time a message is sent into the channel.

      This command will clear all currently scheduled temporary channels AND stop their countdown timers temporarily.

      Sending a message into the channel again, however, will start the channel's countdown timer again.
      """
      self._scheduler.unschedule_all()
      await self._client.send_msg(msg, "Scheduled closure list is cleared.")
      return

   @cmd.add(_cmdd, "addbotflair")
   @cmd.category("Admin - Designated Bot Flairs")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_addbotflair(self, substr, msg, privilege_level):
      """`{cmd} [flair name]` - Add a bot flair, identified by name."""
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

   @cmd.add(_cmdd, "removebotflair")
   @cmd.category("Admin - Designated Bot Flairs")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_addbotflair(self, substr, msg, privilege_level):
      """`{cmd} [flair name]` - Remove a bot flair, identified by name."""
      try:
         self._bot_flairs.remove(substr)
         await self._client.send_msg(msg, "`{}` removed as a bot flair.".format(substr))
      except ValueError:
         await self._client.send_msg(msg, "`{}` is not a bot flair.".format(substr))
      self._save_settings()
      return

   @cmd.add(_cmdd, "adddefault")
   @cmd.category("Admin - Adding/Removing default channels")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_adddefault(self, substr, msg, privilege_level):
      """`{cmd} [channel]` - Add a default channel."""
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
      elif new_default in self._default_channels:
         await self._client.send_msg(msg, "Error: <#{}> is already in default channels.".format(new_default.id))
      else:
         self._default_channels.append(new_default)
         self._save_settings()
         await self._client.send_msg(msg, "<#{}> successfully added to default list.".format(new_default.id))
      return

   @cmd.add(_cmdd, "removedefault")
   @cmd.category("Admin - Adding/Removing default channels")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_removedefault(self, substr, msg, privilege_level):
      """`{cmd} [channel]` - Remove a default channel."""
      to_remove = None
      if len(substr) == 0:
         to_remove = msg.channel
      else:
         to_remove = self._client.search_for_channel(substr, serverrestriction=self._server)

      if to_remove is None:
         await self._client.send_msg(msg, "Error: Channel not found.")
      elif to_remove in self._default_channels:
         self._default_channels.remove(to_remove)
         self._save_settings()
         await self._client.send_msg(msg, "<#{}> successfully removed from default list.".format(to_remove.id))
      else:
         await self._client.send_msg(msg, "Error: Channel is not default.")
      return

   @cmd.add(_cmdd, "settimeout")
   @cmd.category("Admin - Misc")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_settimeout(self, substr, msg, privilege_level):
      """
      `{cmd} [int]` - Set the channel closure timeout, in minutes.

      More specifically, this is the time it takes for a channel to close after the last message that was sent into it.
      """
      try:
         new_timeout = int(substr)
      except ValueError:
         await self._client.send_msg(msg, "Error: Must enter an integer.")
         raise errors.OperationAborted

      if new_timeout < 1:
         await self._client.send_msg(msg, "Error: Timeout must be >0 minutes.")
         raise errors.OperationAborted
      elif new_timeout > 100000:
         await self._client.send_msg(msg, "Error: Timeout too large.")
         raise errors.OperationAborted
      
      self._channel_timeout = new_timeout
      self._save_settings()
      await self._client.send_msg(msg, "Timeout set to {} minutes.".format(str(new_timeout)))
      return

   @cmd.add(_cmdd, "setmaxactive")
   @cmd.category("Admin - Misc")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_setmaxactive(self, substr, msg, privilege_level):
      """
      `{cmd} [int]` - Set the maximum active channels.
      `{cmd} -1` - Set maximum active channels to unlimited.
      """
      try:
         new_value = int(substr)
      except ValueError:
         await self._client.send_msg(msg, "Error: Must enter an integer.")
         raise errors.OperationAborted
      
      set_to_message = None

      if self._max_active_temp_channels < 0:
         await self._client.send_msg(msg, "Max active channels set to unlimited.")
         set_to_message = "unlimited"
      elif self._max_active_temp_channels > 100000:
         await self._client.send_msg(msg, "Error: Max active channels is too large.")
         raise errors.OperationAborted
      else:
         set_to_message = str(new_value)
      
      self._max_active_temp_channels = new_value
      self._save_settings()
      await self._client.send_msg(msg, "Max active channels set to {}.".format(set_to_message))
      return

   @cmd.add(_cmdd, "setmaxlastopened")
   @cmd.category("Admin - Misc")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_setmaxactive(self, substr, msg, privilege_level):
      """
      `{cmd} [int]` - Set the maximum stored last opened channels.

      This is to limit the number of channels that appear when you use the open channel command with no arguments.
      """
      try:
         new_value = int(substr)
      except ValueError:
         await self._client.send_msg(msg, "Error: Must enter an integer.")
         raise errors.OperationAborted

      if new_value < 1:
         await self._client.send_msg(msg, "Error: Value must be >0.")
         raise errors.OperationAborted
      elif new_value > 100000:
         await self._client.send_msg(msg, "Error: Value too large.")
         raise errors.OperationAborted
      
      self._max_stored_last_opened = new_value
      self._save_settings()
      await self._client.send_msg(msg, "Max stored last opened channels set to {}.".format(str(new_value)))
      return

   @cmd.add(_cmdd, "clearlastopened")
   @cmd.category("Admin - Misc")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_setmaxactive(self, substr, msg, privilege_level):
      """
      `{cmd} [int]` - Clear the list of last opened channels.
      """
      old_elements = len(self._last_opened)
      self._last_opened = []
      await self._client.send_msg(msg, "{} removed from the last opened list.".format(str(old_elements)))
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

   def _add_to_last_opened(self, channel):
      if not channel in self._last_opened:
         self._last_opened.insert(0, channel)
         del self._last_opened[self._max_stored_last_opened:]
         assert len(self._last_opened) <= self._max_stored_last_opened
         self._save_settings()
      return

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

   # Run this indefinitely.
   async def run(self):
      while True:
         try: 
            print(">>>>>>>>>>>>>>>>>>> DYNAMICCHANNELS TICK!!!")
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
         except concurrent.futures.CancelledError:
            raise # Allow the coroutine to be cancelled.

