import sys
import asyncio
import random
import re
import datetime
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
            new_module = await inst._module_factory.new_module_instance(module_name, inst)
            modules.append(new_module)
            await new_module.activate()
         except:
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

   async def on_member_join(self, member):
      await self._modules.on_member_join(member)
      return

   async def on_member_remove(self, member):
      await self._modules.on_member_remove(member)
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
      help_content = await self._get_help_content(substr, msg, self.cmd_prefix, privilege_level)
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

   #######################################
   ### MODULE INFO/MANAGEMENT COMMANDS ###
   #######################################

   @cmd.add(_cmd_dict, "mods", "modules")
   @cmd.category("Module Info/Management")
   async def _cmdf_mods(self, substr, msg, privilege_level):
      """`{cmd}` - View installed and available modules."""
      installed_mods = list(self._modules.gen_module_info())
      buf = ""
      if len(installed_mods) == 0:
         buf = "**No modules are installed.**"
      else:
         installed_mods.sort(key=lambda x: x[0])
         buf_active = ""
         buf_inactive = ""
         for val in installed_mods:
            if val[2]: # IF module is active
               buf_active += "`{}`\n".format(val[0])
            else:
               buf_inactive += "`{}`\n".format(val[0])
         if len(buf_active) != 0:
            buf += "**The following modules are installed and active:**\n"
            buf += buf_active[:-1] # Chop off the extra NL
            buf += "\n\n"
         if len(buf_inactive) != 0:
            buf += "**The following modules are installed but inactive:**\n"
            buf += buf_inactive[:-1] # Chop off the extra NL
            buf += "\n\n"
      
      buf2 = "**The following modules are available for installation:**\n"
      buf3 = ""
      for val in self._module_factory.gen_available_modules():
         not_installed = True
         for val2 in installed_mods:
            if val2[0] == val[0]:
               not_installed = False
               break
         if not_installed:
            buf3 += "`{}`\n".format(val[0])
      if len(buf3) == 0:
         buf += "**No modules are available for installation.**"
      else:
         buf += buf2 + buf3[:-1] # Chop off the extra NL

      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "add", "install", "addmodule")
   @cmd.category("Module Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_add(self, substr, msg, privilege_level):
      """`{cmd} [module name]` - Add a module."""
      if self._module_factory.module_exists(substr):
         if self._modules.module_is_installed(substr):
            await self._client.send_msg(msg, "Error: `{}` is already installed.".format(substr))
         else:
            new_module = await self._module_factory.new_module_instance(substr, self)
            await self._modules.add_server_module(new_module)
            await new_module.activate()
            self._storage.add_module(substr)
            await self._client.send_msg(msg, "`{}` successfully installed.".format(substr))
      else:
         await self._client.send_msg(msg, "Error: `{}` does not exist.".format(substr))
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
         await self._client.send_msg(msg, "Error: `{}` is not installed.".format(substr))
      return

   @cmd.add(_cmd_dict, "activate", "reactivate", "activatemodule", "reactivatemodule")
   @cmd.category("Module Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_activate(self, substr, msg, privilege_level):
      """
      `{cmd} [module name]` - Activate an inactive module.

      Modules are usually automatically killed/deactivated upon encountering an error.
      Modules may also be deactivated manually.
      """
      if self._modules.module_is_installed(substr):
         if self._modules.module_is_active(substr):
            await self._client.send_msg(msg, "Error: `{}` is already active.".format(substr))
         else:
            await self._modules.activate_module(substr)
            await self._client.send_msg(msg, "`{}` successfully activated.".format(substr))
      else:
         await self._client.send_msg(msg, "Error: `{}` is not installed.".format(substr))
      return

   @cmd.add(_cmd_dict, "deactivate", "kill", "deactivatemodule", "killmodule")
   @cmd.category("Module Info/Management")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_activate(self, substr, msg, privilege_level):
      """
      `{cmd} [module name]` - Deactivate an active module.
      """
      if self._modules.module_is_installed(substr):
         if self._modules.module_is_active(substr):
            await self._modules.kill_module(substr)
            await self._client.send_msg(msg, "`{}` successfully deactivated.".format(substr))
         else:
            await self._client.send_msg(msg, "Error: `{}` is already inactive.".format(substr))
      else:
         await self._client.send_msg(msg, "Error: `{}` is not installed.".format(substr))
      return

   ###########################################
   ### PRIVILEGES INFO/MANAGEMENT COMMANDS ###
   ###########################################

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

   @cmd.add(_cmd_dict, "prefix", "predicate", "setprefix", "setpredicate")
   @cmd.category("Admin Commands")
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

   async def _get_help_content(self, substr, msg, cmd_prefix, privilege_level):
      buf = None
      if substr == "":
         buf = cmd.compose_help_summary(self._cmd_dict, privilege_level) + "\n\n"
         buf = buf.format(p="{p}", b="")
         buf2 = await self._modules.get_help_content("", privilege_level)
         buf2 = "\n".join(sorted(buf2.splitlines(), key=lambda e: e.lower()))
         buf += buf2
      else:
         buf = await self._modules.get_help_content(substr, privilege_level)
      return buf.format(p=cmd_prefix)
   
   def get_presence_timedelta(self):
      return datetime.datetime.utcnow() - self.initialization_timestamp


