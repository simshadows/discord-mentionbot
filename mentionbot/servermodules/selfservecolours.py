import asyncio
import random
import re
import textwrap

import discord

from .. import utils, errors, cmd
from ..enums import PrivilegeLevel
from ..servermodule import ServerModule, registered

@registered
class SelfServeColours(ServerModule):

   MODULE_NAME = "Self-Serve Colours"
   MODULE_SHORT_DESCRIPTION = "Allows users to pick their own personal colour flair."
   RECOMMENDED_CMD_NAMES = ["colourmod", "colormod"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {}

   _HELP_SUMMARY = """
      `{modhelp}` - Personal colour roles.
      """
   # `{p}{grp}[rgb code]` - Assign yourself a colour.
   # `{p}{grp}colour` - Removes your current colour flair.

   _re_rgb_code = re.compile("[0-9a-fA-F]{6}")

   async def _initialize(self, resources):
      self._res = resources
      self._client = resources.client

      self._res.suppress_autokill(True)
      return

   @cmd.add(_cmdd, "colour", "color", "rgb", top=True, default=True)
   async def _cmdf_ud(self, substr, msg, privilege_level):
      """
      `{cmd} [rgb colour code]` - Assign yourself a colour role.
      `{cmd} random` - Assign yourself a random colour role.
      `{cmd}` - Removes your current colour role.
      """
      # First process the input.
      substr = substr.lower()
      if (len(substr) == 0) or (substr == "clear"):
         # Just remove the colour flair.
         await self._remove_colour_roles(msg.author)
         await self._client.send_msg(msg, "Removed <@{}>'s colour role.".format(msg.author.id))
         return
      elif substr == "random":
         rand_int = random.randint(0,(16**6)-1)
         rand = hex(rand_int)[2:] # Convert to hex
         rand = rand.zfill(6)
         substr = rand
      elif substr.startswith("#"):
         substr = substr[1:]

      rgb_code_str = substr
      if self._re_rgb_code.fullmatch(rgb_code_str):
         rgb_code_int = int(rgb_code_str, base=16)
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

   @cmd.add(_cmdd, "clean")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_clean(self, substr, msg, privilege_level):
      """
      Cleans out all unused colour roles.

      This carries out a dry run by default, meaning that it doesn't actually delete any roles. To carry out the role deletion, use the command `{cmd} finalrun`.
      """
      # First process the input.
      finalrun = False
      if substr == "finalrun":
         finalrun = True
      elif substr != "":
         raise errors.InvalidCommandArgumentsError
      
      # Get all colour roles
      all_colours = {
         x for x in self._res.server.roles if self._re_rgb_code.fullmatch(x.name)
      }
      # Get what's unused
      roles_used = set()
      for member in self._res.server.members:
         roles_used.update(x for x in member.roles)
      colours_unused = all_colours - roles_used

      if len(colours_unused) == 0:
         await self._client.send_msg(msg, "No unused colour roles.")
         return

      if finalrun:
         # WE DELETE ROLES HERE.
         await self._client.send_msg(msg, "Please wait while roles are deleted...")
         server = self._res.server
         client = self._client
         for colour_role in colours_unused:
            await client.delete_role(server, colour_role)

      buf = []
      if finalrun:
         buf.append(str(len(colours_unused)) + " deleted:\n```")
      else:
         buf.append(str(len(colours_unused)) + " to be deleted:\n```")
      #buf += ["ID: " + str(x.id) + ", Name: " + str(x.name) for x in colours_unused]
      buf += [str(x.name) for x in colours_unused]
      buf.append("```")
      await self._client.send_msg(msg, "\n".join(buf))

      if not finalrun:
         buf = "This is a dryrun. As such, nothing was deleted. To delete these roles, use the command `"
         buf += self._res.cmd_prefix + "colourmod clean finalrun`."
         await self._client.send_msg(msg, buf)
      return

   # TODO: Maybe automatically delete unused roles here.
   # async def on_member_remove(self, member):
      # return
   # async def on_member_update(self, before, after):
      # return

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
   
