import asyncio

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered

@registered
class BasicInfo(ServerModule):

   MODULE_NAME = "Basic Information"
   MODULE_SHORT_DESCRIPTION = "Retrieves basic information about the server, users, etc."
   RECOMMENDED_CMD_NAMES = ["basicinfo"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {}

   _HELP_SUMMARY = """
      See `{modhelp}` for basic server/user information commands.
      """

   # TODO: Add this to help detail in the future...
   # *Note: Dates are presented in ISO 8601 format.*

   async def _initialize(self, resources):
      self._res = resources
      self._client = resources.client

      self._res.suppress_autokill(True)
      return

   @cmd.add(_cmdd, "avatar", "dp", "avatarurl")
   @cmd.top_level_alias()
   async def _cmdf_avatar(self, substr, msg, privilege_level):
      """`{p}{c} [user]` - Get a user's avatar."""
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

   @cmd.add(_cmdd, "user", "whois", "who", default=True)
   @cmd.top_level_alias()
   async def _cmdf_user(self, substr, msg, privilege_level):
      """`{p}{c} [user]` - Get user info."""
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

   @cmd.add(_cmdd, "rolestats")
   @cmd.top_level_alias()
   async def _cmdf_rolestats(self, substr, msg, privilege_level):
      """`{p}{c} [rolename]` - Get role stats."""
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
   @cmd.top_level_alias()
   async def _cmdf_server(self, substr, msg, privilege_level):
      """`{p}{c}` - Get some simple server info and statistics."""
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
   @cmd.top_level_alias()
   async def _cmdf_servericon(self, substr, msg, privilege_level):
      """`{p}{c}` - Get server icon."""
      if msg.server.icon_url == "":
         return await self._client.send_msg(msg, "This server has no icon.")
      else:
         return await self._client.send_msg(msg, str(msg.server.icon_url))
