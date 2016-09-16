import asyncio
import re

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered
from ..enums import PrivilegeLevel

from ..attributedictwrapper import AttributeDictWrapper

@registered
class UserBios(ServerModule):

   MODULE_NAME = "User Bios"
   MODULE_SHORT_DESCRIPTION = "User biographies."
   RECOMMENDED_CMD_NAMES = ["userbios", "userbio"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {}

   _HELP_SUMMARY = """
      `{modhelp}` - User biographies.
      """

   _default_settings = {
      "bios": {}
   }

   async def _initialize(self, resources):
      self._res = resources
      self._client = resources.client
      self._server = resources.server

      self._user_bios = None # Initialize later
      # _user_bios[user_id] = bio_string

      await self._load_settings()

      self._res.suppress_autokill(True)
      return

   async def _load_settings(self):
      settings_dict = self._res.get_settings(default=self._default_settings)
      settings = AttributeDictWrapper(settings_dict, self._default_settings)

      self._user_bios = settings.get("bios")
      # Verify each individual user bio.
      for (k, v) in self._user_bios.items():
         if not (isinstance(k, str) and (len(k) > 0)
               and utils.re_digits.fullmatch(k) and isinstance(v, str)
               and (len(v) > 0)):
            buf = "Invalid key or value found. Server ID: " + self._server.id
            buf += ", Key: '" + k + "'."
            raise ValueError(buf)
      return

   async def _save_settings(self):
      settings = {
         "bios": self._user_bios
      }
      self._res.save_settings(settings)
      return

   @cmd.add(_cmdd, "get", default=True)
   async def _cmdf_get(self, substr, msg, privilege_level):
      """
      `{cmd} [user]` - Get the user's bio.
      """
      user = None
      if len(substr) == 0:
         user = msg.author
      else:
         user = self._client.search_for_user(substr, enablenamesearch=True, serverrestriction=msg.server)
         if user is None:
            await self._client.send_msg(msg, "**Error:** Failed to find user `" + substr + "`.")
            return
      # Guaranteed to have a valid user.
      if not user.id in self._user_bios:
         await self._client.send_msg(msg, "User " + utils.user_nick(user) + " does not have a bio.")
         return
      # Guaranteed to have a user with a bio.
      buf = "**User bio for " + utils.user_nick(user) + ":**\n"
      buf += self._user_bios[user.id]
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "set")
   async def _cmdf_set(self, substr, msg, privilege_level):
      """
      `{cmd} [content]` - Set your user bio.
      `{cmd}` - Clear your user bio.

      Note that formatting is restricted. Monospace blocks and bold text will be replaced. This is done to keep formatting clear.
      """
      user = msg.author
      # Possibly clear the user bio and return.
      if len(substr) == 0:
         if user.id in self._user_bios:
            del self._user_bios[user.id]
            buf = "Successfully cleared user bio for " + utils.user_nick(user) + "."
         else:
            buf = "User " + utils.user_nick(user) + " does not have a bio."
         await self._client.send_msg(msg, buf)
         return
      # Now set the user bio.
      original_substr = substr
      substr = substr.replace("```", "'''").replace("**", "\*\*")
      if len(substr) > 500:
         await self._client.send_msg(msg, "**Error:** Bio must be between 1 and 500 characters.")
         return
      if substr.count("\n") > 4:
         await self._client.send_msg(msg, "**Error:** Bio cannot have more than 4 line breaks.")
         return
      self._user_bios[user.id] = substr
      await self._save_settings()
      buf = "Successfully set user bio for " + utils.user_nick(user) + "."
      if original_substr != substr:
         buf += " However, I have replaced instances of triple-grave and"
         buf += " double-asterisk in your bio. This is done to keep formatting"
         buf += " clear."
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "forceremove")
   @cmd.minimum_privilege(PrivilegeLevel.MODERATOR)
   async def _cmdf_forceremove(self, substr, msg, privilege_level):
      """
      `{cmd} [user]` - Remove the user's bio.
      """
      user = None
      if len(substr) == 0:
         await self._client.send_msg(msg, "**Error:** Must specify a user.")
         return
      else:
         user = self._client.search_for_user(substr, enablenamesearch=True, serverrestriction=msg.server)
         if user is None:
            await self._client.send_msg(msg, "**Error:** Failed to find user `" + substr + "`.")
            return
      # Guaranteed to have a user to try to clear a bio from.
      if not user.id in self._user_bios:
         await self._client.send_msg(msg, "User " + utils.user_nick(user) + " does not have a bio.")
         return
      # Guaranteed to have a bio to clear.
      old_bio = self._user_bios[user.id]
      del self._user_bios[user.id]
      await self._save_settings()
      buf = "Successfully cleared user bio for " + utils.user_nick(user) + "."
      await self._client.send_msg(msg, buf)
      # Now we shall attempt to notify that user of the removal.
      buf = "Hello! Your user bio in server " + self._server.name
      buf += " was removed by " + utils.user_nick(msg.author)
      buf += ".\n**Original content:**\n" + old_bio
      await self._client.send_msg(user, buf)
      return

   async def get_extra_user_info(self, member):
      user_bio = None
      if member.id in self._user_bios:
         user_bio = "**User bio:**\n" + self._user_bios[member.id]
      return (None, user_bio)
   