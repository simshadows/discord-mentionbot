import asyncio
import collections
import string
import textwrap

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule
from ..enums import PrivilegeLevel

class PMGreetings(ServerModule):

   MODULE_NAME = "PM Greetings"
   MODULE_SHORT_DESCRIPTION = "Sends greetings to new members via PM."
   RECOMMENDED_CMD_NAMES = ["pmgreetings", "pmgreeting"]

   _SECRET_TOKEN = utils.SecretToken()
   _cmd_dict = {} # Empty dict should work...

   _HELP_SUMMARY = """
See `{modhelp}` to manage the new-member PM greeting system.
   """.strip()

   _MEMBER_NAME_IDENTIFIER = "memname"
   _SERVER_NAME_IDENTIFIER = "servername"

   _SUBSTITUTION_INFO = textwrap.dedent("""
      When setting the greeting message, substitutions can be made.
      `${0}` substitutes into the member's name, and `${1}` substitutes into the server's name.
      
      Escaping: If you want to add a literal `${0}`, you can escape `$` by with `$${0}`. Similarly is done with `${1}`.
      """).format(_MEMBER_NAME_IDENTIFIER, _SERVER_NAME_IDENTIFIER).strip()

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client

      self._greeting_template = "YO DAWG"

      self._res.suppress_autokill(True)
      return

   def get_help_detail(self, substr, privilege_level, module_alias):
      buf = "This module sends personalized greeting messages to new members via PM.\n\n"
      buf += self._SUBSTITUTION_INFO
      buf += "\n\n**Available Commands:**\n"
      buf = buf.format(self._MEMBER_NAME_IDENTIFIER, self._SERVER_NAME_IDENTIFIER).strip()
      buf += "\n" + super(PMGreetings, self).get_help_detail(substr, privilege_level, module_alias)
      return buf

   @cmd.add(_cmd_dict, "view", "viewmessage", "see", "get", "getmessage")
   async def _cmdf_view(self, substr, msg, privilege_level):
      """`{cmd}` - View a copy of the server greeting message."""
      buf = "**New members are sent the following:**\n"
      buf += self._get_server_greeting(msg.author.name)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "viewmono", "mono", "viewmessagemono", "seemono", "getmono", "getmessagemono")
   async def _cmdf_viewmono(self, substr, msg, privilege_level):
      """`{cmd}` - View a monospace copy of the server greeting message."""
      buf = "**Monospace copy of the server greeting message:**\n```\n"
      buf += self._get_server_greeting(msg.author.name) + "\n```"
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "pm", "pmme", "send", "sendme")
   async def _cmdf_view(self, substr, msg, privilege_level):
      """`{cmd}` - Get a personalized version of the greeting message via PM."""
      await self.on_member_join(msg.author)
      await self._client.send_msg(msg, "<@{}>, check your inbox!".format(msg.author.id))
      return

   @cmd.add(_cmd_dict, "set", "setmessage")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_setmessage(self, substr, msg, privilege_level):
      """
      `{cmd} [message contents]` - Set the server greeting message.

      For information on what tokens are used, see `{p}help {mod}`.
      """
      if len(substr) == 0:
         await self._client.send_msg(msg, self._SUBSTITUTION_INFO)
         return
      elif len(substr) > 1800: # This value is arbitrary.
         await self._client.send_msg(msg, "Error: Message is too long.")
         return
      self._greeting_template = substr
      await self._client.send_msg(msg, "Successfully set the new greeting PM. Please double-check.")
      return

   async def on_member_join(self, member):
      buf = self._get_server_greeting(member.name) # Note: Errors will propagate out.
      await self._client.send_msg(member, buf)
      return

   def _get_server_greeting(self, new_member_name):
      mapping = {
         self._MEMBER_NAME_IDENTIFIER: new_member_name,
         self._SERVER_NAME_IDENTIFIER: self._res.server.name,
      }
      return string.Template(self._greeting_template).safe_substitute(mapping)
