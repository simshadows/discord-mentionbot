import asyncio

import discord

import utils
import errors
from enums import PrivilegeLevel
from servermodule import ServerModule

class JCFDiscord(ServerModule):

   RECOMMENDED_CMD_NAMES = ["jcfdiscord"]

   MODULE_NAME = "JCFDiscord"
   MODULE_SHORT_DESCRIPTION = "Functions built specifically for the JCFDiscord community."

   _HELP_SUMMARY_LINES = """
`{pf}functions [types]` - Get a list of MBTI function stacks.
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
`{pf}functions [types]` - Get a list of MBTI function stacks.
   """.strip().splitlines()

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

   def __init__(self, cmd_names, resources):
      self._res = resources

      self._client = self._res.client
      self._cmd_names = cmd_names
      return

   @classmethod
   def get_instance(cls, cmd_names, resources):
      return JCFDiscord(cmd_names, resources)

   @property
   def cmd_names(self):
      return self._cmd_names

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      str_functions = default_cmd_prefix + "functions"
      str_rip = default_cmd_prefix + "rip"
      if content.startswith(str_functions + " ") or (content == str_functions): # TODO: IMPORTANT! FIX THE INCONSISTENCY.
         content = utils.add_base_cmd(content, default_cmd_prefix, self._cmd_names[0])
      elif content.startswith(str_rip + " ") or (content == str_rip): # TODO: IMPORTANT! FIX THE INCONSISTENCY.
         content = utils.add_base_cmd(content, default_cmd_prefix, self._cmd_names[0])
      return content

   def get_help_summary(self, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_SUMMARY_LINES, cmd_prefix, privilegelevel)

   def get_help_detail(self, substr, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_DETAIL_LINES, cmd_prefix, privilegelevel)

   async def process_cmd(self, substr, msg, privilegelevel=0):
      
      # Process the command itself
      (left, right) = utils.separate_left_word(substr)
      if (left == "functions") or (left == "fn") or (left == "stack"):
         args = right.split()
         types = []
         for arg in args:
            arg = arg.upper()
            if arg in self._MBTI_TYPES:
               types.append(arg)
         if len(types) == 0:
            types = self._MBTI_TYPES
         buf = "```\n"
         for mbti_type in types:
            buf += mbti_type + " = " + self._FUNCTION_STACKS[mbti_type] + "\n"
         buf += "```"
         await self._client.send_msg(msg, buf)

      else:
         raise errors.InvalidCommandArgumentsError

      return

