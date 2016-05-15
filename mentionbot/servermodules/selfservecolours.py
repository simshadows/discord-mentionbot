import asyncio
import random
import re

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered

@registered
class SelfServeColours(ServerModule):

   MODULE_NAME = "Self-Serve Colours"
   MODULE_SHORT_DESCRIPTION = "Allows users to pick their own personal colour flair."
   RECOMMENDED_CMD_NAMES = ["colour", "color", "rgb"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmd_dict = {}

   _HELP_SUMMARY = """
      `{p}colour [rgb code]` - Assign yourself a colour. `{p}colour` clears.
      """

   _re_rgb_code = re.compile("[0-9a-fA-F]{6}")

   async def _initialize(self, resources):
      self._res = resources
      self._client = resources.client

      self._res.suppress_autokill(True)
      return

   async def process_cmd(self, substr, msg, privilege_level):
      # First process the input.
      if (len(substr) == 0) or (substr == "clear"):
         # Just remove the colour flair.
         await self._remove_colour_roles(msg.author)
         await self._client.send_msg(msg, "Removed <@{}>'s colour role.".format(msg.author.id))
         return
      elif substr.startswith("#"):
         substr = substr[1:]
      rgb_code_str = r = g = b = None
      if self._re_rgb_code.fullmatch(substr):
         rgb_code_str = substr.lower()
         rgb_code_int = int(rgb_code_str, base=16)
         # r = int(rgb_code_str[:2], base=16)
         # g = int(rgb_code_str[2:4], base=16)
         # b = int(rgb_code_str[-2:], base=16)
      else:
         await self._client.send_msg(msg, substr + " is not a valid colour code.")
         raise errors.OperationAborted

      member = msg.author
      await self._remove_colour_roles(member)

      # Prepare new role object
      colour_obj = discord.Colour(rgb_code_int)
      role_obj = utils.flair_name_to_object(self._res.server, rgb_code_str, case_sensitive=False)
      perm_obj = discord.Permissions.none()
      if role_obj is None:
         role_obj = await self._client.create_role(self._res.server, name=rgb_code_str, colour=colour_obj, permissions=perm_obj)
      else:
         # Ensure role object has the correct colour and permissions.
         await self._client.edit_role(self._res.server, role_obj, colour=colour_obj, permissions=perm_obj)

      # Assign the role
      await self._client.add_roles(member, role_obj)
      await self._client.send_msg(msg, "Assigned <@{0}> the colour #{1}.".format(member.id, rgb_code_str))
      return

   async def _remove_colour_roles(self, member):
      # Remove any role that is an rgb code.
      to_remove = []
      for role_obj in member.roles:
         if self._re_rgb_code.fullmatch(role_obj.name):
            to_remove.append(role_obj)
      await self._client.remove_roles(member, *to_remove)

      # For each removed role, if no one is assigned it, delete it.
      for role_obj in to_remove:
         if utils.role_is_unused(self._res.server, role_obj):
            await self._client.delete_role(self._res.server, role_obj)
      return
   