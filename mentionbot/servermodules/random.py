import asyncio
import random
import re

import discord

import utils
import errors
from servermodule import ServerModule
import cmd

class Random(ServerModule):
   
   _SECRET_TOKEN = utils.SecretToken()

   RECOMMENDED_CMD_NAMES = ["random", "rng", "rnd", "rand"]

   MODULE_NAME = "Random"
   MODULE_SHORT_DESCRIPTION = "Random value generation tools."

   _HELP_SUMMARY_LINES = """
`{pf}random [integer]` - Get random int. (See `{pf}help random` for more!)
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
**Examples**
*All ranges are inclusive unless otherwise noted.*
`{pf}random` - Generates random number from 1 to 10.
`{pf}random number -1 to -5, 6to10` - Generates two random numbers.
`{pf}random choose A;B;C` - Randomly picks an option (delimited by `;`).
`{pf}random coin` - Flips a coin.
`{pf}random colour` - Generates a random RGB colour code.
`{pf}random dice 3d9` - Rolls 9-sided dice (faces 1 to 9) 3 times.
   """.strip().splitlines()

   _RE_DIGITS = re.compile("\d+")
   _RE_INT = re.compile("[-\+]?\d+")
   _RE_KW_CHOOSE = re.compile("choose|ch|choice|choices")
   _RE_DICE_NOTATION = re.compile("(\d*d)?\d+")

   _cmd_dict = {} # Command Dictionary

   async def _initialize(self, resources):
      self._client = resources.client
      return

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      str_choose = default_cmd_prefix + "choose "
      if content.startswith(str_choose):
         content = utils.add_base_cmd(content, default_cmd_prefix, self._cmd_names[0])
      return content

   async def process_cmd(self, substr, msg, privilege_level):
      if substr == "": # Default Case
         substr = "number"
      elif self._RE_INT.match(substr):
         substr = "number " + substr
      elif (not self._RE_KW_CHOOSE.match(substr)) and (";" in substr):
         substr = "choose " + substr
      (left, right) = utils.separate_left_word(substr)
      cmd_to_execute = cmd.get(self._cmd_dict, left, privilege_level)
      await cmd_to_execute(self, right, msg, privilege_level)
      return

   @cmd.add(_cmd_dict, "number", "num", "int", "integer")
   async def _cmdf_number(self, substr, msg, privilege_level):
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
         buf += "{0} (Range: {1} to {2}, inclusive)\n".format(rand, rng_range[0], rng_range[1])
      buf = buf[:-1] # Trim off last newline.
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "choose", "ch", "choice", "choices")
   async def _cmdf_choose(self, substr, msg, privilege_level):
      choices = substr.split(";")
      choices = list(filter(None, choices)) # Remove empty strings
      if len(choices) == 0:
         raise errors.InvalidCommandArgumentsError
      buf = random.choice(choices) + "\n"
      buf += "My choices were: "
      for choice in choices:
         buf += choice + ";"
      buf = buf[:-1]
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "coin", "flip")
   async def _cmdf_coin(self, substr, msg, privilege_level):
      if random.randint(0,1) == 1:
         buf = "Heads"
      else:
         buf = "Tails"
      if random.randint(1,600) == 1:
         buf = "The coin landed on its side."
         buf += "\nThis happens every approx. 1/6000 times!"
         buf += "\nhttp://journals.aps.org/pre/abstract/10.1103/PhysRevE.48.2547"
         buf += "\n(Disclaimer: Actually, this RNG does it every 600th flip"
         buf += " to give this event a slight probability boost.)"
      elif random.randint(1,80) == 1:
         buf = "You accidentally tear a hole in the fabric of spacetime. Good job. Idiot."
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "colour", "color", "rgb")
   async def _cmdf_colour(self, substr, msg, privilege_level):
      rand_int = random.randint(0,(16**6)-1)
      rand = hex(rand_int)[2:] # Convert to hex
      rand = rand.zfill(6)
      buf = "{}, your random colour is {} (decimal: {})".format(msg.author.name, rand, rand_int)
      buf += "\nhttp://www.colorhexa.com/{}.png".format(rand)
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmd_dict, "dice", "roll")
   async def _cmdf_cmdnotimplemented(self, substr, msg, privilege_level):
      if substr == "":
         throws = 1
         sides = 6
      elif self._RE_DICE_NOTATION.fullmatch(substr):
         spl = utils.remove_blank_strings(substr.split("d"))
         if len(spl) == 1:
            throws = 1
            sides = int(spl[0])
         else:
            throws = int(spl[0])
            sides = int(spl[1])
      else:
         raise errors.InvalidCommandArgumentsError
      # Verify values
      if (throws < 1) or (sides < 1) or (throws > 1000):
         raise errors.InvalidCommandArgumentsError
      # Calculate output
      total = 0
      buf3 = ""
      for i in range(0,throws):
         trial = random.randint(1,sides)
         total += trial
         buf3 += str(trial) + ", "
      buf1 = str(total)
      buf2 = "\n\n**Interpretation:** {0}d{1}".format(throws, sides)
      buf2 += "\n**Individual dice rolls:** "
      buf3 = buf3[:-2]
      if throws == 1:
         buf = buf1 + " ({0}d{1})".format(throws, sides)
      elif len(buf1) + len(buf2) + len(buf3) > 1998:
         buf = buf1 + buf2 + "*(Too many dicerolls to display. Sorry!)*"
      else:
         buf = buf1 + buf2 + buf3
      await self._client.send_msg(msg, buf)
      return


   