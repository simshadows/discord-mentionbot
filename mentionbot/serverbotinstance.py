import asyncio
import random
import re
import datetime
import copy

import discord

import utils
from enums import PrivilegeLevel
import errors
import clientextended

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

   # Command Dictionaries
   _cmd = {}

   # IMPORTANT: This needs to be parsed with ServerModule._prepare_help_content()
   # TODO: Figure out a neater way of doing this.
   _HELP_SUMMARY_TO_BEGIN = """
**The following commands are available:**
`{pf}source` - Where to get source code.
`{pf}mods` - Get all installed/available modules.
`{pf}uptime` - Get bot uptime.
>>> PRIVILEGE LEVEL 8000 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
`{pf}say [text]`
`{pf}add [module name]`
`{pf}remove [module name]`
`{pf}prefix [new prefix name]`
   """.strip().splitlines()

   _HELP_ADMIN = """
>>> PRIVILEGE LEVEL 9001 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
`{pf}bo iam [@user] [text]`
`{pf}bo gettime`
`{pf}bo setgame [text]`
`{pf}bo setusername [text]`
`{pf}bo getemail`
`{pf}bo joinserver [invitelink]`
`{pf}bo leaveserver`
`{pf}bo throwexception`
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
         return
      substr = await self._modules.msg_preprocessor(substr, msg, self._cmd_prefix)
      if substr.startswith(self._cmd_prefix):
         substr = substr[len(self._cmd_prefix):].strip()
         print("processing command: {pf}" + substr) # Intentional un-substituted "{pf}"
         
         cmd_to_execute = None
         (left, right) = utils.separate_left_word(substr)
         try:
            cmd_to_execute = self._cmd[left]
         except KeyError:
            pass

         if cmd_to_execute is None:
            # Execute a module command. This will also handle command failure.
            await self._modules.process_cmd(substr, msg, privilegelevel=privilege_level, silentfail=True)
         else:
            # Execute the core command.
            await cmd_to_execute(self, right, msg, privilege_level)
      return

   ########################################################################################
   # CORE COMMANDS ########################################################################
   ########################################################################################

   @utils.cmd(_cmd, "help")
   async def _help(self, substr, msg, privilege_level):
      help_content = self._get_help_content(substr, msg, self.cmd_prefix, privilege_level)
      await self._client.send_msg(msg, help_content)
      return

   @utils.cmd(_cmd, "source", "src")
   async def _source(self, substr, msg, privilege_level):
      await self._client.send_msg(msg, "https://github.com/simshadows/discord-mentionbot")
      return

   @utils.cmd(_cmd, "uptime")
   async def _uptime(self, substr, msg, privilege_level):
      buf = "**Bot current uptime:** {}. ".format(utils.seconds_to_string(self.get_presence_time()))
      await self._client.send_msg(msg, buf)
      return

   @utils.cmd(_cmd, "mods", "modules")
   async def _mods(self, substr, msg, privilege_level):
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

   @utils.cmd(_cmd, "time", "gettime")
   async def _PLACEHOLDER(self, substr, msg, privilege_level):
      await self._client.send_msg(msg, datetime.datetime.utcnow().strftime("My current system time: %c UTC"))
      return

   @utils.cmd(_cmd, "say")
   async def _say(self, substr, msg, privilege_level):
      if privilege_level < PrivilegeLevel.ADMIN:
         raise errors.CommandPrivilegeError
      await self._client.send_msg(msg, substr)
      return

   @utils.cmd(_cmd, "add", "install", "addmodule")
   async def _add(self, substr, msg, privilege_level):
      if privilege_level < PrivilegeLevel.ADMIN:
         raise errors.CommandPrivilegeError
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

   @utils.cmd(_cmd, "remove", "uninstall", "removemodule")
   async def _remove(self, substr, msg, privilege_level):
      if privilege_level < PrivilegeLevel.ADMIN:
         raise errors.CommandPrivilegeError
      if self._modules.module_is_installed(substr):
         await self._modules.remove_server_module(substr)
         self._storage.remove_module(substr)
         await self._client.send_msg(msg, "`{}` successfully uninstalled.".format(substr))
      else:
         await self._client.send_msg(msg, "`{}` is not installed.".format(substr))
      return

   @utils.cmd(_cmd, "prefix", "prefix")
   async def _prefix(self, substr, msg, privilege_level):
      if privilege_level < PrivilegeLevel.ADMIN:
         raise errors.CommandPrivilegeError
      if len(substr) == 0:
         raise errors.InvalidCommandArgumentsError
      self._cmd_prefix = substr
      buf = "`{}` set as command prefix.".format(self._cmd_prefix)
      buf += "\nThe help message is now invoked using `{}help`.".format(self._cmd_prefix)
      await self._client.send_msg(msg, buf)
      return

   @utils.cmd(_cmd, "iam")
   async def _PLACEHOLDER(self, substr, msg, privilege_level):
      if privilege_level != PrivilegeLevel.BOT_OWNER:
         raise errors.CommandPrivilegeError
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

   @utils.cmd(_cmd, "setgame")
   async def _PLACEHOLDER(self, substr, msg, privilege_level):
      if privilege_level != PrivilegeLevel.BOT_OWNER:
         raise errors.CommandPrivilegeError
      await self._client.set_game_status(substr)
      await self._client.send_msg(msg, "**Game set to:** " + substr)
      return

   @utils.cmd(_cmd, "setusername")
   async def _PLACEHOLDER(self, substr, msg, privilege_level):
      if privilege_level != PrivilegeLevel.BOT_OWNER:
         raise errors.CommandPrivilegeError
      await self._client.edit_profile(password, username=substr)
      self._bot_name = substr # TODO: Consider making this a function. Or stop using bot_name...
      await self._client.send_msg(msg, "**Username set to:** " + substr)
      return

   @utils.cmd(_cmd, "getemail")
   async def _PLACEHOLDER(self, substr, msg, privilege_level):
      if privilege_level != PrivilegeLevel.BOT_OWNER:
         raise errors.CommandPrivilegeError
      await self._client.send_msg(msg, "My email is: " + email)
      return

   @utils.cmd(_cmd, "joinserver")
   async def _PLACEHOLDER(self, substr, msg, privilege_level):
      if privilege_level != PrivilegeLevel.BOT_OWNER:
         raise errors.CommandPrivilegeError
      try:
         await self._client.accept_invite(substr)
         await self._client.send_msg(msg, "Successfully joined a new server.")
      except discord.InvalidArgument:
         await self._client.send_msg(msg, "Failed to join a new server.")
      return

   @utils.cmd(_cmd, "leaveserver")
   async def _PLACEHOLDER(self, substr, msg, privilege_level):
      if privilege_level != PrivilegeLevel.BOT_OWNER:
         raise errors.CommandPrivilegeError
      await self._client.send_msg(msg, "Bye!")
      await self._client.leave_server(msg.channel.server)
      return

   @utils.cmd(_cmd, "throwexception")
   async def _PLACEHOLDER(self, substr, msg, privilege_level):
      if privilege_level != PrivilegeLevel.BOT_OWNER:
         raise errors.CommandPrivilegeError
      raise Exception

   @utils.cmd(_cmd, "throwexception2")
   async def _PLACEHOLDER(self, substr, msg, privilege_level):
      if privilege_level != PrivilegeLevel.BOT_OWNER:
         raise errors.CommandPrivilegeError
      await self._client.send_message(msg, "A" * 2001)
      await self._client.send_message(msg, "If you're reading this, it failed to throw...")
      return

   def _get_help_content(self, substr, msg, cmd_prefix, privilege_level):
      if substr == "":
         buf = utils.prepare_help_content(self._HELP_SUMMARY_TO_BEGIN, cmd_prefix, privilegelevel=privilege_level)
         buf += "\n"
      else:
         buf = ""
      buf += self._modules.get_help_content(substr, cmd_prefix, privilege_level=privilege_level)
      return buf

   # RETURNS: Bot's current uptime in seconds
   def get_presence_time(self):
      timediff = datetime.datetime.utcnow() - self.initialization_timestamp
      return timediff.seconds


