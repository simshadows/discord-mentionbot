import asyncio

import discord
import wolframalpha

import utils
import errors
from servermodule import ServerModule

class WolframAlpha(ServerModule):

   RECOMMENDED_CMD_NAMES = ["wamanage"]

   MODULE_NAME = "Wolfram Alpha"
   MODULE_SHORT_DESCRIPTION = "Conveniently allows you to send and receive WA queries."

   _HELP_SUMMARY_LINES = """
`{pf}wa [query]` - Make a Wolfram Alpha query.
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
`{pf}wa [query]` - Make a Wolfram Alpha query.
   """.strip().splitlines()

   _WA_APP_ID = "" # Change this...

   def __init__(self, cmd_names, client):
      self._client = client
      self._cmd_names = cmd_names

      self._wa_client = wolframalpha.Client(WolframAlpha._WA_APP_ID)
      return

   @classmethod
   def get_instance(cls, cmd_names, client, server):
      return WolframAlpha(cmd_names, client)

   @property
   def cmd_names(self):
      return self._cmd_names

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      str_wa = default_cmd_prefix + "wa "
      if content.startswith(str_wa): # TODO: IMPORTANT! FIX THE INCONSISTENCY.
         content = utils.change_base_cmd(content, default_cmd_prefix, self._cmd_names[0] + " q")

      return content

   def get_help_summary(self, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_SUMMARY_LINES, cmd_prefix, privilegelevel)

   def get_help_detail(self, substr, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_DETAIL_LINES, cmd_prefix, privilegelevel)

   async def process_cmd(self, substr, msg, privilegelevel=0):
      
      # Process the command itself
      (left, right) = utils.separate_left_word(substr)
      if (left == "query") or (left == "q"):
         if right == "":
            await self._client.send_msg(msg, "Error: No text input made for query. Aborting.")
         else:
            self._client.send_typing(msg.channel)
            result = self._wa_client.query(right)
            result_pod = None
            for pod in result.pods:
               if str(pod.title) == "Result":
                  result_pod = pod
                  break
            if result_pod is None:
               await self._client.send_msg(msg, "Error: Result pod not found.")
            else:
               try:
                  buf = "```\n" + result_pod.text + "\n```" + result_pod.img
                  await self._client.send_msg(msg, buf)
               except:
                  await self._client.send_msg(msg, "Error: Unknown error. Aborting.")

      elif (left == "query2") or (left == "q2"):
         if privilegelevel < PrivilegeLevel.TRUSTED:
            raise errors.CommandPrivilegeError

         if right == "":
            await self._client.send_msg(msg, "Error: No text input made for query. Aborting.")
         else:
            self._client.send_typing(msg.channel)
            result = self._wa_client.query(right)
            buf = ""
            for pod in result.pods:
               buf += "**" + str(pod.title) + ":**\n"
               if not pod.img is None:
                  buf += str(pod.img) + "\n"
               buf += str(pod.text) + "\n\n"
            buf = buf[:-2] # Trim off last two newlines
            await self._client.send_msg(msg, buf)

      elif (left == "query3") or (left == "q3"):
         if privilegelevel < PrivilegeLevel.TRUSTED:
            raise errors.CommandPrivilegeError

         if right == "":
            await self._client.send_msg(msg, "Error: No text input made for query. Aborting.")
         else:
            self._client.send_typing(msg.channel)
            result = self._wa_client.query(right)
            for pod in result.pods:
               buf = "**" + str(pod.title) + ":**\n"
               if not pod.img is None:
                  buf += str(pod.img) + "\n"
               buf += "```\n" + str(pod.text) + "\n```"
               await self._client.send_msg(msg, buf)

      else:
         raise errors.InvalidCommandArgumentsError

      return

