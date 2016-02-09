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

import servermodulegroup
from serverpersistentstorage import ServerPersistentStorage
from privilegemanager import PrivilegeManager

# Modules
from servermodules.mentions.mentions import Mentions

# ServerBotInstance manages everything to do with a particular server.
# IMPORTANT: client is a MentionBot instance!!!
class ServerBotInstance:
   _RE_MENTIONSTR = re.compile("<@\d+>")

   INIT_MENTIONS_NOTIFY_ENABLED = False
   DEFAULT_COMMAND_PREFIX = "/"

   # IMPORTANT: This needs to be parsed with ServerModule._prepare_help_content()
   # TODO: Figure out a neater way of doing this.
   _HELP_SUMMARY_TO_BEGIN = """
**The following commands are available:**
`{pf}avatar [usermention]` - Get the avatar URL of the user.
`{pf}randomcolour`
`{pf}source` - Where to get source code.
`{pf}rip` - Rest in pieces.
`{pf}status` - Get bot's current status.
>>> PRIVILEGE LEVEL 1 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
`{pf}admin [cmd]` or `{pf}a [cmd]` - Bot admin commands. Must have permission to use.
   """.strip().splitlines()

   def __init__(self, client, server):
      self._client = client
      self._server = server

      self._data_directory = self._client.CACHE_DIRECTORY + "serverdata/" + self._server.id + "/"

      self._cmd_prefix = self.DEFAULT_COMMAND_PREFIX
      self._bot_name = self._client.user.name # TODO: Move this somewhere else.
      self._initialization_timestamp = datetime.datetime.utcnow()

      botowner_ID = self._client.BOTOWNER_ID
      serverowner_ID = self._server.owner.id

      self._storage = ServerPersistentStorage(self._data_directory + "settings.json", self._server)
      self._privileges = PrivilegeManager(botowner_ID, serverowner_ID)

      print(str(self._storage.get_server_settings()))

      modules = [
         Mentions(Mentions.RECOMMENDED_CMD_NAMES, client)
      ]
      self._modules = servermodulegroup.ServerModuleGroup(initial_modules=modules)
      return


   # Call this to process text (to parse for commands).
   async def process_text(self, substr, msg):
      
      await self._modules.on_message(msg)

      (left, right) = utils.separate_left_word(substr)

      if substr.startswith(self._cmd_prefix):
         await self._cmd1(substr[1:].strip(), msg, self._cmd_prefix, no_default=True)

      # EASTER EGG REPLY.
      elif (left == "$blame") and (self._client.bot_mention in substr):
         await self._client.send_msg(msg, "no fk u")

      # TODO: Fix this later.
      # elif (self._client.bot_mention in substr or substr == self._client.user.name + " pls"):
      #    await self._mbSummaryModule.process_cmd("", msg, add_extra_help=True)
      
      # EASTER EGG REPLY
      elif msg.content.startswith("$blame " + self._client.botowner_mention) or msg.content.startswith("$blame " + self._client.botowner.name):
         await self._client.send_msg(msg, "he didnt do shit m8")
      
      return


   async def _cmd1(self, substr, msg, cmd_prefix, no_default=False):
      substr = substr.strip()
      if substr == "" and not no_default:
         raise NotImplementedError # TODO !!!
         # await self._mbSummaryModule.process_cmd("", msg, add_extra_help=False)
      else:
         (left, right) = utils.separate_left_word(substr)
         print(left)
         if left == "help":
            help_content = self._get_help_content(right, msg, cmd_prefix)
            await self._client.send_msg(msg, help_content)

         # TODO: Make mentions a module, and notify/search/summary submodules.
         # elif (left == "mentions") or (left == "mb") or (left == "mentionbot"):
         #    await self._cmd1_mentions(right, msg)

         elif left == "avatar":
            await self._cmd1_avatar(right, msg)

         elif (left == "randomcolour") or (left == "randomcolor"):
            rand_int = random.randint(0,(16**6)-1)
            rand = hex(rand_int)[2:] # Convert to hex
            rand = rand.zfill(6)
            buf = "{}, your random colour is {} (decimal: {})".format(msg.author.name, rand, rand_int)
            buf += "\nhttp://www.colorhexa.com/{}.png".format(rand)
            await self._client.send_msg(msg, buf)

         elif left == "source":
            await self._client.send_msg(msg, "idk, ask sim.")

         elif left == "rip":
            await self._client.send_msg(msg, "doesnt even deserve a funeral")

         # TODO: Make this useable.
         # elif left == "status":
         #    buf = "**Status:**"
         #    buf += "\nBot current uptime: {}. ".format(utils.seconds_to_string(self.get_presence_time()))
         #    buf += "\nNotification system enabled = " + str(self._mbNotifyModule.is_enabled())
         #    await self._client.send_msg(msg, buf)

         # TODO: rework admin command help.
         elif (left == "admin") or (left == "a"):
            await self._cmd_admin(right, msg)

         # USED FOR DEBUGGING
         elif left == "test":
            buf = "I hear ya " + msg.author.name + "!"
            await self._client.send_msg(msg, buf)

         else:
            privilege_level = self._privileges.get_privilege_level(msg.author)
            await self._modules.process_cmd(substr, msg, privilegelevel=privilege_level)
         
         # else:
         #    raise CommandArgumentsError
      
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


   async def _cmd1_avatar(self, substr, msg):
      (left, right) = utils.separate_left_word(substr)
      user = None
      if len(left) > 0:
         user = self._client.search_for_user(left, enablenamesearch=True, serverrestriction=msg.server)
         if user is None:
            return await self._client.send_msg(msg, left + " doesn't even exist m8")
      else:
         user = msg.author

      # Guaranteed to have a user.
      avatar = user.avatar_url
      if avatar == "":
         return await self._client.send_msg(msg, left + " m8 get an avatar")
      else:
         return await self._client.send_msg(msg, avatar)


   async def _cmd_admin(self, substr, msg):
      privilege_level = self._privileges.get_privilege_level(msg.author)
      if privilege_level != PrivilegeLevel.BOT_OWNER:
         raise errors.CommandPrivilegeError

      substr = substr.strip()
      if substr == "" and not no_default:
         raise errors.UnknownCommandError
      else:
         (left1, right1) = utils.separate_left_word(substr)

         if left1 == "say":
            await self._client.send_msg(msg, right1)

         elif left1 == "iam":
            await self._cmd_admin_iam(right1, msg)

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


   async def _cmd_admin_iam(self, substr, msg):
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


