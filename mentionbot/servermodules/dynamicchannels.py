import asyncio
import threading
import copy

import discord

import utils
import errors
from enums import PrivilegeLevel
from servermodule import ServerModule

class DynamicChannels(ServerModule):
   
   _SECRET_TOKEN = utils.SecretToken()

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

   @classmethod
   async def get_instance(cls, cmd_names, resources):
      inst = cls(cls._SECRET_TOKEN)

      inst._res = resources

      inst._client = inst._res.client
      inst._server = inst._res.server
      inst._cmd_names = cmd_names
      inst._default_role = inst._server.default_role

      inst._default_channels = None
      inst._channel_timeout = None # Channel timeout in seconds.
      inst._max_active_temp_channels = None # If <0, then there's no limit.

      inst._load_settings()
      
      return inst

   def __init__(self, token):
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
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

   @property
   def cmd_names(self):
      return self._cmd_names

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      if content.startswith("++"):
         content = default_cmd_prefix + self._cmd_names[0] + " open " + content[2:]
      elif content.startswith("+"):
         content = default_cmd_prefix + self._cmd_names[0] + " search " + content[1:]
      return content

   async def process_cmd(self, substr, msg, privilegelevel=0):

      # Command pre-processing
      if substr == "":
         substr = "settings"
      
      # Process the command itself
      # Here, each query command has a different format, as a way of
      # documenting old formats I tried using.
      (left, right) = utils.separate_left_word(substr)
      if left == "search":
         await self._client.send_msg(msg, "Channel search not yet implemented.")

      elif (left == "open") or (left == "create"):
         await self._client.send_msg(msg, "Channel opening not yet implemented.")

      elif left == "settings":
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
            if new_timeout < 1:
               await self._client.send_msg(msg, "Error: Timeout must be >0 seconds.")
            else:
               self._channel_timeout = new_timeout
               self._save_settings()
               await self._client.send_msg(msg, "Timeout set to {} seconds.".format(str(self._channel_timeout)))
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

   # Generator, yields all temporary channels.
   def _gen_temp_channels(self):
      for channel in self._server.channels:
         if channel in self._default_channels:
            continue
         yield channel

   

