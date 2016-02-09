import asyncio
import random
import re

import discord

import utils
import errors
from servermodule import ServerModule

class Random(ServerModule):

   RECOMMENDED_CMD_NAMES = ["random", "rng", "rnd", "rand"]

   MODULE_NAME = "Random"
   MODULE_SHORT_DESCRIPTION = "A suite of commands for generating random values."

   _HELP_SUMMARY_LINES = """
`{pf}random` - Get random int. (Additional help exists.)
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
**Sorry, I haven't written help info for this module yet. Check back later!**
   """.strip().splitlines()

   _RE_INT = re.compile("[-\+]?\d+")

   # PARAMETER: enabled - If false, the module is disabled.
   def __init__(self, cmd_names, client):
      self._client = client
      self._cmd_names = cmd_names
      return

   @classmethod
   def get_instance(cls, cmd_names, client):
      return Random(cmd_names, client)

   @property
   def cmd_names(self):
      return self._cmd_names

   def get_help_summary(self, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_SUMMARY_LINES, cmd_prefix, privilegelevel)

   def get_help_detail(self, substr, cmd_prefix, privilegelevel=0):
      return utils.prepare_help_content(self._HELP_DETAIL_LINES, cmd_prefix, privilegelevel)

   # Call this every time a message is received.
   async def on_message(self, msg):
      pass

   # Call this to process a command.
   async def process_cmd(self, substr, msg, privilegelevel=0):
      
      # Process command shortcuts
      if substr == "": # Default Case
         substr = "number"
      
      # Process the command itself
      (left, right) = utils.separate_left_word(substr)
      if (left == "number") or (left == "num") or (left == "int") or (left == "integer"):
         await self.cmd_number(right, msg)

      elif (left == "colour") or (left == "color") or (left == "rgb"):
         rand_int = random.randint(0,(16**6)-1)
         rand = hex(rand_int)[2:] # Convert to hex
         rand = rand.zfill(6)
         buf = "{}, your random colour is {} (decimal: {})".format(msg.author.name, rand, rand_int)
         buf += "\nhttp://www.colorhexa.com/{}.png".format(rand)
         await self._client.send_msg(msg, buf)

      else:
         raise errors.InvalidCommandArgumentsError

      return

   async def cmd_number(self, substr, msg):
      # Compile a set of ranges to randomize.
      args = utils.remove_whitespace(substr)
      rng_ranges = []
      rng_sets = args.split(",")

      # Populate rng_ranges
      if (len(rng_sets) == 1) and (rng_sets[0] == ""):
         rng_ranges.append((1, 10))
      elif (len(rng_sets) == 1) and self._RE_INT.fullmatch(rng_sets[0]):
         val = int(rng_sets[0])
         if val > 1:
            rng_ranges.append((1, val))
         elif val < -1:
            rng_ranges.append((val, -1))
         elif val == 1:
            rng_ranges.append((0, 1))
         elif val == -1:
            rng_ranges.append((-1, 0))
         else:
            rng_ranges.append((0, 0))
      else:
         for rng_set in rng_sets:
            rng_set = rng_set.split("to")
            # Convert all resulting strings to digits
            temp = []
            for value in rng_set:
               if self._RE_INT.fullmatch(value):
                  temp.append(int(value))
               else:
                  raise errors.InvalidCommandArgumentsError
            rng_set = temp
            # Calculate the resulting ranges.
            prev = None
            for curr in rng_set:
               if prev != None:
                  if curr > prev:
                     rng_ranges.append((prev, curr))
                  else:
                     rng_ranges.append((curr, prev))
               prev = curr

      # Populate outgoing buffer.
      buf = ""
      for rng_range in rng_ranges:
         rand = random.randint(rng_range[0], rng_range[1])
         buf += "{0} (Range: {1} to {2})".format(rand, rng_range[0], rng_range[1])

      return await self._client.send_msg(msg, buf)


