import asyncio
import copy
import enum
import re

import discord
import dateutil.parser

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered
from ..enums import PrivilegeLevel

from ..attributedictwrapper import AttributeDictWrapper

@registered
class CustomCmd(ServerModule):

   MODULE_NAME = "Custom Commands"
   MODULE_SHORT_DESCRIPTION = "((No short description...))"
   RECOMMENDED_CMD_NAMES = ["customcmds", "customcmd", "customcommands", "customcommand"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {}

   _HELP_SUMMARY = """
      `{modhelp}` - Custom commands.
      """

   class CmdType(enum.Enum):
      DISABLED = 0 # CURRENTLY UNUSED...
      FIXED_REPLY = 1

   # IMPORTANT NOTE: These settings are meant to look like it's just been
   # retrived from 
   _default_settings = {
      "commands": {
         "rip": {
            "type": "FIXED_REPLY", # Convert to enum!
            "text": "doesnt even deserve a funeral",
            # Expected to add extra fields as I add more functionality.
         },
         # "rip" is an example command.
      },
   }

   async def _initialize(self, resources):
      self._res = resources
      self._client = resources.client

      self._custom_commands = None # Initialize later.

      self._load_settings()

      self._res.suppress_autokill(True)
      return

   # PRECONDITION: isinstance(custcmd_name, str)
   @staticmethod
   def _is_valid_custcmd_name(custcmd_name):
      return (len(custcmd_name) > 0) and utils.re_az_09.fullmatch(custcmd_name)

   # Returns nothing, but throws an exception if an issue is found.
   # PRECONDITION: Type conversions (e.g. string to enum) have already been
   #               made.
   # PRECONDITION: isinstance(custcmd_data, dict)
   @staticmethod
   def _validate_custcmd_data(custcmd_data):
      x = custcmd_data["text"]
      if not (isinstance(x, str) and (len(x) > 0)):
         raise ValueError
      return

   def _load_settings(self):
      settings_dict = self._res.get_settings(default=self._default_settings)
      settings = AttributeDictWrapper(settings_dict, self._default_settings)

      custom_commands = settings.get("commands")
      # Verify each channel data object.
      for (k, v) in custom_commands.items():
         if not (isinstance(k, str) and self._is_valid_custcmd_name(k)):
            raise ValueError

         if not isinstance(v, dict):
            raise ValueError
         v["type"] = self.CmdType[v["type"]] # Failed conversion throws exception.
         self._validate_custcmd_data(v)
         
      self._custom_commands = custom_commands
      return

   # NOTE: This does not carry out very few validity checks.
   def _save_settings(self):
      # Make necessary type conversions.
      custom_commands = copy.deepcopy(self._custom_commands)
      for (k, v) in custom_commands.items():
         v["type"] = v["type"].name
      
      settings = {
         "commands": custom_commands,
      }
      self._res.save_settings(settings)
      return

   async def on_message(self, msg, privilege_level):
      # TODO: Lots of potentially redundant string manipulation, but I suppose
      #       I should've defined things better :/
      #       Better safe than sorry, I guess, hence the redundancy.

      if privilege_level == PrivilegeLevel.NO_PRIVILEGE:
         return # Without warning.

      # Get the command name.
      cmd_prefix = self._res.cmd_prefix.strip()
      content = msg.content.strip()
      if content.startswith(cmd_prefix):
         content = content[len(cmd_prefix):]
         (left, right) = utils.separate_left_word(content)
         if left in self._custom_commands:
            await self._process_custom_command(right, msg, self._custom_commands[left])
         if left == "help":
            (left2, right2) = utils.separate_left_word(right)
            if left2 in self._custom_commands:
               # PLACEHOLDER IMPLEMENTATION
               # Please note: another message will be sent by the real help command function.
               # this might be confusing... so gonna have to figure out a solution for this.
               buf = "`{}` is a custom command with a fixed reply.".format(cmd_prefix + left2)
               await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "add", "create")
   @cmd.category("Custom Command Management")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_add(self, substr, msg, privilege_level):
      """
      `{cmd} [cmd_name] [reply]` - Creates a new fixed-reply command.

      `[cmd_name]` is the name that will invoke the command.
      The command name can only be a combination of lower-case letters and digits.

      `[reply]` is simply any arbitrary string that is used as the fixed reply.
   
      If the custom command already exists, this will overwrite it.

      If the custom command clashes with an actual command, then when the command is invoked, then both commands will be carried out. This is to prevent important commands from being made inaccessible.

      **Examples of usage:**

      `{cmd} ping pong`
      Creates a command `{p}ping`, in which the bot will simply reply "pong".
      """
      (left, right) = utils.separate_left_word(substr)
      if len(self._custom_commands) >= 2000:
         buf = "**Error:** Too many custom commands are registered."
         buf += " Please delete one before creating another."
         await self._client.send_msg(msg, buf)
         return
      if len(left) == 0:
         buf = "**Error:** No arguments has been specified."
         await self._client.send_msg(msg, buf)
         return
      if not self._is_valid_custcmd_name(left):
         buf = "**Error:** Invalid command name `{}`.".format(left)
         buf += "\n Command names must be a combination of lower-case letters"
         buf += " (a-z) and digits (0-9)."
         await self._client.send_msg(msg, buf)
         return
      if len(right) == 0:
         buf = "**Error:** No reply content has been specified."
         await self._client.send_msg(msg, buf)
         return

      custcmd_data = {
         "type": self.CmdType.FIXED_REPLY,
         "text": right,
      }
      self._custom_commands[left] = custcmd_data
      self._save_settings()

      cmd_prefix = self._res.cmd_prefix.strip()
      buf = "Successfully created new custom command `{}`.".format(cmd_prefix + left)
      buf += " Please check that it's correct."
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "remove", "delete", "del")
   @cmd.category("Custom Command Management")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_remove(self, substr, msg, privilege_level):
      """`{cmd} [cmd_name]` - Deletes a custom command."""
      if not substr in self._custom_commands:
         buf = "**Error:** The custom command you specified does not exist."
         await self._client.send_msg(msg, buf)
         return
      
      del self._custom_commands[substr]
      self._save_settings()
      buf = "Successfully deleted the custom command `{}`.".format(substr)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "clear", "removeall", "deleteall", "delall")
   @cmd.category("Custom Command Management")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_clear(self, substr, msg, privilege_level):
      """`{cmd}` - Clears all custom commands."""
      self._custom_commands = {}
      self._save_settings()
      buf = "Successfully cleared all custom commands."
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "list")
   async def _cmdf_list(self, substr, msg, privilege_level):
      """`{cmd}` - Lists all the custom commands set up."""
      if len(self._custom_commands) == 0:
         buf = "**No custom commands are set up.**"
         await self._client.send_msg(msg, buf)
         return

      custcmd_names = ["`" + k + "`" for (k, v) in self._custom_commands.items()]
      custcmd_names.sort()
      buf = "**The following custom commands are set up:**\n"
      buf += ", ".join(custcmd_names)
      await self._client.send_msg(msg, buf)
      return

   async def _process_custom_command(self, substr, msg, custcmd_data):
      assert custcmd_data["type"] == self.CmdType.FIXED_REPLY
      buf = custcmd_data["text"]
      await self._client.send_msg(msg, buf)
      return

   