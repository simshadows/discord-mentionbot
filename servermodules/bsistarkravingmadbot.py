import asyncio

import discord

import utils
import errors
from servermodule import ServerModule

class BsiStarkRavingMadBot(ServerModule):

   RECOMMENDED_CMD_NAMES = ["bsistarkravingmadbot", "stark"]

   MODULE_NAME = "BSI StarkRavingMadBot"
   MODULE_SHORT_DESCRIPTION = "Allows this bot to stand-in for the bot *StarkRavingMadBot*."

   _HELP_SUMMARY_LINES = """
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
   """.strip().splitlines()

   # STARK_PF = "$" # TODO: Consider implementing this.

   STARK_HELP = """
**I'm acting as a stand-in for StarkRavingMadBot.**
**I have the following commands implemented:**
- $avatar
~~- $blame~~
- $choose
~~- $color~~
~~- $doot~~
- $flip
- $git
- $help
~~- $intensify~~
~~- $invite~~
~~- $pengu~~
~~- $reddit~~
~~- $rip~~
- $roll
- $say
- $serverstats
~~- $sleep~~
~~- $spooderman~~
~~- $subreddit~~
~~- $swole~~
~~- $truth~~
~~- $ud~~
- $whois
*Reference commit: 89c88d92c98e7ccdf4b45092b6a139982d01acec, 6/2/16*
*Disclaimer: Behaviour may not match up 1:1.*

For reference, I require the following modules to be installed:
`Basic Information`
`Random`
   """.strip()

   STARKRAVINGMADBOT_DEFAULTID = str(121281613660160000)

   def __init__(self, cmd_names, client, server):
      self._client = client
      self._server = server
      self._cmd_names = cmd_names

      # pf = self._client.get_server_bot_instance(self._server).cmd_prefix
      pf = "/"
      this = pf + self._cmd_names[0]
      cmdnotimplemented = this + " cmdnotimplemented"

      self._stark = self._client.search_for_user(self.STARKRAVINGMADBOT_DEFAULTID, enablenamesearch=False, serverrestriction=self._server)
      self._preprocessor_replace = { # Maps commands to their exact substitute.
         "$avatar": pf + "basicinfo avatar",
         "$blame": cmdnotimplemented,
         "$choose": pf + "random choose",
         "$color": cmdnotimplemented,
         "$doot": cmdnotimplemented,
         "$flip": pf + "random coin",
         "$git": this + " git",
         "$help": this + " help",
         "$intensify": cmdnotimplemented,
         "$invite": cmdnotimplemented,
         "$pengu": cmdnotimplemented,
         "$reddit": cmdnotimplemented,
         "$rip": cmdnotimplemented,
         "$roll": pf + "random dice",
         "$say": this + " say",
         "$serverstats": pf + "basicinfo server",
         "$sleep": cmdnotimplemented,
         "$spooderman": cmdnotimplemented,
         "$subreddit": cmdnotimplemented,
         "$swole": cmdnotimplemented,
         "$truth": cmdnotimplemented,
         "$ud": cmdnotimplemented,
         "$whois": pf + "basicinfo user",
      }

      self._c = self._cmd_names[0] # A shorter name. This will be used a LOT.
      return

   @classmethod
   def get_instance(cls, cmd_names, client, server):
      return BsiStarkRavingMadBot(cmd_names, client, server)

   @property
   def cmd_names(self):
      return self._cmd_names

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      if self.dont_run_module():
         return content # Short-circuit if stark is not offline.
      
      # IMPORTANT: This might be a problem if the message implementation of
      #            StarkRavingMadBot changes. e.g. if messages are
      #            invoked with a prefix that has a space.
      (left, right) = utils.separate_left_word(content)
      print(left)
      try:
         left = self._preprocessor_replace[left]
      except KeyError:
         return content

      if right == "":
         return left
      else:
         return left + " " + right

   def get_help_summary(self, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_SUMMARY_LINES, cmd_prefix, privilegelevel)

   def get_help_detail(self, substr, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_DETAIL_LINES, cmd_prefix, privilegelevel)

   async def process_cmd(self, substr, msg, privilegelevel=0):
      
      # Process the command itself
      (left, right) = utils.separate_left_word(substr)
      if left == "cmdnotimplemented":
         buf = "Sorry, I haven't implemented my own version of that command yet."
         await self._client.send_msg(msg, buf)

      elif left == "help":
         await self._client.send_msg(msg, self.STARK_HELP)

      elif left == "git":
         buf = "*Now, I'm not StarkRavingMadBot, but here's a copy-paste of what it would've said:*"
         buf += "\n\"You can find my source at https://github.com/josh951623/StarkRavingMadBot/tree/master. If you'd like to suggest a feature, go ahead and join me in my dev server: https://discord.gg/0ktzcmJwmeWuQtiM.\""
         await self._client.send_msg(msg, buf)

      elif left == "say":
         await self._client.send_msg(msg, "m8")

      else:
         raise errors.InvalidCommandArgumentsError

      return

   def dont_run_module(self):
      try:
         return not utils.member_is_offline(self._stark)
      except AttributeError:
         return False

