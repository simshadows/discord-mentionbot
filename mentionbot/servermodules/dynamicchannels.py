import asyncio
import threading
import copy

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

   _cmd_dict = {} # Command Dictionary

   async def _initialize(self, resources):
      self._res = resources

      self._client = self._res.client
      self._server = self._res.server
      self._default_role = self._server.default_role

      self._default_channels = None
      self._channel_timeout = None # Channel timeout in seconds.
      self._max_active_temp_channels = None # If <0, then there's no limit.

      self._load_settings()
      return

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

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      if content.startswith("++"):
         content = default_cmd_prefix + self._cmd_names[0] + " open " + content[2:]
      elif content.startswith("+"):
         content = default_cmd_prefix + self._cmd_names[0] + " search " + content[1:]
      return content

   async def process_cmd(self, substr, msg, privilegelevel=0):
      if substr == "":
         substr = "settings"
      (left, right) = utils.separate_left_word(substr)
      cmd_to_execute = cmd.get(self._cmd_dict, left, privilegelevel)
      await cmd_to_execute(self, right, msg, privilegelevel)
      return

   @cmd.add(_cmd_dict, "search")
   async def _cmdf_search(self, substr, msg, privilege_level):
      await self._client.send_msg(msg, "Channel search not yet implemented.")
      return

   @cmd.add(_cmd_dict, "open", "create")
   async def _cmdf_open(self, substr, msg, privilege_level):
      await self._client.send_msg(msg, "Channel opening not yet implemented.")
      return

   @cmd.add(_cmd_dict, "settings")
   async def _cmdf_settings(self, substr, msg, privilege_level):
      buf = "**Timeout**: " + str(self._channel_timeout) + " seconds"
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
      return

   @cmd.add(_cmd_dict, "adddefault")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_adddefault(self, substr, msg, privilege_level):
      new_default = self._client.search_for_channel(substr, serverrestriction=self._server)
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
         new_timeout = int(right)
         if new_timeout < 1:
            await self._client.send_msg(msg, "Error: Timeout must be >0 seconds.")
         else:
            self._channel_timeout = new_timeout
            self._save_settings()
            await self._client.send_msg(msg, "Timeout set to {} seconds.".format(str(self._channel_timeout)))
      except ValueError:
         await self._client.send_msg(msg, "Error: Must enter an integer.")
      return

   @cmd.add(_cmd_dict, "setmaxactive")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_setmaxactive(self, substr, msg, privilege_level):
      try:
         self._max_active_temp_channels = int(right)
         self._save_settings()
         if self._max_active_temp_channels < 0:
            await self._client.send_msg(msg, "Max active channels set to unlimited.")
         else:
            await self._client.send_msg(msg, "Max active channels set to {}.".format(str(self._max_active_temp_channels)))
      except ValueError:
         await self._client.send_msg(msg, "Error: Must enter an integer.")
      return

   # Generator, yields all temporary channels.
   def _gen_temp_channels(self):
      for channel in self._server.channels:
         if channel in self._default_channels:
            continue
         yield channel

   

