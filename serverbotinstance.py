import asyncio
import random
import re
import datetime
import copy

import discord

import utils
import errors
import clientextended

import mentions.notify
import mentions.search
import mentions.summary
import helpmessages.helpmessages

# THE FOLLOWING CONSTANTS ARE COPIED FROM mentionbot.py. TODO: FIX THIS.
BOTOWNER_ID = str(119384097473822727) # User ID of the owner of this bot
INITIAL_GLOBALENABLED_MENTIONS_NOTIFY = False

# ServerBotInstance manages everything to do with a particular server.
# For example, a ser
class ServerBotInstance:
   def __init__(self, client, server):
      self._re_mentionstr = re.compile("<@\d+>")

      self._client = client
      self._server = server

      self._bot_name = self._client.user.name # TODO: Move this somewhere else.
      self._initialization_timestamp = datetime.datetime.utcnow()

      self._help_messages = helpmessages.helpmessages.HelpMessages()

      self._mbNotifyModule = mentions.notify.MentionNotifyModule(client, enabled=INITIAL_GLOBALENABLED_MENTIONS_NOTIFY)
      self._mbSearchModule = mentions.search.MentionSearchModule(client)
      self._mbSummaryModule = mentions.summary.MentionSummaryModule(client)
      return


   # Call this every time a message from the server self._server is received.
   async def on_message(self, msg):
      await self._mbNotifyModule.on_message(msg)
      await self._mbSummaryModule.on_message(msg)
      return


   # Call this to process a command.
   # FORMERLY: cmd1()
   async def process_cmd(self, substr, msg, no_default=False):
      substr = substr.strip()
      if substr == "" and not no_default:
         await self._mbSummaryModule.process_cmd("", msg, add_extra_help=False)
      else:
         (left, right) = utils.separate_left_word(substr)

         if left == "help":
            if self._is_privileged_user(msg.author.id):
               privilege_level = 1
            else:
               privilege_level = 0
            buf = self._help_messages.get_message(right, privilegelevel=privilege_level)
            if buf == None:
               raise errors.UnknownCommandError
            else:
               await self._client.send_msg(msg, buf)

         elif (left == "mentions") or (left == "mb") or (left == "mentionbot"):
            await self._cmd1_mentions(right, msg)

         elif left == "avatar":
            await self._cmd1_avatar(right, msg)

         elif (left == "randomcolour") or (left == "randomcolor"):
            # TODO: THIS IS TEMPORARY!!!
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

         elif left == "status":
            buf = "**Status:**"
            buf += "\nBot current uptime: {}. ".format(utils.seconds_to_string(self.get_presence_time()))
            buf += "\nNotification system enabled = " + str(self._mbNotifyModule.is_enabled())
            await self._client.send_msg(msg, buf)

         elif (left == "admin") or (left == "a"):
            await self._cmd_admin(right, msg)

         # USED FOR DEBUGGING
         elif left == "test":
            buf = "I hear ya " + msg.author.name + "!"
            await self._client.send_msg(msg, buf)
         
         # else:
         #    raise CommandArgumentsError
      
      return


   async def _cmd1_mentions(self, substr, msg, no_default=False):
      substr = substr.strip()
      if substr == "" and not no_default:
         await self._mbSummaryModule.process_cmd("", msg, add_extra_help=False)
      else:
         (left, right) = utils.separate_left_word(substr)

         if left == "summary":
            await self._mbSummaryModule.process_cmd(right, msg)

         elif (left == "search") or (left == "s"):
            await self._mbSearchModule.process_cmd(right, msg)

         elif (left == "notify") or (left == "n"):
            await self._mbNotifyModule.process_cmd(right, msg)
         
         else:
            raise errors.UnknownCommandError
      return


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
      if not self._is_privileged_user(msg.author.id):
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

         elif left1 == "toggle":
            (left2, right2) = utils.separate_left_word(right1)
            if (left2 == "mentions") or (left2 == "mb") or (left2 == "mentionbot"):
               (left3, right3) = utils.separate_left_word(right2)
               if (left3 == "notify") or (left3 == "n"):
                  if mentionNotifyModule.is_enabled():
                     self._mbNotifyModule.disable()
                  else:
                     self._mbNotifyModule.enable()
                  await self._client.send_msg(msg, "Notification system enabled = " + str(self._mbNotifyModule.is_enabled()))
               else:
                  raise errors.UnknownCommandError
            else:
               raise errors.UnknownCommandError

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
         
         else:
            raise errors.UnknownCommandError
      return


   async def _cmd_admin_iam(self, substr, msg):
      substr = substr.strip()
      (left, right) = utils.separate_left_word(substr)
      
      if self._re_mentionstr.fullmatch(left):
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


   # TODO: This method will need to be changed in the future.
   def _is_privileged_user(self, user_ID):
      return user_ID == BOTOWNER_ID


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


