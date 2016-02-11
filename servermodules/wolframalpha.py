import asyncio

import discord
import wolframalpha

import utils
import errors
from enums import PrivilegeLevel
from servermodule import ServerModule

class WolframAlpha(ServerModule):

   RECOMMENDED_CMD_NAMES = ["wamanage"]

   MODULE_NAME = "Wolfram Alpha"
   MODULE_SHORT_DESCRIPTION = "Conveniently allows you to send and receive WA queries."

   _HELP_SUMMARY_LINES = """
`{pf}wa [query]` - Make a Wolfram Alpha query. (See `{pf}help wamanage` for more!)
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
`{pf}wa [query]` - Make a Wolfram Alpha query.
`{pf}wamanage maxpods` - Get the max number of pods shown.
>>> PRIVILEGE LEVEL 8000 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
`{pf}wamanage setmaxpods [integer]` - Get the max number of pods shown.
`{pf}wamanage showtext [true|false]` - Set whether or not queries show text results.
`{pf}wamanage showimg [true|false]` - Set whether or not queries show image results.
(NOTE: Settings are not persistently stored. This will change in the future.)
>>> PRIVILEGE LEVEL 0 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

(Pods are answers from Wolfram Alpha.)
   """.strip().splitlines()

   _WA_APP_ID = "" # Change this...

   def __init__(self, cmd_names, client):
      self._client = client
      self._cmd_names = cmd_names

      self._max_pods = 2
      self._show_text = True
      self._show_img = False

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
      # Here, each query command has a different format, as a way of
      # documenting old formats I tried using.
      (left, right) = utils.separate_left_word(substr)
      if (left == "query") or (left == "q"):
         if right == "":
            await self._client.send_msg(msg, "Error: No text input made for query. Aborting.")
         else:
            self._client.send_typing(msg.channel)
            result = self._wa_client.query(right)
            buf = ""
            pods_to_fetch = self._max_pods
            try:
               for pod in result.pods:
                  if pods_to_fetch <= 0:
                     buf += "*Unprinted pod: " + str(pod.title) + "*\n"
                  else:
                     pods_to_fetch += -1
                     buf += "**" + str(pod.title) + ":**\n"
                     if self._show_text:
                        buf += "```\n" + pod.text + "\n```\n"
                     if self._show_img:
                        buf += str(pod.img) + "\n"
               buf = buf[:-1] # Trim off extra newline
            except:
               buf = "Error: Unknown error. Aborting."
            await self._client.send_msg(msg, buf)

      elif left == "maxpods":
         await self._client.send_msg(msg, "Max pods: " + str(self._max_pods))

      elif left == "setmaxpods":
         if privilegelevel < PrivilegeLevel.ADMIN:
            raise errors.CommandPrivilegeError

         new_max_pods = None
         try:
            new_max_pods = int(right)
         except:
            raise errors.InvalidCommandArgumentsError

         if new_max_pods < 1:
            raise errors.InvalidCommandArgumentsError
         self._max_pods = new_max_pods
         await self._client.send_msg(msg, "New max pods set to " + str(self._max_pods) + ".")

      elif left == "showtext":
         if privilegelevel < PrivilegeLevel.ADMIN:
            raise errors.CommandPrivilegeError

         if utils.str_says_true(right):
            self._show_text = True
            await self._client.send_msg(msg, "Queries now show text.")
         else:
            if self._show_img:
               self._show_text = False
               await self._client.send_msg(msg, "Queries no longer show text.")
            else:
               await self._client.send_msg(msg, "Error: Must show at least text or images.")

      elif left == "showimg":
         if privilegelevel < PrivilegeLevel.ADMIN:
            raise errors.CommandPrivilegeError

         if utils.str_says_true(right):
            self._show_img = True
            await self._client.send_msg(msg, "Queries now show images.")
         else:
            if self._show_text:
               self._show_img = False
               await self._client.send_msg(msg, "Queries no longer show images.")
            else:
               await self._client.send_msg(msg, "Error: Must show at least text or images.")

      else:
         raise errors.InvalidCommandArgumentsError

      return

