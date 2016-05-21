import asyncio

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered

@registered
class MentionsNotify(ServerModule):

   MODULE_NAME = "Mentions Notify"
   MODULE_SHORT_DESCRIPTION = "PMs offline users when mentioned."
   RECOMMENDED_CMD_NAMES = ["mnotify", "mentionsnotify", "mn"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {}

   _HELP_SUMMARY = """
      `{modhelp}` - Mentions notification system.
      """

   async def _initialize(self, resources):
      self._res = resources
      self._client = resources.client

      self._res.suppress_autokill(True)
      return

   async def process_cmd(self, substr, msg, privilege_level):
      await self._client.send_msg(msg, "The notify module currently has no commands. Sorry!")
      return

   async def on_message(self, msg):
      for member in msg.mentions:
         if str(member.status) != "offline":
            continue
         buf = "Hello! <@" + msg.author.id + "> mentioned you in <#" + msg.channel.id + "> while you were offline."
         buf += "\n**Message contents are as follows:**"
         buf += "\n" + msg.content
         await self._client.send_msg(member, buf)
         print("MentionNotifyModule: A notification was sent!")
      return




