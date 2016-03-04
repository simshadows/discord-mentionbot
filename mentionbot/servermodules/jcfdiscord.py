import asyncio
import random

import discord

import utils
import errors
from enums import PrivilegeLevel
from servermodule import ServerModule
import cmd

class JCFDiscord(ServerModule):

   MODULE_NAME = "JCFDiscord"
   MODULE_SHORT_DESCRIPTION = "Functions built specifically for the JCFDiscord community."
   RECOMMENDED_CMD_NAMES = ["jcfdiscord"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmd_dict = {}
   _cmd_prep_factory = cmd.CMDPreprocessorFactory()

   _HELP_SUMMARY = """
See `{modhelp}` for JCF Discord commands.
   """.strip()

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

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client
      return

   @cmd.add(_cmd_dict, "functions", "fn", "stack")
   @cmd.preprocess(_cmd_prep_factory, cmd_name="functions")
   async def _cmdf_functions(self, substr, msg, privilege_level):
      """`{cmd}`"""
      args = substr.split()
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
      return

   @cmd.add(_cmd_dict, "choosetruth")
   @cmd.preprocess(_cmd_prep_factory)
   async def _cmdf_choosetruth(self, substr, msg, privilege_level):
      """`{cmd}`"""
      topic = msg.channel.topic
      if topic is None:
         await self._client.send_msg(msg, "There doesn't appear to be a truth game in here.")
         raise errors.OperationAborted
      
      mentions = utils.get_all_mentions(topic)
      if len(mentions) == 0:
         await self._client.send_msg(msg, "There doesn't appear to be a truth game in here.")
         raise errors.OperationAborted
      
      try:
         mentions.remove(msg.author.id)
         if len(mentions) == 0:
            await self._client.send_msg(msg, "<@{}>".format(msg.author.id))
            raise errors.OperationAborted
      except ValueError:
         pass
      
      choice = random.choice(mentions)
      buf = "<@{}>\n".format(choice)
      buf += "My choices were: "
      for mention in mentions:
         user = self._client.search_for_user(mention, enablenamesearch=False, serverrestriction=self._res.server)
         if user is None:
            buf += "<@{}>, ".format(mention)
         else:
            buf += "{}, ".format(user.name)
      buf = buf[:-2]
      await self._client.send_msg(msg, buf)
      return

