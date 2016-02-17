import asyncio

import discord
import wolframalpha

import utils
import errors
from enums import PrivilegeLevel
from servermodule import ServerModule

class WolframAlpha(ServerModule):
   
   _SECRET_TOKEN = utils.SecretToken()

   RECOMMENDED_CMD_NAMES = ["wamanage"]

   MODULE_NAME = "Wolfram Alpha"
   MODULE_SHORT_DESCRIPTION = "Conveniently allows you to send and receive WA queries."

   _HELP_SUMMARY_LINES = """
`{pf}wa [query]` - Make a Wolfram Alpha query. (See `{pf}help wamanage` for more!)
`{pf}define [word]` - Get word definition from WA. (See `{pf}help wamanage` for more!)
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
`{pf}wa [query]` - Make a Wolfram Alpha query.
`{pf}define [word]` - Get word definition from WA. (See `{pf}help wamanage` for more!)
`{pf}wamanage maxpods` - Get the max number of pods shown.
>>> PRIVILEGE LEVEL 8000 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
`{pf}wamanage setmaxpods [integer]` - Get the max number of pods shown.
`{pf}wamanage showtext [true|false]` - Set whether or not queries show text results.
`{pf}wamanage showimg [true|false]` - Set whether or not queries show image results.
(NOTE: Settings are not persistently stored. This will change in the future.)
>>> PRIVILEGE LEVEL 0 >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>

(Pods are answers from Wolfram Alpha.)
   """.strip().splitlines()

   DEFAULT_SHARED_SETTINGS = {
      "wa app id": "PLACEHOLDER",
   }

   DEFAULT_SETTINGS = {
      "max pods": 2,
      "show text": "true",
      "show img": "false",
   }

   async def _initialize(self, resources):
      self._res = resources
      self._client = self._res.client

      self._max_pods = 2
      self._show_text = True
      self._show_img = False

      self._wa_app_ID = "PLACEHOLDER"
      self._wa_client = None

      self._load_settings()
      return

   def _load_settings(self):
      # Shared Settings
      global_settings = self._res.get_shared_settings()
      if global_settings is None:
         self._res.save_shared_settings(self.DEFAULT_SHARED_SETTINGS)
      else:
         try:
            self._wa_app_ID = global_settings["wa app id"]
         except KeyError:
            global_settings["wa app id"] = "PLACEHOLDER"
            self._res.save_shared_settings(global_settings)

      self._wa_client = wolframalpha.Client(self._wa_app_ID)

      # Server Settings
      settings = self._res.get_settings()
      if settings is None:
         self._res.save_settings(self.DEFAULT_SETTINGS)
      else:
         try:
            self._max_pods = settings["max pods"]
            self._show_text = utils.str_says_true(settings["show text"])
            self._show_img = utils.str_says_true(settings["show img"])
         except KeyError:
            settings["max pods"] = 2
            settings["show text"] = True
            settings["show img"] = False
            self._res.save_settings(settings)
      return

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      str_wa = default_cmd_prefix + "wa "
      str_define = default_cmd_prefix + "define "
      if content.startswith(str_wa): # TODO: IMPORTANT! FIX THE INCONSISTENCY.
         content = utils.change_base_cmd(content, default_cmd_prefix, self._cmd_names[0] + " q")
      elif content.startswith(str_define):
         content = utils.change_base_cmd(content, default_cmd_prefix, self._cmd_names[0] + " def")
      return content

   async def process_cmd(self, substr, msg, privilegelevel=0):
      
      # Process the command itself
      # Here, each query command has a different format, as a way of
      # documenting old formats I tried using.
      (left, right) = utils.separate_left_word(substr)
      if (left == "query") or (left == "q"):
         if right == "":
            await self._client.send_msg(msg, "Error: No text input made for query. Aborting.")
         else:
            result = await self.wa_query(right, msg.channel)
            buf = ""
            pods_to_fetch = self._max_pods
            try:
               unprinted_pod_titles = []
               for pod in result.pods:
                  if pods_to_fetch <= 0:
                     unprinted_pod_titles.append(str(pod.title))
                  else:
                     pods_to_fetch -= 1
                     buf += "**" + str(pod.title) + ":**\n"
                     try:
                        if self._show_text:
                           buf += "```\n" + pod.text + "\n```"
                        if self._show_img:
                           buf += str(pod.img) + "\n"
                        buf += "\n"
                     except:
                        buf += str(pod.img) + "\n\n"
               if len(unprinted_pod_titles) > 0:
                  buf += "*Unprinted pods: "
                  for title in unprinted_pod_titles:
                     buf += title + ", "
                  buf = buf[:-2] + "*"
            except:
               buf = "Error: Unknown error. Aborting."
            await self._client.send_msg(msg, buf)

      elif (left == "define") or (left == "def"):
         if right == "":
            await self._client.send_msg(msg, "Error: No text input made for query. Aborting.")
         else:
            result = await self.wa_query(right, msg.channel)
            buf = ""
            try:
               pods = list(result.pods)
               buf = pods[0].text + "\n" + pods[1].text
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

      elif left == "reloadsettings":
         self._load_settings()
         await self._client.send_msg(msg, "Wolfram Alpha settings reloaded successfully.")

      else:
         raise errors.InvalidCommandArgumentsError

      return

   async def wa_query(self, query_str, reply_channel):
      try:
         return self._wa_client.query(query_str)
      except:
         buf = "Error: No app ID has been registered."
         buf += "\nFor security reasons, the bot owner will need "
         buf += "to manually enter it into the module's shared `settings.json`."
         await self._client.send_msg(reply_channel, buf)
         raise errors.OperationAborted

