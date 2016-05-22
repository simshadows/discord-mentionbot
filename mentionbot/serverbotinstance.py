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
import collections
import textwrap

import discord

from . import utils, errors, cmd
from .helpnode import HelpNode
from .enums import PrivilegeLevel

from .servermodulegroup import ServerModuleGroup
from .serverpersistentstorage import ServerPersistentStorage
from .privilegemanager import PrivilegeManager
from .servermodulefactory import ServerModuleFactory

# Registers a core command.
def _core_command(help_page_dict, page_name):
   assert isinstance(page_name, str)
   def function_decorator(function):
      page_commands = help_page_dict[page_name]
      page_commands.append(function)
      return function
   return function_decorator

class CoreCommandsHelpPage(HelpNode):
   def __init__(self):
      self._page_aliases = []
      self._cmd_list = []
      self._cmd_aliases = []
      self._cmd_dict = {}
      self._help_summary = "<<PLACEHOLDER>>"
      self._above_text = "" # This is text that will be added before the
                            # command listing. This must be pre-stripped
                            # then a newline appended to the end.
      return

   # PARAMETER: cmd_obj - A command object to add to the collection.
   def add_command(self, cmd_obj):
      assert hasattr(cmd_obj, "cmd_meta")
      self._cmd_list.append(cmd_obj)
      for alias in cmd_obj.cmd_meta.get_aliases():
         assert not alias in self._cmd_aliases
         self._cmd_aliases.append(alias)
         self._cmd_dict[alias] = cmd_obj
      return

   # PARAMETER: text - Set the help summary text.
   def set_page_aliases(self, alias_list):
      assert isinstance(alias_list, list)
      self._page_aliases = alias_list
      return

   # PARAMETER: text - Set the help summary text.
   def set_help_summary(self, text):
      assert isinstance(text, str)
      self._help_summary = text.strip()
      return

   # PARAMETER: text - Either a string containing text to append to the top
   #                   in get_help_detail(), or None.
   def set_above_text(self, text):
      if text is None:
         self._above_text = ""
      else:
         assert isinstance(text, str)
         self._above_text = text.strip() + "\n\n"
      return

   def get_all_aliases(self):
      return self._cmd_aliases + self._page_aliases

   ################################
   ### HelpNode Implementations ###
   ################################

   async def get_help_detail(self, locator_string, entry_string, privilege_level):
      assert isinstance(locator_string, str) and isinstance(entry_string, str)
      assert isinstance(privilege_level, PrivilegeLevel)
      buf = None
      if entry_string in self._cmd_dict:
         locator_string = entry_string + (" " + locator_string).strip()
      print("LOC: " + locator_string)
      if locator_string is "":
         # Serve the page's help content.
         buf = await cmd.summarise_commands(self._cmd_dict, privilege_level=privilege_level)
         if not self._above_text is None:
            buf = self._above_text + buf
      else:
         # Get the next node's help content.
         (left, right) = utils.separate_left_word(locator_string)
         if left in self._cmd_dict:
            buf = await self._cmd_dict[left].cmd_meta.get_help_detail(right, left, privilege_level)
      return buf

   async def get_help_summary(self, privilege_level):
      assert isinstance(privilege_level, PrivilegeLevel)
      return self._help_summary

   async def node_min_priv(self):
      return PrivilegeLevel.get_lowest_privilege()
      # TODO: Make use of whole-module privilege restrictions in the future.

   async def node_category(self):
      return ""
      # TODO: Make use of categories in the future.

