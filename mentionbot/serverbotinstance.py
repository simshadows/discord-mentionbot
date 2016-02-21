import asyncio
import random
import re
import datetime
import copy

import discord

import utils
from enums import PrivilegeLevel
import errors
import cmd

from servermodulegroup import ServerModuleGroup
from serverpersistentstorage import ServerPersistentStorage
from privilegemanager import PrivilegeManager
from servermodulefactory import ServerModuleFactory

# ServerBotInstance manages everything to do with a particular server.
# IMPORTANT: client is a MentionBot instance!!!
class ServerBotInstance:
   _SECRET_TOKEN = utils.SecretToken()
   
   DEFAULT_COMMAND_PREFIX = "/"

   _RE_MENTIONSTR = re.compile("<@\d+>")

   INIT_MENTIONS_NOTIFY_ENABLED = False

   _cmd_dict = {} # Command Dictionary

   # IMPORTANT: This needs to be parsed with ServerModule._prepare_help_content()
   # TODO: Figure out a neater way of doing this.
   _HELP_SUMMARY_TO_BEGIN = """
**The following commands are available:**
`{pf}source` - Where to get source code.
`{pf}mods` - Get all installed/available modules.
`{pf}uptime` - Get bot uptime.
`{pf}gettime`
>>> PRIVILEGE LEVEL 8000 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
`{pf}say [text]`
`{pf}add [module name]`
`{pf}remove [module name]`
`{pf}prefix [new prefix name]`
>>> PRIVILEGE LEVEL 9001 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
`{pf}iam [@user] [text]`
`{pf}setgame [text]`
`{pf}tempgame [text]`
`{pf}revertgame`
`{pf}setusername [text]`
`{pf}getemail`
`{pf}joinserver [invitelink]`
`{pf}msgcachedebug`
`{pf}msgcachefirst`
`{pf}leaveserver`
`{pf}throwexception`
   """.strip().splitlines()

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

      data = inst._storage.get_server_settings()
      
      modules = []
      for module_name in data["Installed Modules"]:
         try:
            modules.append(await inst._module_factory.new_module_instance(module_name, inst))
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
      if substr.startswith(self._cmd_prefix):
         substr = substr[len(self._cmd_prefix):].strip()
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

   @cmd.add(_cmd_dict, "help")
   async def _cmdf_help(self, substr, msg, privilege_level):
      help_content = self._get_help_content(substr, msg, self.cmd_prefix, privilege_level)
      await self._client.send_msg(msg, help_content)
      return

   @cmd.add(_cmd_dict, "source", "src")
   async def _cmdf_source(self, substr, msg, privilege_level):
      await self._client.send_msg(msg, "https://github.com/simshadows/discord-mentionbot")
      return

   @cmd.add(_cmd_dict, "uptime")
   async def _cmdf_uptime(self, substr, msg, privilege_level):
      buf = "**Bot current uptime:** {}. ".format(utils.seconds_to_string(self.get_presence_time()))
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "mods", "modules")
   async def _cmdf_mods(self, substr, msg, privilege_level):
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

   @cmd.add(_cmd_dict, "time", "gettime", "utc")
   async def _cmdf_time(self, substr, msg, privilege_level):
      await self._client.send_msg(msg, datetime.datetime.utcnow().strftime("My current system time: %c UTC"))
      return

   @cmd.add(_cmd_dict, "say")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_say(self, substr, msg, privilege_level):
      await self._client.send_msg(msg, substr)
      return

   @cmd.add(_cmd_dict, "add", "install", "addmodule")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_add(self, substr, msg, privilege_level):
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
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_remove(self, substr, msg, privilege_level):
      if self._modules.module_is_installed(substr):
         await self._modules.remove_server_module(substr)
         self._storage.remove_module(substr)
         await self._client.send_msg(msg, "`{}` successfully uninstalled.".format(substr))
      else:
         await self._client.send_msg(msg, "`{}` is not installed.".format(substr))
      return

   @cmd.add(_cmd_dict, "prefix", "prefix")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_prefix(self, substr, msg, privilege_level):
      if len(substr) == 0:
         raise errors.InvalidCommandArgumentsError
      self._cmd_prefix = substr
      buf = "`{}` set as command prefix.".format(self._cmd_prefix)
      buf += "\nThe help message is now invoked using `{}help`.".format(self._cmd_prefix)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "iam")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_iam(self, substr, msg, privilege_level):
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

   @cmd.add(_cmd_dict, "setgame")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setgame(self, substr, msg, privilege_level):
      await self._client.set_game_status(substr)
      await self._client.send_msg(msg, "**Game set to:** " + substr)
      return

   @cmd.add(_cmd_dict, "tempgame")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setgame(self, substr, msg, privilege_level):
      await self._client.set_temp_game_status(substr)
      await self._client.send_msg(msg, "**Game temporarily set to:** " + substr)
      return

   @cmd.add(_cmd_dict, "revertgame")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setgame(self, substr, msg, privilege_level):
      await self._client.remove_temp_game_status()
      await self._client.send_msg(msg, "**Reverted game.**")
      return

   @cmd.add(_cmd_dict, "setusername")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setusername(self, substr, msg, privilege_level):
      await self._client.edit_profile(password, username=substr)
      self._bot_name = substr # TODO: Consider making this a function. Or stop using bot_name...
      await self._client.send_msg(msg, "**Username set to:** " + substr)
      return

   @cmd.add(_cmd_dict, "getemail")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_getemail(self, substr, msg, privilege_level):
      await self._client.send_msg(msg, "My email is: " + email)
      return

   @cmd.add(_cmd_dict, "joinserver")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_joinserver(self, substr, msg, privilege_level):
      try:
         await self._client.accept_invite(substr)
         await self._client.send_msg(msg, "Successfully joined a new server.")
      except discord.InvalidArgument:
         await self._client.send_msg(msg, "Failed to join a new server.")
      return

   @cmd.add(_cmd_dict, "leaveserver")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_leaveserver(self, substr, msg, privilege_level):
      await self._client.send_msg(msg, "Bye!")
      await self._client.leave_server(msg.channel.server)
      return

   @cmd.add(_cmd_dict, "msgcachedebug")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_msgcachedebug(self, substr, msg, privilege_level):
      buf = self._client.message_cache_debug_str()
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "msgcachefirst")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_msgcachedebug(self, substr, msg, privilege_level):
      buf = "**Here are the first 20 messages in this channel:**\n"
      count = 1
      for msg_dict in self._client.message_cache_read(msg.server.id, msg.channel.id):
         buf += msg_dict["c"] + "\n"
         if count > 20:
            break
         else:
            count += 1
      await self._client.send_msg(msg, buf[:-1])
      return

   @cmd.add(_cmd_dict, "throwexception")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_throwexception(self, substr, msg, privilege_level):
      raise Exception

   @cmd.add(_cmd_dict, "throwexception2")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_throwexception2(self, substr, msg, privilege_level):
      await self._client.send_message(msg, "A" * 2001)
      await self._client.send_message(msg, "If you're reading this, it failed to throw...")
      return

   def _get_help_content(self, substr, msg, cmd_prefix, privilege_level):
      if substr == "":
         buf = utils.prepare_help_content(self._HELP_SUMMARY_TO_BEGIN, cmd_prefix, privilegelevel=privilege_level)
         buf += "\n"
      else:
         buf = ""
      buf += self._modules.get_help_content(substr, cmd_prefix, privilege_level)
      return buf

   # RETURNS: Bot's current uptime in seconds
   def get_presence_time(self):
      timediff = datetime.datetime.utcnow() - self.initialization_timestamp
      return timediff.seconds


