import asyncio

import discord

import utils
import errors
from servermodule import ServerModule

class BasicInfo(ServerModule):

   RECOMMENDED_CMD_NAMES = ["basicinfo"]

   MODULE_NAME = "Basic Information"
   MODULE_SHORT_DESCRIPTION = "Retrieves basic information about the server, users, etc."

   _HELP_SUMMARY_LINES = """
`{pf}whois [user]` - Get user info.
`{pf}avatar [user]` - Get a user's avatar.
`{pf}thisserver` - Get some simple server info and statistics.
`{pf}servericon` - Get server icon.
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
`{pf}whois [user]` - Get user info.
`{pf}avatar [user]` - Get a user's avatar.
`{pf}thisserver` - Get some simple server info and statistics.
`{pf}servericon` - Get server icon.

*Note: Dates are presented in ISO 8601 format.*
   """.strip().splitlines()

   def __init__(self, cmd_names, client):
      self._client = client
      self._cmd_names = cmd_names
      return

   @classmethod
   def get_instance(cls, cmd_names, resources):
      return BasicInfo(cmd_names, resources.client)

   @property
   def cmd_names(self):
      return self._cmd_names

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      str_avatar = default_cmd_prefix + "avatar"
      str_whois = default_cmd_prefix + "whois"
      str_thisserver = default_cmd_prefix + "thisserver"
      str_servericon = default_cmd_prefix + "servericon"
      if content.startswith(str_avatar):
         content = utils.add_base_cmd(content, default_cmd_prefix, self._cmd_names[0])
      elif content.startswith(str_whois):
         content = utils.add_base_cmd(content, default_cmd_prefix, self._cmd_names[0])
      elif content.startswith(str_thisserver):
         content = utils.add_base_cmd(content, default_cmd_prefix, self._cmd_names[0])
      elif content.startswith(str_servericon):
         content = utils.add_base_cmd(content, default_cmd_prefix, self._cmd_names[0])
      return content

   def get_help_summary(self, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_SUMMARY_LINES, cmd_prefix, privilegelevel)

   def get_help_detail(self, substr, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_DETAIL_LINES, cmd_prefix, privilegelevel)

   async def process_cmd(self, substr, msg, privilegelevel=0):
      
      # Process the command itself
      (left, right) = utils.separate_left_word(substr)
      if (left == "avatar") or (left == "dp") or (left == "avatarurl"):
         await self._cmd_avatar(right, msg)

      elif (left == "user") or (left == "whois") or (left == "who"):
         await self._cmd_user(right, msg)

      elif (left == "server") or (left == "thisserver"):
         await self._cmd_server(right, msg)

      elif (left == "servericon"):
         await self._cmd_servericon(right, msg)

      else:
         raise errors.InvalidCommandArgumentsError

      return

   async def _cmd_avatar(self, substr, msg):
      substr = substr.split()
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
         return await self._client.send_msg(msg, left + " m8 get an avatar")
      else:
         return await self._client.send_msg(msg, avatar)

   async def _cmd_user(self, substr, msg):
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

   async def _cmd_server(self, substr, msg):
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

   async def _cmd_servericon(self, substr, msg):
      if msg.server.icon_url == "":
         return await self._client.send_msg(msg, "This server has no icon.")
      else:
         return await self._client.send_msg(msg, str(msg.server.icon_url))
