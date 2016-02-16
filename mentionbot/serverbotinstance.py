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

# Modules
from servermodules.mentions.mentions import Mentions

# ServerBotInstance manages everything to do with a particular server.
# IMPORTANT: client is a MentionBot instance!!!
class ServerBotInstance:
   
   _SECRET_TOKEN = utils.SecretToken()

   _RE_MENTIONSTR = re.compile("<@\d+>")

   INIT_MENTIONS_NOTIFY_ENABLED = False
   DEFAULT_COMMAND_PREFIX = "/"

   # IMPORTANT: This needs to be parsed with ServerModule._prepare_help_content()
   # TODO: Figure out a neater way of doing this.
   _HELP_SUMMARY_TO_BEGIN = """
**The following commands are available:**
`{pf}source` - Where to get source code.
`{pf}allmods` - Get all modules available for installation.
`{pf}mods` - Get all installed modules.
`{pf}status` - Get bot's current status.
>>> PRIVILEGE LEVEL 8000 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
`{pf}say [text]`
`{pf}add [module name]`
`{pf}remove [module name]`
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

      inst._cmd_prefix = inst.DEFAULT_COMMAND_PREFIX
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
         modules.append(inst._module_factory.new_module_instance(module_name, inst))
      inst._modules = ServerModuleGroup(initial_modules=modules)
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
   


   # Call this to process text (to parse for commands).
   async def process_text(self, substr, msg):
      
      await self._modules.on_message(msg)

      privilege_level = self._privileges.get_privilege_level(msg.author)
      if privilege_level == PrivilegeLevel.NO_PRIVILEGE:
         return

      substr = await self._modules.msg_preprocessor(substr, msg, self._cmd_prefix)

      (left, right) = utils.separate_left_word(substr)

      if substr.startswith(self._cmd_prefix):
         await self._cmd1(substr[1:].strip(), msg, self._cmd_prefix, no_default=True)

      # # EASTER EGG REPLY.
      # elif (left == "$blame") and (self._client.bot_mention in substr):
      #    await self._client.send_msg(msg, "no fk u")

      # TODO: Fix this later.
      # elif (self._client.bot_mention in substr or substr == self._client.user.name + " pls"):
      #    await self._mbSummaryModule.process_cmd("", msg, add_extra_help=True)
      
      # # EASTER EGG REPLY
      # elif msg.content.startswith("$blame " + self._client.botowner_mention) or msg.content.startswith("$blame " + self._client.botowner.name):
      #    await self._client.send_msg(msg, "he didnt do shit m8")
      
      return


   async def _cmd1(self, substr, msg, cmd_prefix, no_default=False):
      substr = substr.strip()
      privilege_level = self._privileges.get_privilege_level(msg.author)
      if substr == "" and not no_default:
         raise NotImplementedError # TODO !!!
         # await self._mbSummaryModule.process_cmd("", msg, add_extra_help=False)
      else:
         (left, right) = utils.separate_left_word(substr)
         if left == "help":
            help_content = self._get_help_content(right, msg, cmd_prefix)
            await self._client.send_msg(msg, help_content)

         elif (left == "allmods") or (left == "allmodules"):
            buf = "**The following modules are available for installation:**"
            for val in self._module_factory.module_list_gen():
               buf += "\n`{0}`: {1}".format(val[0], val[1])
            await self._client.send_msg(msg, buf)

         elif (left == "mods") or (left == "modules"):
            info = self._modules.get_module_info()
            if len(info) == 0:
               buf = "No modules are installed."
            else:
               buf = "**The following modules are installed:**"
               for val in info:
                  buf += "\n`{0}`: {1}".format(val[0], val[1])
            await self._client.send_msg(msg, buf)

         elif left == "source":
            await self._client.send_msg(msg, "https://github.com/simshadows/discord-mentionbot")

         elif left == "status":
            buf = "**Status:**"
            buf += "\nBot current uptime: {}. ".format(utils.seconds_to_string(self.get_presence_time()))
            await self._client.send_msg(msg, buf)

         elif (left == "botowner") or (left == "bo"):
            await self._cmd_botowner(right, msg)

         elif left == "say":
            if privilege_level < PrivilegeLevel.ADMIN:
               raise errors.CommandPrivilegeError
            await self._client.send_msg(msg, right)

         elif (left == "add") or (left == "install") or (left == "addmodule"):
            if privilege_level < PrivilegeLevel.ADMIN:
               raise errors.CommandPrivilegeError
            if self._module_factory.module_exists(right):
               if self._modules.module_is_installed(right):
                  await self._client.send_msg(msg, "`{}` is already installed.".format(right))
               else:
                  new_module = self._module_factory.new_module_instance(right, self)
                  await self._modules.add_server_module(new_module)
                  self._storage.add_module(right)
                  await self._client.send_msg(msg, "`{}` successfully installed.".format(right))
            else:
               await self._client.send_msg(msg, "`{}` does not exist.".format(right))

         elif (left == "remove") or (left == "uninstall") or (left == "removemodule"):
            if privilege_level < PrivilegeLevel.ADMIN:
               raise errors.CommandPrivilegeError
            if self._modules.module_is_installed(right):
               await self._modules.remove_server_module(right)
               self._storage.remove_module(right)
               await self._client.send_msg(msg, "`{}` successfully uninstalled.".format(right))
            else:
               await self._client.send_msg(msg, "`{}` is not installed.".format(right))

         else:
            print("processing command: " + substr)
            privilege_level = self._privileges.get_privilege_level(msg.author)
            await self._modules.process_cmd(substr, msg, privilegelevel=privilege_level, silentfail=True)
      
      return


   def _get_help_content(self, substr, msg, cmd_prefix):
      privilege_level = self._privileges.get_privilege_level(msg.author)
      if substr == "":
         buf = utils.prepare_help_content(self._HELP_SUMMARY_TO_BEGIN, cmd_prefix, privilegelevel=privilege_level)
         buf += "\n"
      else:
         buf = ""
      buf += self._modules.get_help_content(substr, cmd_prefix, privilege_level=privilege_level)
      return buf

   async def _cmd_botowner(self, substr, msg):
      privilege_level = self._privileges.get_privilege_level(msg.author)
      if privilege_level != PrivilegeLevel.BOT_OWNER:
         raise errors.CommandPrivilegeError

      substr = substr.strip()
      if substr == "":
         raise errors.UnknownCommandError
      
      (left1, right1) = utils.separate_left_word(substr)

      if left1 == "iam":
         await self._cmd_botowner_iam(right1, msg)

      # TODO: Reimplement this pls.
      # elif left1 == "toggle":
      #    (left2, right2) = utils.separate_left_word(right1)
      #    if (left2 == "mentions") or (left2 == "mb") or (left2 == "mentionbot"):
      #       (left3, right3) = utils.separate_left_word(right2)
      #       if (left3 == "notify") or (left3 == "n"):
      #          if mentionNotifyModule.is_enabled():
      #             self._mbNotifyModule.disable()
      #          else:
      #             self._mbNotifyModule.enable()
      #          await self._client.send_msg(msg, "Notification system enabled = " + str(self._mbNotifyModule.is_enabled()))
      #       else:
      #          raise errors.UnknownCommandError
      #    else:
      #       raise errors.UnknownCommandError

      elif left1 == "gettime":
         await self._client.send_msg(msg, datetime.datetime.utcnow().strftime("My current system time: %c UTC"))

      elif left1 == "setgame":
         await self._client.set_game_status(right1)
         await self._client.send_msg(msg, "Game set to: " + right1)

      elif left1 == "setusername":
         await self._client.edit_profile(password, username=right1)
         self._bot_name = right1 # TODO: Consider making this a function. Or stop using bot_name...
         await self._client.send_msg(msg, "Username set to: " + right1)

      elif left1 == "getemail":
         await self._client.send_msg(msg, "My email is: " + email)

      elif left1 == "joinserver":
         try:
            await self._client.accept_invite(right1)
            await self._client.send_msg(msg, "Successfully joined a new server.")
         except discord.InvalidArgument:
            await self._client.send_msg(msg, "Failed to join a new server.")

      elif left1 == "leaveserver":
         await self._client.send_msg(msg, "Bye!")
         await self._client.leave_server(msg.channel.server)

      elif left1 == "throwexception":
         raise Exception

      elif left1 == "throwexception2":
         await self._client.send_message(msg, "A" * 2001)
      
      else:
         raise errors.UnknownCommandError
      return


   async def _cmd_botowner_iam(self, substr, msg):
      substr = substr.strip()
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
         await self.process_cmd(right, replacement_msg) # TODO: Make this call on_message()
      return


   # RETURNS: Bot's current uptime in seconds
   def get_presence_time(self):
      timediff = datetime.datetime.utcnow() - initialization_timestamp
      return timediff.seconds


# def msg_list_to_string(mentions, verbose=False): # TYPE: String
#    now = datetime.datetime.utcnow()
#    buf = "" # FORMAT: String
#    for i in mentions:
#       timediff = now - i.timestamp
#       if verbose:
#          buf += "Message ID: " + i.id + "\n"
#          # buf += "Timestamp: " + i.timestamp.strftime("%c UTC") + "\n" # Unnecessary
#       buf += "By " + i.author.name + " in " + "<#{}>".format(i.channel.id) + ", " + utils.seconds_to_string(timediff.seconds) + " ago\n"
#       buf += i.content + "\n\n"
#    if buf != "":
#       buf = buf[:-2]
#    return buf


