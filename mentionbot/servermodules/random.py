import asyncio
import random
import re

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered

@registered
class Random(ServerModule):

   MODULE_NAME = "Random"
   MODULE_SHORT_DESCRIPTION = "Random value generation tools."
   RECOMMENDED_CMD_NAMES = ["random", "rng", "rnd", "rand"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {}

   _HELP_SUMMARY = """
      `{modhelp}` - Generate pseudo-random values.
      """

   # TODO: Add this to help detail in the future...
   # **Examples**
   # *All ranges are inclusive unless otherwise noted.*
   # `{pf}random` - Generates random number from 1 to 10.
   # `{pf}random number -1 to -5, 6to10` - Generates two random numbers.
   # `{pf}random choose A;B;C` - Randomly picks an option (delimited by `;`).
   # `{pf}random coin` - Flips a coin.
   # `{pf}random colour` - Generates a random RGB colour code.
   # `{pf}random dice 3d9` - Rolls 9-sided dice (faces 1 to 9) 3 times.

   _re_kw_choose = re.compile("choose|ch|choice|choices")
   _re_dice_notation = re.compile("(\d*d)?\d+")

   async def _initialize(self, resources):
      self._res = resources
      self._client = resources.client

      self._res.suppress_autokill(True)
      return

   async def process_cmd(self, substr, msg, privilege_level):
      if utils.re_int.match(substr):
         substr = "number " + substr
      elif (not self._re_kw_choose.match(substr)) and (";" in substr):
         substr = "choose " + substr
      return await super(Random, self).process_cmd(substr, msg, privilege_level)

   @cmd.add(_cmdd, "number", "num", "int", "integer", default=True)
   async def _cmdf_number(self, substr, msg, privilege_level):
      """
      `{cmd} [args]` - Generates a random integer.

      **Examples of usage:**

      *Note: All ranges listed here are inclusive.*

      `{cmd}`
      Random number from 1 to 10.

      `{cmd} 2000`
      Random number from 1 to 2000.

      `{cmd} -50 to 100`
      Random number from -50 to 100.

      `{cmd} 1 to 5 to 10 to 15`
      Generates three random numbers of the ranges 1-5, 5-10, and 10-15.
      """
      # Compile a set of ranges to randomize.
      
      args = utils.remove_whitespace(substr)
      rng_ranges = []
      rng_sets = args.split(",")

      # Populate rng_ranges
      if (len(rng_sets) == 1) and (rng_sets[0] == ""):
         rng_ranges.append((1, 10))
      elif (len(rng_sets) == 1) and utils.re_int.fullmatch(rng_sets[0]):
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
               if utils.re_int.fullmatch(value):
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

   @cmd.add(_cmdd, "choose", "choice", "choices", top=True)
   async def _cmdf_choose(self, substr, msg, privilege_level):
      """
      `{cmd} [option1]; [option2]; [...]` - Randomly choose from multiple options.

      **EXAMPLE:**

      `{cmd} Red; Green; Blue`
      Randomly choose between those three colours.
      """
      choices = substr.split(";")
      choices = list(filter(None, choices)) # Remove empty strings
      if len(choices) == 0:
         raise errors.InvalidCommandArgumentsError
      buf = "\a" + random.choice(choices).strip() + "\n"
      buf += "**My choices were**: "
      for choice in choices:
         buf += choice.strip() + "; "
      buf = buf[:-2]
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "coin", "flip", top=True)
   async def _cmdf_coin(self, substr, msg, privilege_level):
      """
      `{cmd}` - 50/50 Heads or tails.

      Or... at least in theory. Some say there's a 1/6000 possibility of seeing the coin land on its side, though I've personally never seen it happen.
      """
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

   @cmd.add(_cmdd, "dice", "roll", top=True)
   async def _cmdf_cmdnotimplemented(self, substr, msg, privilege_level):
      """
      `{cmd} [args]` - Roll some dice.

      **Dice notation:**

      Dice rolls are represented with a code of the form:
      "3d6"
      This code means you roll 6-sided dice three times and sum up the result.
      Furthermore, these dice have sides of values 1,2,3,4,... . E.g. a 6-sided dice has sides 1,2,3,4,5,6.
      
      **Examples of usage:**

      `{cmd}`
      Rolls a 1d6 (a single 6-sided die).

      `{cmd} 12`
      Rolls a 1d12 (a single 12-sided die).

      `{cmd} d4`
      Rolls a 1d4 (a single 4-sided die).

      `{cmd} 2d8`
      Rolls a 2d8 (two 8-sided dice).

      `{cmd} 1000d498`
      Rolls a 1000d498 (1000 498-sided dice).
      """
      if substr == "":
         throws = 1
         sides = 6
      elif self._re_dice_notation.fullmatch(substr):
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

   @cmd.add(_cmdd, "user", "member", "u", "mem")
   async def _cmdf_colour(self, substr, msg, privilege_level):
      """
      `{cmd}` - Chooses a random member from this server.

      This command does not mention users.
      """
      random_member = random.choice(list(msg.server.members))
      buf = "**Your random user is:** {0} (UID: {1})\n".format(random_member.name, random_member.id)
      buf += "(Chosen out of {} users.)".format(str(len(msg.server.members))) # TODO: Fix concurrent access?
      await self._client.send_msg(msg, buf)
      return


   