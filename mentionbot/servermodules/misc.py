import asyncio
import os
import copy
import datetime
import urllib.parse as urllibparse

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered
from ..enums import PrivilegeLevel

@registered
class Misc(ServerModule):
   """
   This module basically exists to reduce the clutter in serverbotinstance.py and the base help message.
   """

   MODULE_NAME = "Misc"
   MODULE_SHORT_DESCRIPTION = "Additional misc. commands not available by default."
   RECOMMENDED_CMD_NAMES = ["misc"]

   _SECRET_TOKEN = utils.SecretToken()
   _cmd_dict = {} # Empty dict should work...

   _HELP_SUMMARY = """
See `{modhelp}` for misc. commands.
   """.strip()

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client

      self._res.suppress_autokill(True)
      return

   @cmd.add(_cmd_dict, "time", "gettime", "utc")
   @cmd.top_level_alias()
   async def _cmdf_time(self, substr, msg, privilege_level):
      """`{p}{c}` - Get bot's system time in UTC."""
      await self._client.send_msg(msg, datetime.datetime.utcnow().strftime("My current system time: %c UTC"))
      return

   ##########################
   ### TEMPORARY COMMANDS ###
   ##########################

   # Random commands go here until they find a home in a proper module.

   @cmd.add(_cmd_dict, "lmgtfy", "google", "goog", "yahoo")
   @cmd.top_level_alias()
   async def _cmdf_say(self, substr, msg, privilege_level):
      """`{p}{c} [text]` - Let me google that for you..."""
      if len(substr) == 0:
         raise errors.InvalidCommandArgumentsError
      await self._client.send_msg(msg, "http://lmgtfy.com/?q=" + urllibparse.quote(substr))
      return

   ######################
   ### ADMIN COMMANDS ###
   ######################

   @cmd.add(_cmd_dict, "say")
   @cmd.top_level_alias()
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_say(self, substr, msg, privilege_level):
      """`{p}{c} [text]` - Echo's the following text."""
      await self._client.send_msg(msg, substr)
      return

   @cmd.add(_cmd_dict, "iam")
   @cmd.top_level_alias()
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_iam(self, substr, msg, privilege_level):
      """
      `{p}{c} [user] [text]` - Reprocesses text as a different author.

      This command is useful for executing commands for another user.
      Otherwise, it does nothing if the string isn't a valid command.

      Note that this command is a bit of a hacky solution. It is possible \
      that some commands will utterly misbehave when this command is used.
      """
      (left, right) = utils.separate_left_word(substr)
      if utils.re_user_mention.fullmatch(left):
         user_to_pose_as = left[2:-1]
         replacement_msg = copy.deepcopy(msg)
         replacement_msg.author = self._client.search_for_user(user_to_pose_as)
         if replacement_msg.author == None:
            return await self._client.send_msg(msg, "Unknown user.")
         replacement_msg.content = right
         await self._client.send_msg(msg, "Executing command as {}: {}".format(replacement_msg.author, replacement_msg.content))
         await self._client.send_msg(msg, "**WARNING: There are no guarantees of the safety of this operation.**")
         await self._res.server_process_text(right, replacement_msg)
      return

   @cmd.add(_cmd_dict, "setgame", "setgamestatus")
   @cmd.top_level_alias()
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setgame(self, substr, msg, privilege_level):
      """`{p}{c} [text]` - Sets the bot's game status."""
      await self._client.set_game_status(substr)
      await self._client.send_msg(msg, "**Game set to:** " + substr)
      return

   @cmd.add(_cmd_dict, "tempgame")
   @cmd.top_level_alias()
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setgame(self, substr, msg, privilege_level):
      """`{p}{c} [text]` - Sets a temporary game status on the bot."""
      await self._client.set_temp_game_status(substr)
      await self._client.send_msg(msg, "**Game temporarily set to:** " + substr)
      return

   @cmd.add(_cmd_dict, "revertgame")
   @cmd.top_level_alias()
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setgame(self, substr, msg, privilege_level):
      """`{p}{c}` - Reverts a temporary game status."""
      await self._client.remove_temp_game_status()
      await self._client.send_msg(msg, "**Reverted game.**")
      return

   @cmd.add(_cmd_dict, "setusername", "updateusername", "newusername", "setname", "newname")
   @cmd.top_level_alias()
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setusername(self, substr, msg, privilege_level):
      """`{p}{c} [text]` - Set the bot's username."""
      await self._client.edit_profile(None, username=substr)
      await self._client.send_msg(msg, "**Username set to:** " + substr)
      return

   @cmd.add(_cmd_dict, "setavatar", "updateavatar", "setdp", "newdp")
   @cmd.top_level_alias()
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_setusername(self, substr, msg, privilege_level):
      """
      `{p}{c} [url]` - Updates avatar to the URL. (Other options are available.)

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
   @cmd.top_level_alias()
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_joinserver(self, substr, msg, privilege_level):
      """`{p}{c} [invite link]` - Attempt to join a server via invite link."""
      try:
         await self._client.accept_invite(substr)
         await self._client.send_msg(msg, "Successfully joined a new server.")
      except:
         await self._client.send_msg(msg, "Failed to join a new server.")
      return

   @cmd.add(_cmd_dict, "leaveserver")
   @cmd.top_level_alias()
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_leaveserver(self, substr, msg, privilege_level):
      """`{p}{c}` - Make the bot leave the server."""
      await self._client.send_msg(msg, "Bye!")
      await self._client.leave_server(msg.channel.server)
      return

   @cmd.add(_cmd_dict, "msgcachedebug")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_msgcachedebug(self, substr, msg, privilege_level):
      """`{cmd}` - Debugging function for the message cache."""
      buf = self._client.message_cache_debug_str()
      await self._client.send_msg(msg, buf)
      return

   ################################
   ### TEMPORARY ADMIN COMMANDS ###
   ################################

   @cmd.add(_cmd_dict, "testbell")
   @cmd.category("Admin Commands")
   @cmd.minimum_privilege(PrivilegeLevel.BOT_OWNER)
   async def _cmdf_msgcachedebug(self, substr, msg, privilege_level):
      """`{cmd}` - Test the effectiveness of the bell character."""
      buf = "<@\a119384097473822727>"
      await self._client.send_msg(msg, buf)
      return
