import asyncio
import enum
import re

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered

@registered
class PMChannelInfo(ServerModule):

   MODULE_NAME = "PM Channel Info"
   MODULE_SHORT_DESCRIPTION = "((No short description...))"
   RECOMMENDED_CMD_NAMES = ["pmchinfo"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {}

   _HELP_SUMMARY = """
      `{modhelp}` - Channel info PM system.
      """

   class PrivilegeLevel(enum.IntEnum):
      DISABLED = 0
      PM_ONCE = 1
      AFTER_LAST_PM

   _default_settings = {
      "channel data": {}, # settings["channel data"][ch_id] = some data
      # The data associated with each channel ID will have the following format:
      # {
      #     "chid": string (channel ID),
      #     "message": string (the message that is PMed),
      #     "mode": enum (whether disabled, pm only once, pm after last pm, etc.),
      #     "timeperiod": datetime (use varies depending on mode.)
      #     "users": [{
      #        "uid": string (user ID),
      #        "last pmed": datetime (date of last PM received by the user),
      #        "last message": datetime (date of last message sent into the channel by the user.)
      #     }],
      # {
      # Data from storage is serialized, so must unserialize when loading settings.
   }

   async def _initialize(self, resources):
      self._res = resources
      self._client = resources.client

      self._ch_data = None # Initialize later.

      self._load_settings()

      self._res.suppress_autokill(True)
      return

   def _load_settings(self):
      settings_dict = self._res.get_settings(default=self._default_settings)
      settings = AttributeDictWrapper(settings_dict, self._default_settings)

      self._ch_data = settings.get("channel data")
      # Verify each channel data object.
      try:
         for (k, v) in self._ch_data.items():
            
            if not (isinstance(k, str) and (len(k) > 0)
                  and utils.re_digits.fullmatch(k) and isinstance(v, dict)):
               raise ValueError
            
            x = v["chid"]
            if not (isinstance(x, str) and (len(x) > 0) and
                  utils.re_digits.fullmatch(x)):
               raise ValueError

            x = v["message"]
            if not (isinstance(x, str) and (len(x) > 0)):
               raise ValueError

            x = v["mode"]


      except:
         self._ch_data = None
         raise
         
      return

   @cmd.add(_cmdd, "colour", "color", "rgb")
   async def _cmdf_colour(self, substr, msg, privilege_level):
      """`{cmd}` - Generates a random RGB colour code."""
      rand_int = random.randint(0,(16**6)-1)
      rand = hex(rand_int)[2:] # Convert to hex
      rand = rand.zfill(6)
      buf = "{}, your random colour is {} (decimal: {})".format(msg.author.name, rand, rand_int)
      buf += "\nhttp://www.colorhexa.com/{}.png".format(rand)
      await self._client.send_msg(msg, buf)
      return


   