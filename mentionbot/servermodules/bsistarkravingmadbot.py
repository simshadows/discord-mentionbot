import asyncio
import random

import discord

import utils
import errors
from servermodule import ServerModule
import cmd

class BsiStarkRavingMadBot(ServerModule):

   MODULE_NAME = "BSI StarkRavingMadBot"
   MODULE_SHORT_DESCRIPTION = "Allows this bot to stand-in for the bot *StarkRavingMadBot*."
   RECOMMENDED_CMD_NAMES = ["bsistarkravingmadbot", "stark"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmd_dict = {}
   _cmd_prep_factory = cmd.CMDPreprocessorFactory()

   _HELP_SUMMARY = """
See `{modhelp}` for StarkRavingMadBot standin commands.
   """.strip()

   # STARK_PF = "$" # TODO: Consider implementing this.

   STARK_HELP = """
**I'm acting as a stand-in for StarkRavingMadBot.**
**I have the following commands implemented:**
- $avatar
- $blame
- $choose
- $color
~~- $doot~~
- $flip
- $git
- $help
~~- $intensify~~
~~- $invite~~
~~- $pengu~~
~~- $reddit~~
- $rip
- $roll
- $say
- $serverstats
- $sleep
~~- $spooderman~~
~~- $subreddit~~
- $swole
~~- $truth~~
~~- $ud~~
- $whois

*Reference commit: 89c88d92c98e7ccdf4b45092b6a139982d01acec, 6/2/16*
*Disclaimer: Behaviour may not match up 1:1.*
For reference, I require the following modules to be installed:
`Basic Information`
`Random`
   """.strip()

   STARKRAVINGMADBOT_DEFAULTID = "121281613660160000"

   _MBTI_TYPES = [
      "INTJ","INTP","ENTJ","ENTP","INFJ","INFP","ENFJ","ENFP",
      "ISTJ","ISFJ","ESTJ","ESFJ","ISTP","ISFP","ESTP","ESFP",
   ]
   _MBTI_TYPES_SET = set(_MBTI_TYPES) # Faster access to get set membership

   async def _initialize(self, resources):
      self._client = resources.client
      self._server = resources.server
      self._res = resources

      # pf = self._client.get_server_bot_instance(self._server).cmd_prefix
      pf = "/"
      this = pf + self._cmd_names[0]
      cmdnotimplemented = this + " cmdnotimplemented"

      self._stark = self._client.search_for_user(self.STARKRAVINGMADBOT_DEFAULTID, enablenamesearch=False, serverrestriction=self._server)
      self._preprocessor_replace = { # Maps commands to their exact substitute.
         "avatar": pf + "basicinfo avatar",
         "blame": this + " blame",
         "choose": pf + "random choose",
         "color": pf + "colour",
         "colour": pf + "colour",
         "doot": cmdnotimplemented,
         "flip": pf + "random coin",
         "functions": pf + "jcfdiscord functions",
         "git": this + " git",
         "help": this + " help",
         "intensify": cmdnotimplemented,
         "invite": cmdnotimplemented,
         "noot": pf + "jcfdiscord noot",
         "pengu": cmdnotimplemented,
         "reddit": cmdnotimplemented,
         "rip": this + " rip",
         "roll": pf + "random dice",
         "say": this + " say",
         "serverstats": pf + "basicinfo server",
         "sleep": this + " sleep",
         "spooderman": cmdnotimplemented,
         "subreddit": cmdnotimplemented,
         "swole": pf + "jcfdiscord swole",
         "truth": cmdnotimplemented,
         "ud": cmdnotimplemented,
         "whois": pf + "basicinfo user",
      }

      self._sleep_choices = [
         "Go to sleep",
         "Git to bed",
         "The addiction is more satisfying while conscious",
         "(ﾉಠ_ಠ)ﾉ*:・ﾟ✧\ngit to sleep"
      ]

      self._c = self._cmd_names[0] # A shorter name. This will be used a LOT.
      return

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      content = await super(BsiStarkRavingMadBot, self).msg_preprocessor(content, msg, default_cmd_prefix)
      
      if self.dont_run_module():
         return content # Short-circuit if stark is not offline.

      if content.startswith("$"):
         new_content = content[1:]
         (left, right) = utils.separate_left_word(new_content)
         
         # Deal with type flair commands
         if left.upper() in self._MBTI_TYPES_SET:
            return default_cmd_prefix + "jcfdiscord typeflair " + left

         # Any other command
         try:
            left = self._preprocessor_replace[left.lower()]
         except KeyError:
            return content
         if right == "":
            return left
         else:
            return left + " " + right
      return content

   @cmd.add(_cmd_dict, "cmdnotimplemented")
   async def _cmdf_cmdnotimplemented(self, substr, msg, privilege_level):
      """`{cmd}` - (Please don't use this command.)"""
      buf = "Sorry, I haven't implemented my own version of that command yet."
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "help")
   async def _cmdf_help(self, substr, msg, privilege_level):
      """`{cmd}` - Get a stand-in version of Stark's help message."""
      await self._client.send_msg(msg, self.STARK_HELP)
      return

   @cmd.add(_cmd_dict, "blame")
   @cmd.preprocess(_cmd_prep_factory)
   async def _cmdf_blame(self, substr, msg, privilege_level):
      """`{p}{c}`"""
      if (substr == "<@{}>".format(self._res.botowner_ID)) or (substr == "<@{}>".format(self._res.me_ID)):
         # TODO: Consider also checking name matches... idk
         buf = "{} did nothing wrong."
      elif random.getrandbits(1):
         buf = "Fuck you {}."
      else:
         buf = "Thanks, {}!"
      if len(substr) == 0:
         await self._client.send_msg(msg, buf.format("<@" + msg.author.id+ ">"))
      else:
         await self._client.send_msg(msg, buf.format(substr))
      return

   @cmd.add(_cmd_dict, "doot")
   @cmd.preprocess(_cmd_prep_factory)
   async def _cmdf_doot(self, substr, msg, privilege_level):
      """`{p}{c}`"""
      # var m = await Client.SendMessage(e.Channel, "doot doot");
      # await Task.Delay(1000);
      # TODO: Figure out how to do this with asyncio without hanging up the bot for the whole 1 second...
      await self._client.send_msg(msg, "doot doot (thank mr skeltal)")
      return

   @cmd.add(_cmd_dict, "git")
   async def _cmdf_git(self, substr, msg, privilege_level):
      """`{cmd}` - Get a stand-in version of Stark's source command."""
      buf = "*Now, I'm not StarkRavingMadBot, but here's a copy-paste of what it would've said:*"
      buf += "\n\"You can find my source at https://github.com/josh951623/StarkRavingMadBot/tree/master. If you'd like to suggest a feature, go ahead and join me in my dev server: https://discord.gg/0ktzcmJwmeWuQtiM.\""
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "say")
   async def _cmdf_say(self, substr, msg, privilege_level):
      """`{cmd}`"""
      await self._client.send_msg(msg, "m8")
      return

   @cmd.add(_cmd_dict, "sleep")
   @cmd.preprocess(_cmd_prep_factory)
   async def _cmdf_sleep(self, substr, msg, privilege_level):
      """`{p}{c}`"""
      # The original command takes a user mention from substr and appends it to the end.
      # so "$sleep" -> "Go to sleep"
      # and "$sleep <@123> <@456>" -> "Go to sleep <@123>"
      # Something like that.
      await self._client.send_msg(msg, random.choice(self._sleep_choices))
      return

   @cmd.add(_cmd_dict, "rip")
   @cmd.preprocess(_cmd_prep_factory)
   async def _cmdf_rip(self, substr, msg, privilege_level):
      """`{p}{c}`"""
      await self._client.send_msg(msg, "doesnt even deserve a funeral")
      return

   def dont_run_module(self):
      try:
         return not utils.member_is_offline(self._stark)
      except AttributeError:
         return False

