# TEMP
import urllib.parse as urllibparse

import os
import sys
import asyncio
import random
import re
import datetime
import copy
import traceback

import discord

from . import utils, errors, cmd
from .enums import PrivilegeLevel

from .servermodulegroup import ServerModuleGroup
from .serverpersistentstorage import ServerPersistentStorage
from .privilegemanager import PrivilegeManager
from .servermodulefactory import ServerModuleFactory

# ServerBotInstance manages everything to do with a particular server.
# IMPORTANT: client is a MentionBot instance!!!
class ServerBotInstance:
   _SECRET_TOKEN = utils.SecretToken()
   
   DEFAULT_COMMAND_PREFIX = "/"

   _RE_MENTIONSTR = re.compile("<@\d+>")

   INIT_MENTIONS_NOTIFY_ENABLED = False

   _cmd_dict = {} # Command Dictionary

   @classmethod
   async def get_instance(cls, client, server):
      inst = cls(cls._SECRET_TOKEN)
      inst._client = client
      inst._server = server

      inst._data_directory = inst._client.CACHE_DIRECTORY + "serverdata/" + inst._server.id + "/"
      inst._shared_directory = inst._client.CACHE_DIRECTORY + "shared/"

      inst._cmd_prefix = None
      inst._bot_name = inst._client.user.name # TODO: Move this somewhere else.
      inst._initialization_timestamp = datetime.datetime.utcnow()

      botowner_ID = inst._client.BOTOWNER_ID
      serverowner_ID = inst._server.owner.id

      inst._storage = ServerPersistentStorage(inst._data_directory + "settings.json", inst._server)
      inst._privileges = PrivilegeManager(botowner_ID, serverowner_ID)
      inst._module_factory = await ServerModuleFactory.get_instance(inst._client, inst._server)

      inst._modules = None # Initialize later

      # Load and apply server settings

      privileges_settings_dict = inst._storage.get_bot_command_privilege_settings()
      inst._privileges.apply_json_settings_struct(privileges_settings_dict)

      # TODO: Make the below as neat as the above code.

      data = inst._storage.get_server_settings()
      
      modules = []
      for module_name in data["Installed Modules"]:
         try:
            modules.append(await inst._module_factory.new_module_instance(module_name, inst))
         except:
            print(traceback.format_exc())
            print("Error installing module {}. Skipping.".format(module_name))
      inst._modules = ServerModuleGroup(initial_modules=modules)

      try:
         inst._cmd_prefix = data["cmd prefix"]
      except KeyError:
         inst._cmd_prefix = data["cmd prefix"] = inst.DEFAULT_COMMAND_PREFIX
         
      inst._storage.save_server_settings(data)

      return inst

   def __init__(self, token):
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
      return

   @property
   def client(self):
      return self._client

   @property
   def server(self):
      return self._server

   @property
   def cmd_prefix(self):
      return self._cmd_prefix

   @property
   def data_directory(self):
      return self._data_directory

   @property
   def shared_directory(self):
      return self._shared_directory

   @property
   def initialization_timestamp(self):
      return self._initialization_timestamp
   

   # Call this to process text (to parse for commands).
   async def process_text(self, substr, msg):
      await self._modules.on_message(msg)
      privilege_level = self._privileges.get_privilege_level(msg.author)
      if privilege_level == PrivilegeLevel.NO_PRIVILEGE:
         return # Without warning.
      substr = await self._modules.msg_preprocessor(substr, msg, self._cmd_prefix)

      is_command = False
      bot_mention = "<@{}>".format(str(self._client.user.id))
      bot_mention2 = "<@!{}>".format(str(self._client.user.id))
      if substr.startswith(self._cmd_prefix):
         substr = substr[len(self._cmd_prefix):].strip()
         is_command = True
      elif substr.startswith(bot_mention):
         # If message starts with this bot being mentioned, treat it as a command.
         # This is done as a guaranteed way of invoking commands.
         # Useful when multiple bots share the same command predicate.
         substr = substr[len(bot_mention):].strip()
         is_command = True
      elif substr.startswith(bot_mention2):
         # TODO: Do something about the exclamation mark thing...
         substr = substr[len(bot_mention2):].strip()
         is_command = True

      if is_command:
         print("processing command: {pf}" + utils.str_asciionly(substr)) # Intentional un-substituted "{pf}"
         
         cmd_to_execute = None
         (left, right) = utils.separate_left_word(substr)
         try:
            cmd_to_execute = self._cmd_dict[left]
         except KeyError:
            pass

         if cmd_to_execute is None:
            # Execute a module command. This will also handle command failure.
            await self._modules.process_cmd(substr, msg, privilege_level, silentfail=True)
         else:
            # Execute the core command.
            try:
               if privilege_level < cmd_to_execute.minimum_privilege:
                  raise errors.CommandPrivilegeError
            except AttributeError:
               pass
            await cmd_to_execute(self, right, msg, privilege_level)
      return

   ########################################################################################
   # CORE COMMANDS ########################################################################
   ########################################################################################

   ########################
   ### GENERAL COMMANDS ###
   ########################

   @cmd.add(_cmd_dict, "help")
   async def _cmdf_help(self, substr, msg, privilege_level):
      """
      `{cmd} [command name]` - More help.

      This text should only show when obtaining additional help.
      """
      help_content = self._get_help_content(substr, msg, self.cmd_prefix, privilege_level)
      await self._client.send_msg(msg, help_content)
      return

   @cmd.add(_cmd_dict, "source", "src")
   async def _cmdf_source(self, substr, msg, privilege_level):
      """`{cmd}` - Where to get my source code."""
      await self._client.send_msg(msg, "https://github.com/simshadows/discord-mentionbot")
      return

   @cmd.add(_cmd_dict, "uptime")
   async def _cmdf_uptime(self, substr, msg, privilege_level):
      """`{cmd}` - Get time since initialization."""
      buf = "**Bot current uptime:** {}. ".format(utils.timedelta_to_string(self.get_presence_timedelta()))
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "time", "gettime", "utc")
   async def _cmdf_time(self, substr, msg, privilege_level):
      """`{cmd}` - Get bot's system time in UTC."""
      await self._client.send_msg(msg, datetime.datetime.utcnow().strftime("My current system time: %c UTC"))
      return

   @cmd.add(_cmd_dict, "say")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_say(self, substr, msg, privilege_level):
      """`{cmd} [text]` - Echo's the following text."""
      await self._client.send_msg(msg, substr)
      return

   ##########################
   ### TEMPORARY COMMANDS ###
   ##########################

   # Random commands go here until they find a home in a proper module.

   @cmd.add(_cmd_dict, "lmgtfy", "google", "goog", "yahoo")
   async def _cmdf_say(self, substr, msg, privilege_level):
      """`{cmd} [text]` - Let me google that for you..."""
      if len(substr) == 0:
         raise errors.InvalidCommandArgumentsError
      await self._client.send_msg(msg, "http://lmgtfy.com/?q=" + urllibparse.quote(substr))
      return

   @cmd.add(_cmd_dict, "testbell")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_msgcachedebug(self, substr, msg, privilege_level):
      """`{cmd}`"""
      buf = "<@\a119384097473822727>"
      await self._client.send_msg(msg, buf)
      return

   #######################################
   ### MODULE INFO/MANAGEMENT COMMANDS ###
   #######################################

   @cmd.add(_cmd_dict, "mods", "modules")
   @cmd.category("Module Info/Management")
   async def _cmdf_mods(self, substr, msg, privilege_level):
      """`{cmd}` - View installed and available modules."""
      installed_mods = list(self._modules.gen_module_info())
      if len(installed_mods) == 0:
         buf = "**No modules are installed.**"
      else:
         buf = "**The following modules are installed:**"
         for val in installed_mods:
            buf += "\n`{0}`: {1}".format(val[0], val[1])
      
      buf2 = "\n\n**The following modules are available for installation:**"
      buf3 = ""
      for val in self._module_factory.gen_available_modules():
         not_installed = True
         for val2 in installed_mods:
            if val2[0] == val[0]:
               not_installed = False
               break
         if not_installed:
            buf3 += "\n`{0}`: {1}".format(val[0], val[1])
      if len(buf3) == 0:
         buf += "\n\n**No modules are available for installation.**"
      else:
         buf += buf2 + buf3

      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "add", "install", "addmodule")
   @cmd.category("Module Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_add(self, substr, msg, privilege_level):
      """`{cmd} [module name]` - Add a module."""
      if self._module_factory.module_exists(substr):
         if self._modules.module_is_installed(substr):
            await self._client.send_msg(msg, "`{}` is already installed.".format(substr))
         else:
            new_module = await self._module_factory.new_module_instance(substr, self)
            await self._modules.add_server_module(new_module)
            self._storage.add_module(substr)
            await self._client.send_msg(msg, "`{}` successfully installed.".format(substr))
      else:
         await self._client.send_msg(msg, "`{}` does not exist.".format(substr))
      return

   @cmd.add(_cmd_dict, "remove", "uninstall", "removemodule")
   @cmd.category("Module Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_remove(self, substr, msg, privilege_level):
      """`{cmd} [module name]` - Remove a module."""
      if self._modules.module_is_installed(substr):
         await self._modules.remove_server_module(substr)
         self._storage.remove_module(substr)
         await self._client.send_msg(msg, "`{}` successfully uninstalled.".format(substr))
      else:
         await self._client.send_msg(msg, "`{}` is not installed.".format(substr))
      return

   ###########################################
   ### PRIVILEGES INFO/MANAGEMENT COMMANDS ###
   ###########################################

   @cmd.add(_cmd_dict, "prefix", "prefix")
   @cmd.category("Command Privilege Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_prefix(self, substr, msg, privilege_level):
      """`{cmd} [new prefix]` - Set new command prefix."""
      if len(substr) == 0:
         raise errors.InvalidCommandArgumentsError
      self._cmd_prefix = substr
      buf = "`{}` set as command prefix.".format(self._cmd_prefix)
      buf += "\nThe help message is now invoked using `{}help`.".format(self._cmd_prefix)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "privinfo", "allprivs", "privsinfo", "whatprivs")
   @cmd.category("Command Privilege Info/Management")
   async def _cmdf_privinfo(self, substr, msg, privilege_level):
      """`{cmd}` - Get information on the bot's command privilege system."""
      buf = "This bot has internal command privilege levels to determine what"
      buf += " commands users have access to. This is managed separately from"
      buf += " discord's own privileges."
      buf += "\n\nThe bot command privilege levels from highest to lowest are:"
      privilege_levels_list = sorted(PrivilegeLevel.get_all_values(), key=lambda e: e[1], reverse=True)
      for (priv_obj, priv_value, commonname) in privilege_levels_list:
         buf += "\n`" + commonname + "`"
      # buf += "\n\nThe bot can continue to function without further configuring"
      # buf += " the privilege levels as it defaults to giving the bot owner and"
      # buf += " server owner their special privileges and giving everyone else"
      # buf += " a default level."
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "priv", "privilege", "mypriv")
   @cmd.category("Command Privilege Info/Management")
   async def _cmdf_priv(self, substr, msg, privilege_level):
      """`{cmd}` - Check your command privilege level."""
      buf = await self._get_user_priv_process("", msg)
      buf += "\nFor info on privilege levels, use the command `{}privinfo`.".format(self._cmd_prefix)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "privof", "privilegeof")
   @cmd.category("Command Privilege Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.TRUSTED)
   async def _cmdf_privof(self, substr, msg, privilege_level):
      """`{cmd} [user]` - Check someone's command privilege level."""
      buf = await self._get_user_priv_process(substr, msg)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "userprivsresolved", "userprivilegesresolved")
   @cmd.category("Command Privilege Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.TRUSTED)
   async def _cmdf_userprivsresolved(self, substr, msg, privilege_level):
      """`{cmd}` - Get list of everyone with command privilege levels resolved."""
      priv_levels = {} # FORMAT: {priv_level: [member]}
      for member in self._server.members:
         member_priv_level = self._privileges.get_privilege_level(member)
         try:
            member_list = priv_levels[member_priv_level]
         except KeyError:
            member_list = priv_levels[member_priv_level] = []
         member_list.append(member)

      priv_levels_sorted_list = sorted(priv_levels.items(), key=lambda e: e[0], reverse=True)
      buf = "**Here are the resolved privilege levels for all users:**\n"
      for (priv_level, member_list) in priv_levels_sorted_list:
         buf += "\nPrivilege level `{}`:\n```".format(priv_level.get_commonname())
         for member in sorted(member_list, key=lambda e: member.name.lower()):
            buf += "\n{} (ID: {})".format(member.name, member.id)
         buf += "\n```"
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "userprivs", "userprivileges")
   @cmd.category("Command Privilege Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.TRUSTED)
   async def _cmdf_userprivs(self, substr, msg, privilege_level):
      """`{cmd}` - View user-assigned command privileges."""
      user_privileges = self._privileges.get_user_privileges()
      buf = None
      if len(user_privileges) == 0:
         buf = "No users have been assigned bot command privilege levels."
      else:
         buf = "The following users have been assigned bot command privilege levels:\n```"
         def uname_alphabet_sort(e):
            user_obj = self._client.search_for_user(e[0], enablenamesearch=False, serverrestriction=self._server)
            if user_obj is None:
               return ""
            else:
               return user_obj.name.lower()
         user_privileges = sorted(user_privileges, key=uname_alphabet_sort)
         user_privileges = sorted(user_privileges, key=lambda e: e[1], reverse=True)
         for (user_ID, priv_obj) in user_privileges:
            user_obj = self._client.search_for_user(user_ID, enablenamesearch=False, serverrestriction=self._server)
            buf += "\n{0} (ID: {1}): {2}".format(user_obj.name, user_ID, priv_obj.get_commonname())
         buf += "\n```"
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "roleprivs", "roleprivileges", "flairprivs", "flairprivileges", "tagprivs", "tagprivileges")
   @cmd.category("Command Privilege Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.TRUSTED)
   async def _cmdf_roleprivs(self, substr, msg, privilege_level):
      """`{cmd}` - View role-assigned command privileges."""
      role_privileges = self._privileges.get_role_privileges()
      buf = None
      if len(role_privileges) == 0:
         buf = "No roles have been assigned bot command privilege levels."
      else:
         buf = "The following roles have been assigned bot command privilege levels:\n```"
         role_privileges = sorted(role_privileges, key=lambda e: e[0].lower())
         role_privileges = sorted(role_privileges, key=lambda e: e[1], reverse=True)
         for (role_name, priv_obj) in role_privileges:
            buf += "\n{0}: {1}".format(role_name, priv_obj.get_commonname())
         buf += "\n```"
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "adduserpriv", "adduserprivilege")
   @cmd.category("Command Privilege Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_adduserpriv(self, substr, msg, privilege_level):
      """`{cmd} [user] [privilege level]` - Add a user command privilege."""
      # Required 2 arguments.
      # Argument 1: User.
      (left, right) = utils.separate_right_word(substr)
      user_obj = self._client.search_for_user(left, enablenamesearch=True, serverrestriction=self._server)
      if user_obj is None:
         await self._client.send_msg(msg, "Error: User not found. Aborting.")
         raise errors.OperationAborted
      # Argument 2: Privilege Level
      try:
         priv_obj = PrivilegeLevel.commonname_to_enum(right)
      except errors.DoesNotExist:
         buf = "Error: Level `{}` is not recognized. Aborting.".format(right)
         buf += "\n(For info on privilege levels, use the command `{}privinfo`.)".format(self._cmd_prefix)
         await self._client.send_msg(msg, buf)
         raise errors.OperationAborted

      if priv_obj >= PrivilegeLevel.SERVER_OWNER:
         await self._client.send_msg(msg, "Error: Not allowed to assign that level.")
         raise errors.OperationAborted
      
      self._privileges.assign_user_privileges(user_obj.id, priv_obj)

      # Save settings
      settings_dict = self._privileges.get_json_settings_struct()
      self._storage.save_bot_command_privilege_settings(settings_dict)

      buf = "Successfully assigned level `{0}` to user {1}.".format(right, user_obj.name)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "addrolepriv", "addroleprivilege")
   @cmd.category("Command Privilege Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_addrolepriv(self, substr, msg, privilege_level):
      """`{cmd} [role name] [privilege level]` - Add a role command privilege."""
      # Required 2 arguments.
      # Argument 1: Role.
      # TODO: This is broken because roles can have spaces in them.
      (left, right) = utils.separate_right_word(substr)
      role_obj = utils.flair_name_to_object(self._server, left)
      if role_obj is None:
         await self._client.send_msg(msg, "Error: Role not found. Aborting.")
         raise errors.OperationAborted
      # Argument 2: Privilege Level.
      try:
         priv_obj = PrivilegeLevel.commonname_to_enum(right)
      except errors.DoesNotExist:
         buf = "Error: Level `{}` is not recognized. Aborting.".format(right)
         buf += "\n(For info on privilege levels, use the command `{}privinfo`.)".format(self._cmd_prefix)
         await self._client.send_msg(msg, buf)
         raise errors.OperationAborted

      if priv_obj >= PrivilegeLevel.SERVER_OWNER:
         await self._client.send_msg(msg, "Error: Not allowed to assign that level.")
         raise errors.OperationAborted
      
      self._privileges.assign_role_privileges(left, priv_obj)

      # Save settings
      settings_dict = self._privileges.get_json_settings_struct()
      self._storage.save_bot_command_privilege_settings(settings_dict)

      buf = "Successfully assigned level `{0}` to role {1}.".format(right, left)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "removeuserpriv", "removeuserprivilege")
   @cmd.category("Command Privilege Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_removeuserpriv(self, substr, msg, privilege_level):
      """`{cmd} [user]` - Remove a user command privilege."""
      if len(substr) == 0:
         buf = "Error: No arguments have been entered."
      else:
         user_obj = self._client.search_for_user(substr, enablenamesearch=True, serverrestriction=self._server)
         if user_obj is None:
            buf = "Error: User {} not found.".format(substr)
         else:
            try:
               self._privileges.assign_user_privileges(user_obj.id, None)
               buf = "Successfully unassigned personal command privilege level for {}.".format(user_obj.name)
            except errors.NoRecordExists:
               buf = "Error: {} doesn't have a personally assigned command privilege level.".format(user_obj.name)
      
      # Save settings
      settings_dict = self._privileges.get_json_settings_struct()
      self._storage.save_bot_command_privilege_settings(settings_dict)

      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "removerolepriv", "removeroleprivilege", "removeflairpriv", "removeflairprivilege", "removetagpriv", "removetagprivilege")
   @cmd.category("Command Privilege Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_removerolepriv(self, substr, msg, privilege_level):
      """`{cmd} [role name]` - Remove a role command privilege."""
      if len(substr) == 0:
         buf = "Error: No arguments have been entered."
      else:
         try:
            self._privileges.assign_role_privileges(substr, None)
            buf = "Successfully unassigned role command privilege level for {}.".format(substr)
         except errors.NoRecordExists:
            buf = "Error: {} doesn't have an assigned command privilege level.".format(substr)
      
      # Save settings
      settings_dict = self._privileges.get_json_settings_struct()
      self._storage.save_bot_command_privilege_settings(settings_dict)

      await self._client.send_msg(msg, buf)
      return

   ### Related Services ###

   async def _get_user_priv_process(self, substr, msg):
      user_priv_level = None
      if len(substr) == 0:
         user_obj = msg.author
      else:
         user_obj = self._client.search_for_user(substr, enablenamesearch=True, serverrestriction=self._server)
         if user_obj is None:
            await self._client.send_msg(msg, "User {} not found. Aborting.".format(substr))
            raise errors.OperationAborted
      
      user_priv_level = self._privileges.get_privilege_level(user_obj)
      priv_str = user_priv_level.get_commonname()
      buf = "User {0} has a bot command privilege level of `{1}`.".format(user_obj.name, priv_str)
      return buf

   ###################################################
   ### OTHER GENERAL MANAGEMENT/DEBUGGING COMMANDS ###
   ###################################################

   @cmd.add(_cmd_dict, "iam")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_iam(self, substr, msg, privilege_level):
      """`{cmd} [user] [text]`"""
      (left, right) = utils.separate_left_word(substr)
      if self._RE_MENTIONSTR.fullmatch(left):
         user_to_pose_as = left[2:-1]
         replacement_msg = copy.deepcopy(msg)
         replacement_msg.author = self._client.search_for_user(user_to_pose_as)
         if replacement_msg.author == None:
            return await self._client.send_msg(msg, "Unknown user.")
         replacement_msg.content = right
         await self._client.send_msg(msg, "Executing command as {}: {}".format(replacement_msg.author, replacement_msg.content))
         await self._client.send_msg(msg, "**WARNING: There are no guarantees of the safety of this operation.**")
         await self.process_text(right, replacement_msg) # TODO: Make this call on_message()
      return

   @cmd.add(_cmd_dict, "setgame", "setgamestatus")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setgame(self, substr, msg, privilege_level):
      """`{cmd} [text]`"""
      await self._client.set_game_status(substr)
      await self._client.send_msg(msg, "**Game set to:** " + substr)
      return

   @cmd.add(_cmd_dict, "tempgame")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setgame(self, substr, msg, privilege_level):
      """`{cmd} [text]`"""
      await self._client.set_temp_game_status(substr)
      await self._client.send_msg(msg, "**Game temporarily set to:** " + substr)
      return

   @cmd.add(_cmd_dict, "revertgame")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setgame(self, substr, msg, privilege_level):
      """`{cmd}`"""
      await self._client.remove_temp_game_status()
      await self._client.send_msg(msg, "**Reverted game.**")
      return

   @cmd.add(_cmd_dict, "setusername", "updateusername", "newusername", "setname", "newname")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setusername(self, substr, msg, privilege_level):
      """`{cmd} [text]`"""
      await self._client.edit_profile(None, username=substr)
      self._bot_name = substr # TODO: Consider making this a function. Or stop using bot_name...
      await self._client.send_msg(msg, "**Username set to:** " + substr)
      return

   @cmd.add(_cmd_dict, "setavatar", "updateavatar", "setdp", "newdp")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setusername(self, substr, msg, privilege_level):
      """
      `{cmd} [url]` - Updates avatar to the URL. (Other options are available.)

      If the URL is omitted, the cache file is instead used.

      This file is in cache/updateavatar.
      """
      if len(substr) != 0:
         await self._client.send_msg(msg, "Setting avatar via url...")
         try:
            data = utils.download_from_url(substr)
            await self._client.edit_profile(None, avatar=data)
            await self._client.send_msg(msg, "Avatar changed successfully.")
         except Exception as e:
            print(traceback.format_exc())
            buf = "Failed to set avatar. (Error: `{}`.)".format(str(type(e).__name__))
            await self._client.send_msg(msg, buf)
      elif len(msg.attachments) != 0:
         await self._client.send_msg(msg, "Setting avatar via attached file...")
         # TODO: This code is quite identical to the case above. Fix this!!!
         try:
            data = utils.download_from_url(msg.attachments[0]["url"])
            await self._client.edit_profile(None, avatar=data)
            await self._client.send_msg(msg, "Avatar changed successfully.")
         except Exception as e:
            print(traceback.format_exc())
            buf = "Failed to set avatar. (Error: `{}`.)".format(str(type(e).__name__))
            await self._client.send_msg(msg, buf)
      else:
         await self._client.send_msg(msg, "Setting avatar via saved file...")
         our_dir = self._client.CACHE_DIRECTORY + "updateavatar/"
         # TODO: Make that filename a constant
         # TODO: Nicer cache directory name use?
         utils.mkdir_recursive(our_dir)
         files_list = os.listdir(our_dir)
         if len(files_list) == 0:
            await self._client.send_msg(msg, "Please add a file in `" + our_dir + "`.")
         else:
            operation_failed = False
            try:
               filename = files_list[0]
               filepath = our_dir + filename
               with open(filepath, "rb") as img_file:
                  img_bytes = img_file.read()
               await self._client.edit_profile(None, avatar=img_bytes)
               buf = "Avatar changed successfully with file `" + filename + "`."
               await self._client.send_msg(msg, buf)
            except Exception as e:
               print(traceback.format_exc())
               buf = "Failed to set avatar. (Error: `{}`.)".format(str(type(e).__name__))
               await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "joinserver")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_joinserver(self, substr, msg, privilege_level):
      """`{cmd} [invite link]`"""
      try:
         await self._client.accept_invite(substr)
         await self._client.send_msg(msg, "Successfully joined a new server.")
      except:
         await self._client.send_msg(msg, "Failed to join a new server.")
      return

   @cmd.add(_cmd_dict, "leaveserver")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_leaveserver(self, substr, msg, privilege_level):
      """`{cmd}`"""
      await self._client.send_msg(msg, "Bye!")
      await self._client.leave_server(msg.channel.server)
      return

   @cmd.add(_cmd_dict, "msgcachedebug")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_msgcachedebug(self, substr, msg, privilege_level):
      """`{cmd}`"""
      buf = self._client.message_cache_debug_str()
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "closebot", "quit", "exit")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_closebot(self, substr, msg, privilege_level):
      """`{cmd}`"""
      await self._client.send_msg(msg, "brb killing self")
      sys.exit(0)

   @cmd.add(_cmd_dict, "throwexception", "exception")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_throwexception(self, substr, msg, privilege_level):
      """`{cmd}`"""
      raise Exception

   @cmd.add(_cmd_dict, "throwexception2")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_throwexception2(self, substr, msg, privilege_level):
      """`{cmd}`"""
      await self._client.send_message(msg, "A" * 2001)
      await self._client.send_message(msg, "If you're reading this, it failed to throw...")
      return

   @cmd.add(_cmd_dict, "throwbaseexception", "baseexception")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_throwexception(self, substr, msg, privilege_level):
      """`{cmd}`"""
      raise BaseException

   def _get_help_content(self, substr, msg, cmd_prefix, privilege_level):
      buf = None
      if substr == "":
         buf = cmd.compose_help_summary(self._cmd_dict, privilege_level) + "\n\n"
         buf = buf.format(p="{p}", b="")
         buf2 = self._modules.get_help_content("", privilege_level)
         buf2 = "\n".join(sorted(buf2.splitlines(), key=lambda e: e.lower()))
         buf += buf2
      else:
         buf = self._modules.get_help_content(substr, privilege_level)
      return buf.format(p=cmd_prefix)
   
   def get_presence_timedelta(self):
      return datetime.datetime.utcnow() - self.initialization_timestamp


