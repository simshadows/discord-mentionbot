import asyncio
import collections
import string
import textwrap

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered
from ..enums import PrivilegeLevel

from ..attributedictwrapper import AttributeDictWrapper

@registered
class SimpleLogger(ServerModule):

   MODULE_NAME = "Simple Event Logger"
   MODULE_SHORT_DESCRIPTION = "For logging basic events into a channel."
   RECOMMENDED_CMD_NAMES = ["simplelogger"]

   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {} # Empty dict should work...

   _HELP_SUMMARY = """
      `{modhelp}` - Simple event logger.
      """

   _default_settings = {
      "ch_id": "123", # Placeholder channel ID to be filled later.

      "ena_on_bot_startup": False,

      "ena_on_member_join": True,
      "ena_on_member_remove": True,
      "ena_on_member_ban": True,
      "ena_on_member_unban": True,
   }

   EventAttrName = collections.namedtuple("EventAttrName", ["attr_name", "settings_key"])
   _event_dict = {
      "on_bot_startup": EventAttrName("_ena_on_bot_startup", "ena_on_bot_startup"),
      "on_member_join": EventAttrName("_ena_on_member_join", "ena_on_member_join"),
      "on_member_remove": EventAttrName("_ena_on_member_remove", "ena_on_member_remove"),
      "on_member_ban": EventAttrName("_ena_on_member_ban", "ena_on_member_ban"),
      "on_member_unban": EventAttrName("_ena_on_member_unban", "ena_on_member_unban"),

      # This dictionary allows for easy iteration and reference of field names
      # and settings keys where appropriate, making use of getattr() and setattr().
   }
   _event_list = [v for (k, v) in _event_dict.items()]

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client
      self._server = self._res.server

      self._ch_id = None # To be loaded.

      # Event Enable Flags
      # These are typically accessed with _event_dict or _event_list
      self._ena_on_bot_startup = None # To be loaded.
      self._ena_on_member_join = None # To be loaded.
      self._ena_on_member_remove = None # To be loaded.
      self._ena_on_member_ban = None # To be loaded.
      self._ena_on_member_unban = None # To be loaded.

      self._load_settings()

      if self._ena_on_bot_startup:
         await self._send_log_message("Initialization complete.")

      self._res.suppress_autokill(True)
      return

   def _load_settings(self):
      settings_dict = self._res.get_settings(default=self._default_settings)
      settings = AttributeDictWrapper(settings_dict, self._default_settings)
      
      self._ch_id = settings.get("ch_id", accept_if=settings.str_digits_only)

      # Event Enable Flags
      for event in self._event_list:
         setattr(self, event.attr_name, settings.get(event.settings_key))
         # EQUIVALENT: self._attribute = settings.get(setting_key)
      
      return

   def _save_settings(self):
      settings = {
         "ch_id": self._ch_id,
      }

      # Event Enable Flags
      for event in self._event_list:
         assert isinstance(getattr(self, event.attr_name), bool)
         settings[event.settings_key] = getattr(self, event.attr_name)

      self._res.save_settings(settings)
      return

   async def _get_help_header_text(self, privilege_level):
      buf = textwrap.dedent("""
         This module sends simple server event logs to a specified channel on the server. This makes it easy for server administration to keep track of what's happening.
         """).strip()
      return buf

   ##################################
   ### COMPULSORY SETTERS/GETTERS ###
   ##################################
   
   # self._ch_id
   #
   # While this field may be set from other methods, it is preferable to
   # read it indirectly using this method as it does necessary validation.
   #
   # Returns a channel object of the channel in which log messages are to be
   # sent to.
   def _get_channelobj(self):
      ch_id = self._ch_id
      assert isinstance(ch_id, str) and utils.re_digits.fullmatch(ch_id)

      ch_obj = self._client.search_for_channel(ch_id, serverrestriction=self._server)
      if ch_obj is None:
         # Then no valid channel exists, so we must get the default channel.
         ch_obj = self._server.default_channel
         assert not ch_obj is None
         self._ch_id = ch_obj.id
         assert isinstance(self._ch_id, str)
         assert utils.re_digits.fullmatch(self._ch_id)
         return ch_obj
      else:
         # Then we found the channel, and we must return it.
         return ch_obj

   ################
   ### COMMANDS ###
   ################

   @cmd.add(_cmdd, "status", "settings", "setting", default=True)
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_status(self, substr, msg, privilege_level):
      """
      `{cmd}` - View the module's settings.
      """
      
      msg_template = textwrap.dedent("""
         **- - - - - Simple Logger Module Settings - - - - -**

         **Log messages are being sent to:** {ch}

         **Events Enabled:**
         {events}

         To enable {example_event} to be logged, use the command:
         `{module_cmd} enable {example_event}`
         To disable {example_event} logging, use the command:
         `{module_cmd} disable {example_event}`
         Similar commands exist for the other events.
         """).strip()

      def enabled_or_disabled(x):
         assert isinstance(x, bool)
         if x:
            return "Enabled"
         return "Disabled"

      events_lines = []
      for (event_name, event) in self._event_dict.items():
         buf = event_name + ": "
         buf += enabled_or_disabled(getattr(self, event.attr_name))
         events_lines.append(buf)

      example_event = list(self._event_dict.items())[0][0]
      module_cmd = self._res.cmd_prefix + self._res.module_cmd_aliases[0]

      new_kwargs = {
         "ch": utils.ch_to_mention(self._get_channelobj()),
         "events": "\n".join(events_lines),
         "example_event": example_event,
         "module_cmd": module_cmd,
      }
      buf = msg_template.format(**new_kwargs)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "enable", "ena")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_enable(self, substr, msg, privilege_level):
      """
      `{cmd} [event name]` - Enable the logging of a particular event.
      """
      event_name = substr.lower()
      if not event_name in self._event_dict:
         await self._client.send_msg(msg, "**Error:** `{}` is not a recognized event.".format(substr))
         return

      attr_name = self._event_dict[event_name].attr_name
      setattr(self, attr_name, True)
      self._save_settings()

      ch_str = utils.ch_to_mention(self._get_channelobj())
      buf = "Simple Logger will now log `{}` events in {}.".format(event_name, ch_str)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "disable", "dis", "disa")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_disable(self, substr, msg, privilege_level):
      """
      `{cmd} [event name]` - Disable the logging of a particular event.
      """
      event_name = substr.lower()
      if not event_name in self._event_dict:
         await self._client.send_msg(msg, "**Error:** `{}` is not a recognized event.".format(substr))
         return

      attr_name = self._event_dict[event_name].attr_name
      setattr(self, attr_name, False)
      self._save_settings()

      buf = "Simple Logger will no longer log `{}` events.".format(event_name)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "setchannel", "setch")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_setchannel(self, substr, msg, privilege_level):
      """
      `{cmd} [channel]` - Set the channel to send log messages to.
      """
      ch_obj = None
      if len(substr) == 0:
         ch_obj = msg.channel
      else:
         ch_obj = self._client.search_for_channel(substr, enablenamesearch=True, serverrestriction=self._server)

      if ch_obj is None:
         buf = "**Error:** Channel not found. No changes were made."
      else:
         self._ch_id = ch_obj.id
         self._save_settings()
         buf = "Log messages will now be directed to " + utils.ch_to_mention(ch_obj) + "."
         if ch_obj != msg.channel:
            buf0 = "This channel is now set to receive log messages."
            await self._send_log_message(buf0)
      await self._client.send_msg(msg, buf)
      return

   #####################
   ### Logged Events ###
   #####################

   async def on_member_join(self, member):
      if self._ena_on_member_join:
         await self._send_log_message("A new user joined the server: " + utils.user_to_str(member))
      return

   async def on_member_remove(self, member):
      if self._ena_on_member_remove:
         await self._send_log_message("A user left the server (or was kicked): " + utils.user_to_str(member))
      return

   async def on_member_ban(self, member):
      if self._ena_on_member_ban:
         await self._send_log_message("A user has been banned: " + utils.user_to_str(member))
      return

   async def on_member_unban(self, user):
      if self._ena_on_member_unban:
         await self._send_log_message("A user has been unbanned: " + utils.user_to_str(user))
      return

   ###############
   ### Helpers ###
   ###############

   async def _send_log_message(self, content):
      assert isinstance(content, str) and len(content) > 0
      buf = content
      ch_target = self._client.search_for_channel(self._ch_id, serverrestriction=self._server)
      await self._client.send_msg(ch_target, buf)
      return
