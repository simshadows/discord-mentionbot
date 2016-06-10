import asyncio
import random
import re
import urllib.parse as urllibparse
import json
import textwrap
import os

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered

@registered
class Misc(ServerModule):

   MODULE_NAME = "Misc"
   MODULE_SHORT_DESCRIPTION = "Miscellaneous commands."
   RECOMMENDED_CMD_NAMES = ["misc", "miscellaneous"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {}

   _HELP_SUMMARY = """
      `{modhelp}` - Miscellaneous commands.
      """

   _UD_MAX_DEFINITIONS = 2
   _UD_MSG_MAX_SIZE = 1800
   _UD_DEF_MAX_SIZE = 1800

   async def _initialize(self, resources):
      self._res = resources
      self._client = resources.client

      self._res.suppress_autokill(True)
      return

   @cmd.add(_cmdd, "lmgtfy", "google", "goog", "yahoo", top=True)
   async def _cmdf_say(self, substr, msg, privilege_level):
      """`{cmd} [text]` - Let me google that for you..."""
      if len(substr) == 0:
         raise errors.InvalidCommandArgumentsError
      await self._client.send_msg(msg, "http://lmgtfy.com/?q=" + urllibparse.quote(substr))
      return

   @cmd.add(_cmdd, "tex", "latex", top=True)
   async def _cmdf_tex(self, substr, msg, privilege_level):
      """
      `{cmd} [code]` - Generate a math equation from LaTeX code.

      This command uses the codecogs website.
      http://latex.codecogs.com/
      """
      if len(substr) == 0:
         raise errors.InvalidCommandArgumentsError
      url = "http://latex.codecogs.com/png.latex?\dpi{300}%20\huge%20"
      # url += substr.replace(" ", "%20")
      url += urllibparse.quote(substr)
      bytedata = None
      try:
         bytedata = utils.download_from_url(url)
         if len(bytedata) <= 100: # Arbitrary value...
            raise Exception
      except:
         buf = "<@{}>".format(msg.author.id)
         buf += " Error generating image. Is your LaTeX code correct?"
         await self._client.send_msg(msg, buf)
         return
      filename = utils.generate_temp_filename() + ".png"
      with open(filename, "wb") as f:
         f.write(bytedata)
      await self._client.perm_send_file(msg.channel, filename)
      os.remove(filename)
      return

   @cmd.add(_cmdd, "ud", "urbandictionary", "urban", top=True)
   async def _cmdf_ud(self, substr, msg, privilege_level):
      """`{cmd}` - Query urban dictionary."""
      if len(substr) == 0:
         raise errors.InvalidCommandArgumentsError
      substr_encoded = urllibparse.quote(substr)
      def_url = "http://www.urbandictionary.com/define.php?term=" + substr_encoded
      api_url = "http://api.urbandictionary.com/v0/define?term=" + substr_encoded
      
      buf = "{}".format(def_url)
      bytedata = utils.download_from_url(api_url)
      json_data = json.loads(bytedata.decode())

      # See https://github.com/zdict/zdict/wiki/Urban-dictionary-API-documentation
      # for API documentation.

      result_type = json_data["result_type"]
      if result_type == "no_results":
         buf = "Sorry fam, found nothing."
         buf += " See for yourself at " + def_url
         await self._client.send_msg(msg, buf)
         return
      elif result_type != "exact":
         buf += "\n**Result type:** " + str(result_type)

      def_list = json_data["list"]
      if len(def_list) == 0:
         raise RuntimeError("Expected >0 definitions.")

      buf += "\n**Found " + str(len(def_list)) + " definitions. "
      buf += "Displaying top " + str(self._UD_MAX_DEFINITIONS)
      # NOTE: The number self._UD_MAX_DEFINITIONS is merely a placeholder,
      # chosen as the number's string representation's length matches the
      # maximum expected to be printed. We will remove it later.
      
      buf2 = "**."
      defs_printed = 0
      for def_item in def_list:
         tmp_buf1 = textwrap.dedent("""
            **Word:** {word}
            **Votes:** +{thumbs_up} -{thumbs_down}
            **Author:** {author}
            """).strip().format(**def_item)
         tmp_buf2 = textwrap.dedent("""
            ```
            {definition}

            Example:
            {example}
            ```
            """).strip().format(**def_item)
         def_buf = "\n\n" + tmp_buf1
         
         if ((len(tmp_buf2) > self._UD_MSG_MAX_SIZE - len(def_buf) - len(buf2) - len(buf)) or
               (len(tmp_buf2) > self._UD_DEF_MAX_SIZE)):
            def_buf += "\n*The definition is too large to display. Follow the link to view it in browser.*"
            def_buf += "\n" + def_item["permalink"]
         else:
            def_buf += "\n" + tmp_buf2

         if len(def_buf) > self._UD_MSG_MAX_SIZE - len(buf2) - len(buf):
            break

         defs_printed += 1
         buf2 += def_buf
         if defs_printed == self._UD_MAX_DEFINITIONS:
            break

      # Now we complete the process of assembling the string.
      # This is the bit where we remove the placeholder number.
      buf = buf[:-len(str(self._UD_MAX_DEFINITIONS))]
      buf += str(defs_printed) + buf2

      await self._client.send_msg(msg, buf)
      return


   