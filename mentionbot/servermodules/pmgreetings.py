import asyncio

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

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client

      self._greetings_enabled = True
      self._greeting_message = "YO DAWG"

      self._res.suppress_autokill(True)
      return

   def get_help_detail(self, substr, privilege_level, module_alias):
      buf = "At this module's present state, you can only have the default message.\n\n"
      buf += "**Available Commands:**\n"
      buf += super(PMGreetings, self).get_help_detail(substr, privilege_level, module_alias)
      return buf

   @cmd.add(_cmd_dict, "viewmessage")
   async def _cmdf_viewmessage(self, substr, msg, privilege_level):
      """`{cmd}` - View a copy of the server greeting message."""
      buf = "**The following message is what new members are sent:**"
      buf += self._get_server_greeting(msg.author.name)
      await self._client.send_msg(msg, buf)
      return

   async def on_member_join(self, member):
      if not self._greetings_enabled:
         return
      buf = self._get_server_greeting(member.name) # Note: Errors will propagate out.
      await self._client.send_msg(member, buf)
      return

   def _get_server_greeting(self, new_member_name):
      return self._greeting_message
