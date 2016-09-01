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
class PMGreetings(ServerModule):

   MODULE_NAME = "Server Greetings"
   MODULE_SHORT_DESCRIPTION = "Greets new users."
   RECOMMENDED_CMD_NAMES = ["servergreeting", "servergreetings"]

   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {} # Empty dict should work...

   _HELP_SUMMARY = """
      `{modhelp}` - Greeting system.
      """

   _MEMBER_NAME_IDENTIFIER = "memname"
   _SERVER_NAME_IDENTIFIER = "servername"

   _SUBSTITUTION_INFO = textwrap.dedent("""
      When setting greeting messages, substitutions can be made.
      `${0}` substitutes into a mention of the new member, and `${1}` substitutes into the server's name.
      If you want to add a literal `${0}`, you can escape `$` by with `$${0}`. Similarly is done with `${1}`.
      """).format(_MEMBER_NAME_IDENTIFIER, _SERVER_NAME_IDENTIFIER).strip()

   _default_settings = {
      "pm_msg_template": "Hey, $memname! Welcome to $servername! :)",
      "ch_msg_template": "Welcome to $servername, $memname!",

      "pm_msg_isenabled": True,
      "ch_msg_isenabled": True,

      "ch_msg_channelid": "123", # Placeholder channel ID to be filled later.
   }

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client
      self._server = self._res.server

      self._pm_msg_template = None # To be loaded.
      self._ch_msg_template = None # To be loaded.

      self._pm_msg_isenabled = None # To be loaded.
      self._ch_msg_isenabled = None # To be loaded.

      self._ch_msg_channelid = None # To be loaded.
      # Stores channel ID as a string.

      self._load_settings()

      self._res.suppress_autokill(True)
      return

   async def _get_help_header_text(self, privilege_level):
      buf = "This module sends personalized greeting messages to new members in channel and via PM.\n\n"
      buf += self._SUBSTITUTION_INFO
      buf += "\n\n**Available Commands:**\n"
      buf = buf.format(self._MEMBER_NAME_IDENTIFIER, self._SERVER_NAME_IDENTIFIER).strip()
      return buf

   def _load_settings(self):
      settings_dict = self._res.get_settings(default=self._default_settings)
      settings = AttributeDictWrapper(settings_dict, self._default_settings)

      self._pm_msg_template = settings.get("pm_msg_template", accept_if=settings.str_not_empty)
      self._ch_msg_template = settings.get("ch_msg_template", accept_if=settings.str_not_empty)

      self._pm_msg_isenabled = settings.get("pm_msg_isenabled")
      self._ch_msg_isenabled = settings.get("ch_msg_isenabled")
      
      self._ch_msg_channelid = settings.get("ch_msg_channelid", accept_if=settings.str_digits_only)
      return

   def _save_settings(self):
      settings = {
         "pm_msg_template": self._pm_msg_template,
         "ch_msg_template": self._ch_msg_template,

         "pm_msg_isenabled": self._pm_msg_isenabled,
         "ch_msg_isenabled": self._ch_msg_isenabled,

         "ch_msg_channelid": self._ch_msg_channelid,
      }
      self._res.save_settings(settings)
      return

   ##################################
   ### COMPULSORY SETTERS/GETTERS ###
   ##################################
   
   # self._ch_msg_channelid
   #
   # While this field may be set from other methods, it is preferable to
   # read it indirectly using this method as it does necessary validation.
   #
   # Returns a channel object of the channel in which an in-channel greeting
   # is to be sent.
   def _get_greeting_channelobj(self):
      ch_id = self._ch_msg_channelid
      assert isinstance(ch_id, str)
      assert utils.re_digits.fullmatch(ch_id)

      ch_obj = self._client.search_for_channel(ch_id, serverrestriction=self._server)
      if ch_obj is None:
         # Then no valid channel exists, so we must get the default channel.
         ch_obj = self._server.default_channel
         assert not ch_obj is None
         self._ch_msg_channelid = ch_obj.id
         assert isinstance(self._ch_msg_channelid, str)
         assert utils.re_digits.fullmatch(self._ch_msg_channelid)
         return ch_obj
      else:
         # Then we found the channel, and we must return it.
         return ch_obj

   ################
   ### COMMANDS ###
   ################

   @cmd.add(_cmdd, "status", "view", "setting", "settings", default=True)
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_status(self, substr, msg, privilege_level):
      """`{cmd}` - Shows all settings."""

      msg_template = textwrap.dedent("""
         **- - - - - Greeting Module Settings - - - - -**

         **PM Greeting Enabled:** {pm_enabled}

         **In-Channel Greeting Enabled:** {ch_enabled}
         **Greeting Channel:** {ch_channel}

         **PM Greeting Template:**
         {pm_template}

         **In-Channel Greeting Template:**
         {ch_template}

         **Other notes:**
         {substitution_info}
         """).strip()

      def yes_or_no(x):
         assert isinstance(x, bool)
         if x:
            return "Yes"
         return "No"

      modulecmd = self._res.cmd_prefix + self._res.module_cmd_aliases[0]

      pm_template = self._pm_msg_template
      if len(pm_template) > 500:
         pm_template = "*(Template exceeds 500 characters. Please view it with the command `{}`.)*"
         pm_template = pm_template.format(modulecmd + " pmview")

      ch_template = self._ch_msg_template
      if len(ch_template) > 500:
         ch_template = "*(Template exceeds 500 characters. Please view it with the command `{}`.)*"
         ch_template = ch_template.format(modulecmd + " chview")

      new_kwargs = {
         "pm_enabled": yes_or_no(self._pm_msg_isenabled),
         "ch_enabled": yes_or_no(self._ch_msg_isenabled),
         "ch_channel": utils.ch_to_mention(self._get_greeting_channelobj()),
         "pm_template": pm_template,
         "ch_template": ch_template,
         "substitution_info": self._SUBSTITUTION_INFO,
      }
      buf = msg_template.format(**new_kwargs)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "pmview")
   @cmd.category("PM Greetings")
   async def _cmdf_pmview(self, substr, msg, privilege_level):
      """
      `{cmd}` - View a copy of the PM greeting message template.
      """
      buf = "**Here's a copy of the PM greeting message template:**\n"
      buf += self._pm_msg_template
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "chview")
   @cmd.category("In-Channel Greetings")
   async def _cmdf_chview(self, substr, msg, privilege_level):
      """
      `{cmd}` - View a copy of the in-channel greeting message template.
      """
      buf = "**Here's a copy of the in-channel greeting message template:**\n"
      buf += self._ch_msg_template
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "pmdemo")
   @cmd.category("PM Greetings")
   async def _cmdf_pmdemo(self, substr, msg, privilege_level):
      """`{cmd}` - Get a personalized version of the greeting message via PM."""
      pm_target = msg.author
      buf = self._get_pm_greeting(pm_target)
      await self._client.send_msg(pm_target, buf)

      await self._client.send_msg(msg, "<@{}>, check your inbox!".format(msg.author.id))
      return

   @cmd.add(_cmdd, "chdemo")
   @cmd.category("In-Channel Greetings")
   async def _cmdf_chdemo(self, substr, msg, privilege_level):
      """`{cmd}` - Get a personalized version of the greeting message."""
      buf = "**- - - - - In-Channel Greeting Demo - - - - -**\n"
      buf += self._get_ch_greeting(msg.author)
      buf += "\n**- - - - - In-Channel Greeting Demo - - - - -**"
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "pmenable")
   @cmd.category("PM Greetings")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_pmenable(self, substr, msg, privilege_level):
      """
      `{cmd} [true/false]` - Enable/disable PM greetings.
      """
      enabled_str = None
      if utils.str_says_true(substr) or (len(substr) == 0):
         self._pm_msg_isenabled = True
         enabled_str = "enabled."
      else:
         self._pm_msg_isenabled = False
         enabled_str = "disabled."
      self._save_settings()

      buf = "PM greetings is now " + enabled_str
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "chenable")
   @cmd.category("In-Channel Greetings")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_chenable(self, substr, msg, privilege_level):
      """
      `{cmd} [true/false]` - Enable/disable in-channel greetings.
      """
      enabled_str = None
      if utils.str_says_true(substr) or (len(substr) == 0):
         self._ch_msg_isenabled = True
         enabled_str = "enabled."
      else:
         self._ch_msg_isenabled = False
         enabled_str = "disabled."
      self._save_settings()

      buf = "In-channel greetings is now " + enabled_str
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "pmtemplate")
   @cmd.category("PM Greetings")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_pmtemplate(self, substr, msg, privilege_level):
      """
      `{cmd} [message contents]` - Set the PM greeting template.

      Messages are personalized using substitution tokens. This allows you to insert the user's name, the server's name, etc.

      For information on what these tokens are, see `{p}help {grp}`.
      """
      if len(substr) == 0:
         await self._client.send_msg(msg, "Error: No content.")
         return
      elif len(substr) > 1800: # This value is arbitrary.
         await self._client.send_msg(msg, "Error: Message is too long.")
         return

      self._pm_msg_template = substr
      self._save_settings()

      await self._client.send_msg(msg, "Successfully set the new PM greeting template. Please double-check.")
      return

   @cmd.add(_cmdd, "chtemplate")
   @cmd.category("In-Channel Greetings")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_chtemplate(self, substr, msg, privilege_level):
      """
      `{cmd} [message contents]` - Set the in-channel greeting template.

      Messages are personalized using substitution tokens. This allows you to insert the user's name, the server's name, etc.

      For information on what these tokens are, see `{p}help {grp}`.
      """
      if len(substr) == 0:
         await self._client.send_msg(msg, "Error: No content.")
         return
      elif len(substr) > 1800: # This value is arbitrary.
         await self._client.send_msg(msg, "Error: Message is too long.")
         return

      self._ch_msg_template = substr
      self._save_settings()

      await self._client.send_msg(msg, "Successfully set the new in-channel greeting template. Please double-check.")
      return

   @cmd.add(_cmdd, "setchannel", "setch")
   @cmd.category("In-Channel Greetings")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_setchannel(self, substr, msg, privilege_level):
      """
      `{cmd} [channel]` - Set the channel to send in-channel greeting messages.
      """
      ch_obj = None
      if len(substr) == 0:
         ch_obj = msg.channel
      else:
         ch_obj = self._client.search_for_channel(substr, enablenamesearch=True, serverrestriction=self._server)

      if ch_obj is None:
         buf = "**Error:** Channel not found. No changes were made."
      else:
         self._ch_msg_channelid = ch_obj.id
         self._save_settings()
         buf = "In-channel greeting messages will now be sent in " + utils.ch_to_mention(ch_obj) + "."
      await self._client.send_msg(msg, buf)
      return

   async def on_member_join(self, member):
      if self._pm_msg_isenabled:
         buf = self._get_pm_greeting(member) # Note: Errors will propagate out.
         await self._client.send_msg(member, buf)
      if self._ch_msg_isenabled:
         buf = self._get_ch_greeting(member) # Note: Errors will propagate out.
         ch_target = self._get_greeting_channelobj()
         await self._client.send_msg(ch_target, buf)
      return

   def _get_pm_greeting(self, new_member):
      mapping = {
         self._MEMBER_NAME_IDENTIFIER: "<@{}>".format(new_member.id),
         self._SERVER_NAME_IDENTIFIER: self._res.server.name,
      }
      return string.Template(self._pm_msg_template).safe_substitute(mapping)

   def _get_ch_greeting(self, new_member):
      mapping = {
         self._MEMBER_NAME_IDENTIFIER: "<@{}>".format(new_member.id),
         self._SERVER_NAME_IDENTIFIER: self._res.server.name,
      }
      return string.Template(self._ch_msg_template).safe_substitute(mapping)
