import asyncio
import random

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered
from ..enums import PrivilegeLevel

@registered
class JCFDiscord(ServerModule):

   MODULE_NAME = "JCFDiscord"
   MODULE_SHORT_DESCRIPTION = "Functions built specifically for the JCFDiscord community."
   RECOMMENDED_CMD_NAMES = ["jcfdiscord"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmd_dict = {}

   _HELP_SUMMARY = """
      See `{modhelp}` for JCF Discord commands.
      """

   _FUNCTION_STACKS = {
      "INTJ": "Ni - Te - Fi - Se",
      "INTP": "Ti - Ne - Si - Fe",
      "ENTJ": "Te - Ni - Se - Fi",
      "ENTP": "Ne - Ti - Fe - Si",
      "INFJ": "Ni - Fe - Ti - Se",
      "INFP": "Fi - Ne - Si - Te",
      "ENFJ": "Fe - Ni - Se - Ti",
      "ENFP": "Ne - Fi - Te - Si",
      "ISTJ": "Si - Te - Fi - Ne",
      "ISFJ": "Si - Fe - Ti - Ne",
      "ESTJ": "Te - Si - Ne - Fi",
      "ESFJ": "Fe - Si - Ne - Ti",
      "ISTP": "Ti - Se - Ni - Fe",
      "ISFP": "Fi - Se - Ni - Te",
      "ESTP": "Se - Ti - Fe - Ni",
      "ESFP": "Se - Fi - Te - Ni",
   }

   _MBTI_TYPES = [
      "INTJ","INTP","ENTJ","ENTP","INFJ","INFP","ENFJ","ENFP",
      "ISTJ","ISFJ","ESTJ","ESFJ","ISTP","ISFP","ESTP","ESFP",
   ]
   _MBTI_TYPES_SET = set(_MBTI_TYPES) # Faster access to get set membership

   _EASTER_EGG_STACKS = {
      "ESPN": "Sp - Or - Ts - Tv", "ISPN": "Or - Sp - Tv - Ts",
      "ESPS": "Op - Sr - Ts - Tv", "ISPS": "Sr - Op - Tv - Ts",
      "ENPN": "Tp - Or - Ts - Sv", "INPN": "Or - Tp - Sv - Ts",
      "ENPS": "Op - Tr - Ss - Tv", "INPS": "Tr - Op - Tv - Ss",
      "ESJN": "Sp - Tr - Os - Tv", "ISJN": "Tr - Sp - Tv - Os",
      "ESJS": "Tp - Sr - Ts - Ov", "ISJS": "Sr - Tp - Ov - Ts",
      "ENJN": "Tp - Tr - Os - Sv", "INJN": "Tr - Tp - Sv - Os",
      "ENJS": "Tp - Tr - Ss - Ov", "INJS": "Tr - Tp - Ov - Ss",

      "XXXX": "Xx - Xx - Xx - Xx",
   }

   _EASTER_EGG_TYPES = [
      "ESPN", "ISPN", "ESPS", "ISPS", "ENPN", "INPN", "ENPS", "INPS",
      "ESJN", "ISJN", "ESJS", "ISJS", "ENJN", "INJN", "ENJS", "INJS",
      "XXXX",
   ]
   _EASTER_EGG_TYPES_SET = set(_EASTER_EGG_TYPES) # Faster access to get set membership

   _SWOLEBRO_ID = "100335016025788416"

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client

      self._res.suppress_autokill(True)
      return

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      if content.startswith(default_cmd_prefix):
         new_content = content[len(default_cmd_prefix):]
         (left, right) = utils.separate_left_word(new_content)
         if left.upper() in self._MBTI_TYPES_SET:
            return default_cmd_prefix + self.cmd_names[0] + " typeflair " + left
      return await super(JCFDiscord, self).msg_preprocessor(content, msg, default_cmd_prefix)

   @cmd.add(_cmd_dict, "functions", "fn", "stack")
   @cmd.top_level_alias("functions")
   async def _cmdf_functions(self, substr, msg, privilege_level):
      """`{cmd}`"""
      args = substr.split()
      types = []
      for arg in args:
         arg = arg.upper()
         if (arg in self._MBTI_TYPES_SET) or (arg in self._EASTER_EGG_TYPES_SET):
            types.append(arg)
      if len(types) == 0:
         types = self._MBTI_TYPES
      buf = "```\n"
      for mbti_type in types:
         function_stack_str = None
         if mbti_type in self._MBTI_TYPES_SET:
            function_stack_str = self._FUNCTION_STACKS[mbti_type]
         else:
            function_stack_str = self._EASTER_EGG_STACKS[mbti_type]
         buf += mbti_type + " = " + function_stack_str + "\n"
      buf += "```"
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "typeflair")
   async def _cmdf_typeflair(self, substr, msg, privilege_level):
      (left, right) = utils.separate_left_word(substr)
      new_role_name = left.upper()
      if not new_role_name in self._MBTI_TYPES_SET:
         raise errors.InvalidCommandArgumentsError
      new_role = utils.flair_name_to_object(self._res.server, new_role_name, case_sensitive=False)
      if new_role is None:
         await self._client.send_msg(msg, "Role '{}'' does not exist. Aborting with no changes.".format(new_role))
         raise errors.OperationAborted
      await utils.remove_flairs_by_name(self._client, msg.author, *self._MBTI_TYPES, case_sensitive=False)
      await self._client.add_roles(msg.author, new_role)
      await self._client.send_msg(msg, "Assigned <@{0}> the type flair '{1}'.".format(msg.author.id, new_role_name))
      return

   @cmd.add(_cmd_dict, "subreddit")
   async def _cmdf_noot(self, substr, msg, privilege_level):
      """`{cmd}`"""
      await self._client.send_msg(msg, "Our subreddit is at https://www.reddit.com/r/JCFDiscord/.")
      return

   @cmd.add(_cmd_dict, "swole")
   @cmd.top_level_alias()
   async def _cmdf_swole(self, substr, msg, privilege_level):
      """`{cmd}`"""
      if msg.author.id == self._SWOLEBRO_ID:
         await self._client.send_msg(msg, "Dude, you so swole <@{}>".format(self._SWOLEBRO_ID))
      elif ("fitness" in msg.channel.name.lower()) or ("swole" in msg.channel.name.lower()):
         await self._client.send_msg(msg, "<#{}> is the best place to get swole with swolebro.".format(msg.channel.id))
      else:
         await self._client.send_msg(msg, "Too bad you're not as swole as swolebro <@{}>.".format(msg.author.id))
      return

   @cmd.add(_cmd_dict, "noot")
   @cmd.top_level_alias()
   async def _cmdf_noot(self, substr, msg, privilege_level):
      """`{cmd}`"""
      # var m = await Client.SendMessage(e.Channel, "Penguins will rule the earth!");
      # await Task.Delay(1000);
      # TODO: Figure out how to do this with asyncio without hanging up the bot for the whole 1 second...
      await self._client.send_msg(msg, "noot noot")
      return