# ServerBotInstance manages everything to do with a particular server.
# IMPORTANT: client is a MentionBot instance!!!
class ServerBotInstance:
   _SECRET_TOKEN = utils.SecretToken()
   
   DEFAULT_COMMAND_PREFIX = "/"

   _RE_MENTIONSTR = re.compile("<@\d+>")

   INIT_MENTIONS_NOTIFY_ENABLED = False

   _cmdd = {} # Command Dictionary
   _helpd = collections.defaultdict(lambda: []) # Used to compile the
                                                # core help pages.
   _help_page_list = [] # Set up at the end of class initialization, this list
                        # holds all help pages to add to ServerModuleGroup in
                        # each ServerBotInstance instance.

   _help_page_above_text = {
      "core": """
         These are your core commands.

         Use them wisely, young Padawan.
         """,
      "admin": """
         Modulezz
         """
   }

   _help_page_summaries = {
      "core": "`{p}help core` - Core commands.",
      "admin": "`{p}help admin` - For managing the bot.",
   }

   @classmethod
   async def get_instance(cls, client, server):
      self = cls(cls._SECRET_TOKEN)
      self._client = client
      self._server = server

      self._data_directory = self._client.CACHE_DIRECTORY + "serverdata/" + self._server.id + "/"
      self._shared_directory = self._client.CACHE_DIRECTORY + "shared/"

      self._cmd_prefix = None
      self._bot_name = self._client.user.name # TODO: Move this somewhere else.
      self._initialization_timestamp = datetime.datetime.utcnow()

      botowner_ID = self._client.BOTOWNER_ID
      serverowner_ID = self._server.owner.id

      self._storage = ServerPersistentStorage(self._data_directory + "settings.json", self._server)
      self._privileges = PrivilegeManager(botowner_ID, serverowner_ID)
      self._module_factory = await ServerModuleFactory.get_instance(self._client, self._server)

      self._modules = None # Initialize later

      # Load and apply server settings

      privileges_settings_dict = self._storage.get_bot_command_privilege_settings()
      self._privileges.apply_json_settings_struct(privileges_settings_dict)

      # TODO: Make the below as neat as the above code.

      data = self._storage.get_server_settings()
      
      modules = []
      for module_name in data["Installed Modules"]:
         try:
            new_module = await self._module_factory.new_module_instance(module_name, self)
            modules.append(new_module)
            await new_module.activate()
         except:
            print("Error installing module {}. Skipping.".format(module_name))
      self._modules = ServerModuleGroup(initial_modules=modules, core_help_pages=cls._help_page_list)

      try:
         self._cmd_prefix = data["cmd prefix"]
      except KeyError:
         self._cmd_prefix = data["cmd prefix"] = self.DEFAULT_COMMAND_PREFIX
         
      self._storage.save_server_settings(data)

      return self

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

      
      bot_mention = "<@{}>".format(str(self._client.user.id))
      bot_mention2 = "<@!{}>".format(str(self._client.user.id))
      
      begins_with_bot_mention = False
      bot_mention_len = None
      match = utils.re_user_mention.match(substr)
      if match:
         uid = utils.umention_str_to_id(substr[match.start():match.end()])
         if uid == str(self._client.user.id):
            begins_with_bot_mention = True
            bot_mention_len = match.end() - match.start()

      is_command = False
      if substr.startswith(self._cmd_prefix):
         substr = substr[len(self._cmd_prefix):].strip()
         is_command = True
      elif begins_with_bot_mention:
         # If message starts with this bot being mentioned, treat it as a command.
         # This is done as a guaranteed way of invoking commands.
         # Useful when multiple bots share the same command predicate.
         substr = substr[bot_mention_len:].strip()
         is_command = True
         if len(substr) == 0:
            substr = "help"

      if is_command:
         print("processing command: {pf}" + utils.str_asciionly(substr)) # Intentional un-substituted "{pf}"
         
         cmd_to_execute = None
         (left, right) = utils.separate_left_word(substr)
         try:
            cmd_to_execute = self._cmdd[left]
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

   #############################
   ### GENERAL CORE COMMANDS ###
   #############################

   @cmd.add(_cmdd, "help")
   @_core_command(_helpd, "core")
   async def _cmdf_help(self, substr, msg, privilege_level):
      """
      `{cmd} [...]` - Retrieve more information about how to use the bot.

      Able to retrieve information on modules and commands.

      **Examples:**

      `{cmd}`
      A summary of where to find more information.

      `{cmd} core`
      More info on all the core commands.

      `{cmd} help uptime`
      More info on the `{p}uptime` command.

      `{cmd} random`
      More info on the `Random` module.

      `{cmd} random coin`
      More info on the `{p}random coin` command from the `Random` module.

      `{cmd} coin`
      Same as `{cmd} random coin`, since `{cmd} coin` is an alias of the command.
      """
      help_content = await self._get_help_content(substr, msg, self.cmd_prefix, privilege_level)
      await self._client.send_msg(msg, help_content)
      return

   @cmd.add(_cmdd, "source", "src", "github", "git")
   @_core_command(_helpd, "core")
   async def _cmdf_source(self, substr, msg, privilege_level):
      """`{cmd}` - Where to get my source code."""
      await self._client.send_msg(msg, "https://github.com/simshadows/discord-mentionbot")
      return

   @cmd.add(_cmdd, "wiki")
   @_core_command(_helpd, "core")
   async def _cmdf_wiki(self, substr, msg, privilege_level):
      """`{cmd}` - A guide on how to use me!"""
      await self._client.send_msg(msg, "I don't have a wiki yet :c")
      return

   @cmd.add(_cmdd, "uptime")
   @_core_command(_helpd, "core")
   async def _cmdf_uptime(self, substr, msg, privilege_level):
      """`{cmd}` - Get time since initialization."""
      buf = "**Bot current uptime:** {}. ".format(utils.timedelta_to_string(self.get_presence_timedelta()))
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "time", "gettime", "utc")
   @_core_command(_helpd, "core")
   async def _cmdf_time(self, substr, msg, privilege_level):
      """`{cmd}` - Get bot's system time in UTC."""
      await self._client.send_msg(msg, datetime.datetime.utcnow().strftime("My current system time: %c UTC"))
      return

   @cmd.add(_cmdd, "priv", "privilege", "mypriv")
   @_core_command(_helpd, "core")
   async def _cmdf_priv(self, substr, msg, privilege_level):
      """`{cmd}` - Check your command privilege level."""
      buf = await self._get_user_priv_process("", msg)
      buf += "\nFor info on privilege levels, use the command `{}privinfo`.".format(self._cmd_prefix)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "mods", "modules")
   @_core_command(_helpd, "core")
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

   @cmd.add(_cmdd, "avatar", "dp", "avatarurl")
   @_core_command(_helpd, "core")
   @cmd.category("Commands for retrieving simple information")
   async def _cmdf_avatar(self, substr, msg, privilege_level):
      """`{cmd} [user]` - Get a user's avatar."""
      substr = substr.strip()
      user = None
      if len(substr) == 0:
         user = msg.author
      else:
         user = self._client.search_for_user(substr, enablenamesearch=True, serverrestriction=msg.server)
         if user is None:
            return await self._client.send_msg(msg, substr + " doesn't even exist m8")

      # Guaranteed to have a user.
      avatar = user.avatar_url
      if avatar == "":
         return await self._client.send_msg(msg, substr + " m8 get an avatar")
      else:
         return await self._client.send_msg(msg, avatar)

   @cmd.add(_cmdd, "user", "whois", "who")
   @_core_command(_helpd, "core")
   @cmd.category("Commands for retrieving simple information")
   async def _cmdf_user(self, substr, msg, privilege_level):
      """`{cmd} [user]` - Get user info."""
      # Get user. Copied from _cmd_avatar()...
      substr = substr.strip()
      user = None
      if len(substr) == 0:
         user = msg.author
      else:
         user = self._client.search_for_user(substr, enablenamesearch=True, serverrestriction=msg.server)
         if user is None:
            return await self._client.send_msg(msg, substr + " doesn't even exist m8")
      
      # Guaranteed to have a user.
      buf = "```"
      buf += "\nID: " + user.id
      buf += "\nName: " + user.name
      buf += "\nAvatar hash: "
      if user.avatar is None:
         buf += "[no avatar]"
      else:
         buf += str(user.avatar)
      buf += "\nJoin date: " + user.joined_at.isoformat() + " UTC"
      buf += "\nServer Deafened: " + str(user.deaf)
      buf += "\nServer Mute: " + str(user.mute)
      buf += "\nServer Roles:"
      for role in user.roles:
         buf += "\n   {0} (ID: {1})".format(role.name.replace("@","@ "), role.id)
      buf += "\n```"
      return await self._client.send_msg(msg, buf)

   @cmd.add(_cmdd, "role", "rolelist")
   @_core_command(_helpd, "core")
   @cmd.category("Commands for retrieving simple information")
   async def _cmdf_rolestats(self, substr, msg, privilege_level):
      """`{cmd} [rolename]` - Get role stats."""
      server = msg.server
      if len(substr) == 0:
         await self._client.send_msg(msg, "Error: Must specify a role.")
         return
      buf = None
      n_matching_roles = 0
      for role in server.roles:
         if role.name == substr:
            n_matching_roles += 1
      if n_matching_roles == 0:
         await self._client.send_msg(msg, "No roles match `{}`.".format(substr))
         return
      matching_members = []
      for member in server.members:
         for role in member.roles[1:]: # Skips over the @everyone role
            if role.name == substr:
               matching_members.append(member)
               break
      if n_matching_roles == 1:
         if len(matching_members) == 0:
            await self._client.send_msg(msg, "No users are in the role `{}`.".format(substr))
            return
         else:
            buf = "**The following users are in the role `{}`:**".format(substr)
      else:
         buf = "{0} roles match the name `{1}`.\n".format(str(n_matching_roles), substr)
         if len(matching_members) == 0:
            buf += "No users are in any of these roles."
            await self._client.send_msg(msg, buf)
            return
         else:
            buf += "**The following users are in at least one of these roles:**"
      buf += "\n```"
      for member in matching_members:
         buf += "\n" + utils.user_to_str(member)
      buf += "\n```"
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "thisserver", "server")
   @_core_command(_helpd, "core")
   @cmd.category("Commands for retrieving simple information")
   async def _cmdf_server(self, substr, msg, privilege_level):
      """`{cmd}` - Get some simple server info and statistics."""
      s = msg.server
      # Count voice and text channels
      text_ch_total = 0
      voice_ch_total = 0
      for channel in s.channels:
         if channel.type == discord.ChannelType.text:
            text_ch_total += 1
         else:
            voice_ch_total += 1

      buf = "```"
      buf += "\nID: " + s.id
      buf += "\nName: " + s.name
      buf += "\nIcon hash: "
      if s.icon is None:
         buf += "[no icon]"
      else:
         buf += str(s.icon)
      buf += "\nRegion: " + str(s.region)
      buf += "\nOwner: {0} (ID: {1})".format(s.owner.name, s.owner.id)
      buf += "\nNumber of roles: " + str(len(s.roles))
      buf += "\nNumber of members: " + str(len(s.members))
      buf += "\nNumber of text channels: " + str(text_ch_total)
      buf += "\nNumber of voice channels: " + str(voice_ch_total)
      buf += "\n```"
      return await self._client.send_msg(msg, buf)

   @cmd.add(_cmdd, "servericon")
   @_core_command(_helpd, "core")
   @cmd.category("Commands for retrieving simple information")
   async def _cmdf_servericon(self, substr, msg, privilege_level):
      """`{cmd}` - Get server icon."""
      if msg.server.icon_url == "":
         return await self._client.send_msg(msg, "This server has no icon.")
      else:
         return await self._client.send_msg(msg, str(msg.server.icon_url))

   ##########################
   ### TEMPORARY COMMANDS ###
   ##########################

   # Random commands go here until they find a home in a proper module.

   @cmd.add(_cmdd, "lmgtfy", "google", "goog", "yahoo")
   @_core_command(_helpd, "core")
   @cmd.category("Other Commands")
   async def _cmdf_say(self, substr, msg, privilege_level):
      """`{cmd} [text]` - Let me google that for you..."""
      if len(substr) == 0:
         raise errors.InvalidCommandArgumentsError
      await self._client.send_msg(msg, "http://lmgtfy.com/?q=" + urllibparse.quote(substr))
      return

   #######################################
   ### MODULE INFO/MANAGEMENT COMMANDS ###
   #######################################

   @cmd.add(_cmdd, "add", "install", "addmodule")
   @_core_command(_helpd, "admin")
   @cmd.category("Module Management")
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

   @cmd.add(_cmdd, "remove", "uninstall", "removemodule")
   @_core_command(_helpd, "admin")
   @cmd.category("Module Management")
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

   @cmd.add(_cmdd, "activate", "reactivate", "activatemodule", "reactivatemodule")
   @_core_command(_helpd, "admin")
   @cmd.category("Module Management")
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

   @cmd.add(_cmdd, "deactivate", "kill", "deactivatemodule", "killmodule")
   @_core_command(_helpd, "admin")
   @cmd.category("Module Management")
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

   @cmd.add(_cmdd, "say")
   @_core_command(_helpd, "admin")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_say(self, substr, msg, privilege_level):
      """`{cmd} [text]` - Echo's the following text."""
      await self._client.send_msg(msg, substr)
      return

   @cmd.add(_cmdd, "privinfo", "allprivs", "privsinfo", "whatprivs")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Command Privileges")
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

   @cmd.add(_cmdd, "privof", "privilegeof")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Command Privileges")
   @cmd.minimum_privilege(PrivilegeLevel.TRUSTED)
   async def _cmdf_privof(self, substr, msg, privilege_level):
      """`{cmd} [user]` - Check someone's command privilege level."""
      buf = await self._get_user_priv_process(substr, msg)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "userprivsresolved", "userprivilegesresolved")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Command Privileges")
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

   @cmd.add(_cmdd, "userprivs", "userprivileges")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Command Privileges")
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

   @cmd.add(_cmdd, "roleprivs", "roleprivileges", "flairprivs", "flairprivileges", "tagprivs", "tagprivileges")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Command Privileges")
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

   @cmd.add(_cmdd, "adduserpriv", "adduserprivilege")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Command Privileges")
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

   @cmd.add(_cmdd, "addrolepriv", "addroleprivilege")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Command Privileges")
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

   @cmd.add(_cmdd, "removeuserpriv", "removeuserprivilege")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Command Privileges")
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

   @cmd.add(_cmdd, "removerolepriv", "removeroleprivilege", "removeflairpriv", "removeflairprivilege", "removetagpriv", "removetagprivilege")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Command Privileges")
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

   @cmd.add(_cmdd, "prefix", "predicate", "setprefix", "setpredicate")
   @_core_command(_helpd, "admin")
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

   @cmd.add(_cmdd, "iam")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_iam(self, substr, msg, privilege_level):
      """`{cmd} [user] [text]`"""
      (left, right) = utils.separate_left_word(substr)
      if utils.re_user_mention.fullmatch(left):
         user_to_pose_as = utils.umention_str_to_id(left)
         replacement_msg = copy.deepcopy(msg)
         replacement_msg.author = self._client.search_for_user(user_to_pose_as)
         if replacement_msg.author == None:
            return await self._client.send_msg(msg, "Unknown user.")
         replacement_msg.content = right
         await self._client.send_msg(msg, "Executing command as {}: {}".format(replacement_msg.author, replacement_msg.content))
         await self._client.send_msg(msg, "**WARNING: There are no guarantees of the safety of this operation.**")
         await self.process_text(right, replacement_msg) # TODO: Make this call on_message()
      return

   @cmd.add(_cmdd, "setgame", "setgamestatus")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setgame(self, substr, msg, privilege_level):
      """`{cmd} [text]`"""
      await self._client.set_game_status(substr)
      await self._client.send_msg(msg, "**Game set to:** " + substr)
      return

   @cmd.add(_cmdd, "tempgame")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setgame(self, substr, msg, privilege_level):
      """`{cmd} [text]`"""
      await self._client.set_temp_game_status(substr)
      await self._client.send_msg(msg, "**Game temporarily set to:** " + substr)
      return

   @cmd.add(_cmdd, "revertgame")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setgame(self, substr, msg, privilege_level):
      """`{cmd}`"""
      await self._client.remove_temp_game_status()
      await self._client.send_msg(msg, "**Reverted game.**")
      return

   @cmd.add(_cmdd, "setusername", "updateusername", "newusername", "setname", "newname")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setusername(self, substr, msg, privilege_level):
      """`{cmd} [text]`"""
      await self._client.edit_profile(None, username=substr)
      self._bot_name = substr # TODO: Consider making this a function. Or stop using bot_name...
      await self._client.send_msg(msg, "**Username set to:** " + substr)
      return

   @cmd.add(_cmdd, "setavatar", "updateavatar", "setdp", "newdp")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
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

   @cmd.add(_cmdd, "joinserver")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_joinserver(self, substr, msg, privilege_level):
      """`{cmd} [invite link]`"""
      try:
         await self._client.accept_invite(substr)
         await self._client.send_msg(msg, "Successfully joined a new server.")
      except:
         await self._client.send_msg(msg, "Failed to join a new server.")
      return

   @cmd.add(_cmdd, "leaveserver")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_leaveserver(self, substr, msg, privilege_level):
      """`{cmd}`"""
      await self._client.send_msg(msg, "Bye!")
      await self._client.leave_server(msg.channel.server)
      return

   @cmd.add(_cmdd, "msgcachedebug")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_msgcachedebug(self, substr, msg, privilege_level):
      """`{cmd}`"""
      buf = self._client.message_cache_debug_str()
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "closebot", "quit", "exit")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_closebot(self, substr, msg, privilege_level):
      """`{cmd}`"""
      await self._client.send_msg(msg, "brb killing self")
      sys.exit(0)

   @cmd.add(_cmdd, "throwexception", "exception")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_throwexception(self, substr, msg, privilege_level):
      """`{cmd}`"""
      raise Exception

   @cmd.add(_cmdd, "throwexception2")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_throwexception2(self, substr, msg, privilege_level):
      """`{cmd}`"""
      await self._client.send_message(msg, "A" * 2001)
      await self._client.send_message(msg, "If you're reading this, it failed to throw...")
      return

   @cmd.add(_cmdd, "throwbaseexception", "baseexception")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_throwexception(self, substr, msg, privilege_level):
      """`{cmd}`"""
      raise BaseException

   @cmd.add(_cmdd, "testbell")
   @_core_command(_helpd, "admin")
   @cmd.category("Bot Owner Only")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_msgcachedebug(self, substr, msg, privilege_level):
      """`{cmd}`"""
      buf = "<@\a119384097473822727>"
      await self._client.send_msg(msg, buf)
      return

   async def _get_help_content(self, substr, msg, cmd_prefix, privilege_level):
      buf = None
      if substr == "[...]":
         buf = textwrap.dedent("""
            Oh, sorry, I meant you can query any available module or command by adding more to the help command you just used.

            `{p}help` gives you a summary of all the other places you can reach via this help command, in order to find more bot commands.

            `{p}help random` gives you a summary of the commands for the module of random number generation commands.

            `{p}help coin` gives you a detailed explanation of what the `{p}coin` command actually does.

            (Note: These commands may not work if the `Random` module is not installed.)
            """)
      else:
         buf = await self._modules.get_help_detail(substr, "", privilege_level)
         if buf is None:
            return "No help content found for `{}`.".format(substr)
         if substr is "":
            buf = textwrap.dedent("""
               To read more about other bot commands/functions:
               **`{p}help [...]`**
               """).strip() + "\n\n" + buf
      return buf.format(p=cmd_prefix, grp="")
   
   def get_presence_timedelta(self):
      return datetime.datetime.utcnow() - self.initialization_timestamp

   # Set up the pages.
   for (page_name, cmd_list) in _helpd.items():
      page = CoreCommandsHelpPage()
      page.set_page_aliases([page_name])
      if page_name in _help_page_above_text:
         above_text = _help_page_above_text[page_name]
         above_text = textwrap.dedent(above_text).strip()
         page.set_above_text(above_text)
      if page_name in _help_page_summaries:
         summary_text = _help_page_summaries[page_name]
         page.set_help_summary(summary_text)
      for cmd_obj in cmd_list:
         page.add_command(cmd_obj)
      _help_page_list.append(page)

