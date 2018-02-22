import asyncio
import random
import textwrap
import datetime

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
   _cmdd = {}

   _HELP_SUMMARY = """
      `{modhelp}` - JCF Discord commands.
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
   _MBTI_TYPES = sorted([k for (k,v) in _FUNCTION_STACKS.items()])
   _MBTI_TYPES_SET = set(_MBTI_TYPES) # Faster access to get set membership

   _EASTER_EGG_STACKS = {
      "ESPN": "Sp - Or - Ts - Tv",
      "XXXX": "Xx - Xx - Xx - Xx",
      "CUTE": "Ra - Wr - Xd - :3",
      "JOSH": "Jo - Sh - Jo - Sh",
      "BUSY": "Bu - Sy - Bo - Dy",
      "NSFW": "Bo - Ob - Di - Ck",
      "BOTS": "Si - Te - Fi - Ne",
      "POOP": "Di - Ar - Rh - Ea",
      "PTSD": "Tr - Ig - Ge - Rd",
      # "PHIL": "Sh - It - He - Ad",
      "AIDS": "In - Fe - Ct - Ed",
      "TWAT": "Sh - It - He - Ad",
      "NICE": "Si - Fe - Ti - Ne",
   }
   # "ESPN": "Sp - Or - Ts - Tv", "ISPN": "Or - Sp - Tv - Ts",
   # "ESPS": "Op - Sr - Ts - Tv", "ISPS": "Sr - Op - Tv - Ts",
   # "ENPN": "Tp - Or - Ts - Sv", "INPN": "Or - Tp - Sv - Ts",
   # "ENPS": "Op - Tr - Ss - Tv", "INPS": "Tr - Op - Tv - Ss",
   # "ESJN": "Sp - Tr - Os - Tv", "ISJN": "Tr - Sp - Tv - Os",
   # "ESJS": "Tp - Sr - Ts - Ov", "ISJS": "Sr - Tp - Ov - Ts",
   # "ENJN": "Tp - Tr - Os - Sv", "INJN": "Tr - Tp - Sv - Os",
   # "ENJS": "Tp - Tr - Ss - Ov", "INJS": "Tr - Tp - Ov - Ss",
   _EASTER_EGG_TYPES = [k for (k,v) in _EASTER_EGG_STACKS.items()]
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
            return default_cmd_prefix + self._res.module_cmd_aliases[0] + " typeflair " + left
      elif content.lower().startswith("/xxxx"):
         # TODO: Implement this in a nicer and more efficient way.
         await self._client.send_msg(msg, "For example, to give yourself the ISFJ role, type in `/ISFJ`.")
         return "arbitrary non-command string"
      return await super(JCFDiscord, self).msg_preprocessor(content, msg, default_cmd_prefix)

   @cmd.add(_cmdd, "functions", "fn", "stack", top="functions")
   async def _cmdf_functions(self, substr, msg, privilege_level):
      """
      `{cmd} [mbti type codes]` - Prints the corresponding MBTI cognitive function stack.

      *Easter egg: you can view function definitions by including `src` or `source` as an argument.*
      """
      args = substr.split()
      types = []

      # Easter egg code.
      c_code_easteregg = False
      for buf in args:
         buf2 = buf.lower()
         if buf2 == "source" or buf2 == "src" or buf2 == "c":
            c_code_easteregg = True
            break

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

      # Easter egg code.
      if c_code_easteregg:
         buf = self._easteregg_c_functions_transf(buf, msg)

      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "iamaspecialsnowflake", top=True)
   async def _cmdf_typeflair(self, substr, msg, privilege_level):
      """
      `{cmd}` - Who's a special little snowflake?
      """
      await utils.remove_flairs_by_name(self._client, msg.author, *self._MBTI_TYPES, case_sensitive=False)
      await self._client.send_msg(msg, "Cleared <@{0}>'s' type flair.".format(msg.author.id))
      return

   @cmd.add(_cmdd, "typeflair")
   async def _cmdf_typeflair(self, substr, msg, privilege_level):
      """
      `{cmd} [mbti type code]` - Get the bot to assign you an MBTI type role.
   
      There is also a shortcut to using this command:
      `{p}[mbti type code]`

      **Example:** `{p}ISFJ` assigns you the `ISFJ` role.
      """
      (left, right) = utils.separate_left_word(substr)
      new_role_name = left.upper()
      if not new_role_name in self._MBTI_TYPES_SET:
         raise errors.InvalidCommandArgumentsError
      new_role = utils.flair_name_to_object(self._res.server, new_role_name, case_sensitive=False)
      if new_role is None:
         await self._client.send_msg(msg, "Role '{}'' does not exist. Aborting with no changes.".format(new_role))
         raise errors.OperationAborted
      await utils.remove_flairs_by_name(self._client, msg.author, *self._MBTI_TYPES, case_sensitive=False)
      await asyncio.sleep(1)
      await self._client.add_roles(msg.author, new_role)
      await self._client.send_msg(msg, "Assigned <@{0}> the type flair '{1}'.".format(msg.author.id, new_role_name))
      return

   # Temporarily unavailable.
   # @cmd.add(_cmdd, "subreddit", default=True)
   # async def _cmdf_noot(self, substr, msg, privilege_level):
   #    """`{cmd}` - Get a link to the JCFDiscord community's subreddit."""
   #    await self._client.send_msg(msg, "Our subreddit is at https://www.reddit.com/r/JCFDiscord/.")
   #    return

   @cmd.add(_cmdd, "swole", top=True)
   async def _cmdf_swole(self, substr, msg, privilege_level):
      """`{cmd}`"""
      if msg.author.id == self._SWOLEBRO_ID:
         await self._client.send_msg(msg, "Dude, you so swole <@{}>".format(self._SWOLEBRO_ID))
      elif ("fitness" in msg.channel.name.lower()) or ("swole" in msg.channel.name.lower()):
         await self._client.send_msg(msg, "<#{}> is the best place to get swole with swolebro.".format(msg.channel.id))
      else:
         await self._client.send_msg(msg, "Too bad you're not as swole as swolebro <@{}>.".format(msg.author.id))
      return

   @cmd.add(_cmdd, "noot", top=True)
   async def _cmdf_noot(self, substr, msg, privilege_level):
      """`{cmd}`"""
      # var m = await Client.SendMessage(e.Channel, "Penguins will rule the earth!");
      # await Task.Delay(1000);
      # TODO: Figure out how to do this with asyncio without hanging up the bot for the whole 1 second...
      await self._client.send_msg(msg, "noot noot")
      return

   # Adding this easter egg to the command function would be complicated and
   # probably not worth it to implement this easter egg (in case I want to
   # remove it later), so it's implemented to parse the string and modify it
   # before sending it as a message.
   @classmethod
   def _easteregg_c_functions_transf(cls, buf_original, msg):
      """an easter egg."""
      
      # General format
      """
      ```C
      /*         File: type_behaviour1.c
       *      Authors: simshadows
       * Last Updated: 12/06/2016 13:06
       *      Version: 2.3.291
       * 
       * Defines the behaviour of some MBTI types.
       */

      #include "human.h"
      #include "jcf.h"
      
      #define C_EASTER_EGG true

      Behaviour isfj(SensoryData s) {
         Thoughts t = new_thoughts(s);
         si(t);
         fe(t);
         ti(t);
         ne(t);
         return make_decision(t);
      }
      ```
      """
      # TODO: Over time, implement some additional bits such as custom author name.

      buf_final = textwrap.dedent("""\
         ```C
         /*         File: type_behaviour{rnd1}.c
          *      Authors: {msg.author.name}
          * Last Updated: {d}/{m}/{y} {h}:{min}
          *      Version: {rnd2}.{rnd3}.{rnd4}
          * 
          * Defines the behaviour of some MBTI types.
          */

         #include <stdbool.h>
         #include "human.h"
         #include "jcf.h"
         
         #define C_EASTER_EGG true{c_fn_defs}
         ```
         """)

      buf = buf_original[4:-4]
      lines = buf.splitlines()
      lines = [x.split() for x in lines]
      stacks = [(x[0].lower(), x[2].lower(), x[4].lower(), x[6].lower(), x[8].lower()) for x in lines]

      fn_def_template = "\n\n" + textwrap.dedent("""\
         Behaviour {mbti}(SensoryData s) {{
            Thoughts t = new_thoughts(s);
            {fn1}(t);
            {fn2}(t);
            {fn3}(t);
            {fn4}(t);
            return make_decision(t);
         }}
         """).strip()
      fn_defs = [fn_def_template.format(mbti=x[0], fn1=x[1], fn2=x[2], fn3=x[3], fn4=x[4]) for x in stacks]

      now = datetime.datetime.now()

      new_kwargs = {
         "c_fn_defs": "".join(fn_defs),
         "msg": msg,
         "rnd1": str(random.randint(1,13)),
         "rnd2": str(random.randint(1,13)),
         "rnd3": str(random.randint(1,13)),
         "rnd4": str(random.randint(1,999)).zfill(4),
         "d": str(now.day).zfill(2),
         "m": str(now.month).zfill(2),
         "y": str(now.year).zfill(4),
         "h": str(now.hour).zfill(2),
         "min": str(now.minute).zfill(2),
      }
      return buf_final.format(**new_kwargs)
