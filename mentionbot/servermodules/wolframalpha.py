import asyncio

import discord
import wolframalpha
import traceback

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered
from ..enums import PrivilegeLevel

@registered
class WolframAlpha(ServerModule):

   MODULE_NAME = "Wolfram Alpha"
   MODULE_SHORT_DESCRIPTION = "Conveniently allows you to send and receive WA queries."
   RECOMMENDED_CMD_NAMES = ["wamanage"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {}

   _HELP_SUMMARY = """
      See `{modhelp}` to manage the Wolfram Alpha module.
      `[p]wa [query]` - Make a Wolfram Alpha query.
      `[p]define [word]` - Get word definition from WA.
      """

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

      self._res.suppress_autokill(True)
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

   @cmd.add(_cmdd, "query", "q", top="wa")
   async def _cmdf_query(self, substr, msg, privilege_level):
      """`{cmd} [query]` - Make a Wolfram Alpha query."""
      if substr == "":
         await self._client.send_msg(msg, "Error: No text input made for query. Aborting.")
      else:
         result = await self.wa_query(substr, msg.channel)
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
         if len(buf) == 0:
            buf = "No result."
         await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "define", "def", top="define")
   async def _cmdf_define(self, substr, msg, privilege_level):
      """`{cmd} [word]` - Get word definition from WA."""
      if substr == "":
         await self._client.send_msg(msg, "Error: No text input made for query. Aborting.")
      else:
         result = await self.wa_query("define " + substr, msg.channel)
         buf = ""
         try:
            pods = list(result.pods)
            buf = "**" + pods[0].text + "**\n" + pods[1].text
         except:
            print(traceback.format_exc())
            buf = "Error: Unknown error. Aborting."
         if len(buf) == 0:
            buf = "No result."
         await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "maxpods")
   async def _cmdf_maxpods(self, substr, msg, privilege_level):
      """`{cmd}` - Get the max number of pods shown."""
      await self._client.send_msg(msg, "Max pods: " + str(self._max_pods))
      return

   @cmd.add(_cmdd, "setmaxpods")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_setmaxpods(self, substr, msg, privilege_level):
      """`{cmd} [integer]` - Get the max number of pods shown."""
      new_max_pods = None
      try:
         new_max_pods = int(substr)
      except:
         raise errors.InvalidCommandArgumentsError

      if new_max_pods < 1:
         raise errors.InvalidCommandArgumentsError
      self._max_pods = new_max_pods
      await self._client.send_msg(msg, "New max pods set to " + str(self._max_pods) + ".")
      return

   @cmd.add(_cmdd, "showtext")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_showtext(self, substr, msg, privilege_level):
      """`{cmd} [true|false]` - Set whether or not queries show text results."""
      if utils.str_says_true(substr):
         self._show_text = True
         await self._client.send_msg(msg, "Queries now show text.")
      else:
         if self._show_img:
            self._show_text = False
            await self._client.send_msg(msg, "Queries no longer show text.")
         else:
            await self._client.send_msg(msg, "Error: Must show at least text or images.")
      return

   @cmd.add(_cmdd, "showimg")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_showimg(self, substr, msg, privilege_level):
      """`{cmd} [true|false]` - Set whether or not queries show image results"""
      if utils.str_says_true(substr):
         self._show_img = True
         await self._client.send_msg(msg, "Queries now show images.")
      else:
         if self._show_text:
            self._show_img = False
            await self._client.send_msg(msg, "Queries no longer show images.")
         else:
            await self._client.send_msg(msg, "Error: Must show at least text or images.")
      return

   @cmd.add(_cmdd, "reloadsettings")
   async def _cmdf_cmdnotimplemented(self, substr, msg, privilege_level):
      """`{cmd}`"""
      self._load_settings()
      await self._client.send_msg(msg, "Wolfram Alpha settings reloaded successfully.")
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

