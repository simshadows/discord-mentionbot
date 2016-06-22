import asyncio
import random
import re
import textwrap
import collections

import discord

from .. import utils, errors, cmd
from ..servermodule import ServerModule, registered
from ..enums import PrivilegeLevel

@registered
class TruthGame(ServerModule):

   MODULE_NAME = "Truth Game"
   MODULE_SHORT_DESCRIPTION = "Tools to play *Truth*."
   RECOMMENDED_CMD_NAMES = ["truth", "troof", "trufe"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmdd = {}

   _HELP_SUMMARY = """
      `{modhelp}` - Truth game.
      """

   DEFAULT_SETTINGS = {
      "enabled channels": []
   }

   _PARTICIPANT_DELIMITER = " --> "

   _RULES_STRING = textwrap.dedent("""\
   **Rules for a game of _Truth_**:
   idk, ask the people playing it.
   """)

   async def _initialize(self, resources):
      self._client = resources.client
      self._res = resources

      self._enabled_channels = None
      self._load_settings()

      self._randomized_picks = collections.defaultdict(dict)
      # _randomized_picks[channel_id][player_string] = picks (an integer)

      self._res.suppress_autokill(True)
      return

   def _load_settings(self):
      settings = self._res.get_settings(default=self.DEFAULT_SETTINGS)

      self._enabled_channels = []
      try:
         self._enabled_channels = settings["enabled channels"]
         if self._enabled_channels is None:
            print("DEBUGGING: truthgame.py TruthGame._load_settings() enabled channels is None!")
            self._enabled_channels = []
      except KeyError:
         self._enabled_channels = settings["enabled channels"] = []
         self._res.save_settings(settings)

      return

   def _save_settings(self):
      settings = self._res.get_settings()
      settings["enabled channels"] = self._enabled_channels
      self._res.save_settings(settings)
      return

   @cmd.add(_cmdd, "rules")
   async def _cmdf_enable(self, substr, msg, privilege_level):
      """`{cmd}` - View game rules."""
      await self._client.send_msg(msg, self._RULES_STRING)
      return

   @cmd.add(_cmdd, "newgame", top=True)
   @cmd.minimum_privilege(PrivilegeLevel.TRUSTED)
   async def _cmdf_newgame(self, substr, msg, privilege_level):
      """`{cmd}` - New game."""
      channel = msg.channel
      await self._abort_if_not_truth_channel(channel)
      await self._new_game(channel)
      await self._client.send_msg(channel, "Truth game cleared.")
      return

   @cmd.add(_cmdd, "in", top=True)
   async def _cmdf_in(self, substr, msg, privilege_level):
      """
      `{cmd}` - Adds you to the game.

      This command also allows moderators to add other users and arbitrary strings as participants.
      **Example:** `{cmd} an elephant` - Adds "an elephant" as a participant.
      """
      channel = msg.channel
      await self._abort_if_not_truth_channel(channel)
      new_participant = None
      if (privilege_level < PrivilegeLevel.MODERATOR) or (len(substr) == 0):
         new_participant = "<@" + msg.author.id + ">"
      else:
         new_participant = substr
         if self._PARTICIPANT_DELIMITER in new_participant:
            await self._client.send_msg(channel, "Error: Not allowed to use the delimiter characters.")
            raise errors.OperationAborted
      if new_participant in self._get_participants(channel):
         await self._client.send_msg(channel, "Error: {} is already a participant.".format(new_participant))
      else:
         await self._add_participant(channel, new_participant)
         await self._client.send_msg(channel, "Added {} to the game.".format(new_participant))
      return

   @cmd.add(_cmdd, "out", top=True)
   async def _cmdf_out(self, substr, msg, privilege_level):
      """
      `{cmd}` - Removes you from the game.

      This command also allows moderators to remove other users and arbitrary strings.
      **Example:** `{cmd} an elephant` - Removes "an elephant" as a participant.
      """
      channel = msg.channel
      await self._abort_if_not_truth_channel(channel)
      participant = None
      if (privilege_level < PrivilegeLevel.MODERATOR) or (len(substr) == 0):
         participant = "<@" + msg.author.id + ">"
      else:
         participant = substr
      if participant in self._get_participants(channel):
         await self._remove_participant(channel, participant)
         await self._client.send_msg(channel, "Removed {} from the game.".format(participant))
      else:
         await self._client.send_msg(channel, "Error: {} is not already a participant.".format(participant))
      return

   @cmd.add(_cmdd, "enablechannel")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_enable(self, substr, msg, privilege_level):
      """`{cmd}` - Enable Truth in this channel."""
      channel = msg.channel
      if channel.id in self._enabled_channels:
         await self._client.send_msg(channel, "This channel is already a Truth game channel.")
      else:
         self._enabled_channels.append(channel.id)
         self._save_settings()
         await self._client.send_msg(channel, "This channel is now a Truth game channel.")
      return

   @cmd.add(_cmdd, "disablechannel")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_disable(self, substr, msg, privilege_level):
      """`{cmd}` - Disable Truth in this channel."""
      channel = msg.channel
      if channel.id in self._enabled_channels:
         self._enabled_channels.remove(channel.id)
         self._save_settings()
         await self._client.send_msg(channel, "This channel is no longer a Truth game channel.")
      else:
         await self._client.send_msg(channel, "This channel is not a Truth game channel.")
      return

   @cmd.add(_cmdd, "viewenabled")
   async def _cmdf_viewenabled(self, substr, msg, privilege_level):
      """`{cmd}` - View all channels that are enabled as Truth channels."""
      buf = None
      if len(self._enabled_channels) == 0:
         buf = "No channels have Truth game enabled."
      else:
         buf = "**Truth game enabled channels:**"
         for channel_id in self._enabled_channels:
            buf += "\n<#{0}> (ID: {0})".format(channel_id)
      await self._client.send_msg(msg, buf)
      return

   # TODO: Edit this to use the topic string abstraction methods.
   #       Currently, it only consideres user mentions to be participants!
   @cmd.add(_cmdd, "choose", "random", "rand")
   async def _cmdf_choosetruth(self, substr, msg, privilege_level):
      """`{cmd}` - Pick a random participant other than yourself."""
      topic = msg.channel.topic
      if topic is None:
         await self._client.send_msg(msg, "There doesn't appear to be a truth game in here.")
         raise errors.OperationAborted
      
      mentions = utils.get_all_mentions(topic)
      if len(mentions) == 0:
         await self._client.send_msg(msg, "There doesn't appear to be a truth game in here.")
         raise errors.OperationAborted
      
      (choice, choices) = self._pseudorandom_pick(msg.channel.id, mentions, msg.author.id)
      buf = "<@{}>\n".format(choice)
      buf += "My choices were: "
      for mention in mentions:
         user = self._client.search_for_user(mention, enablenamesearch=False, serverrestriction=self._res.server)
         if user is None:
            buf += "<@{}>, ".format(mention)
         else:
            buf += "{}, ".format(user.name)
      buf = buf[:-2]
      await self._client.send_msg(msg, buf)
      return

   @cmd.add(_cmdd, "resetprstate")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_viewenabled(self, substr, msg, privilege_level):
      """`{cmd}` - Reset the state of the pseudorandomizer."""
      self._randomized_picks[msg.channel.id] = {}
      await self._client.send_msg(msg, "This game's pseudorandomizer state has been reset.")
      return

   @cmd.add(_cmdd, "viewprstate")
   @cmd.minimum_privilege(PrivilegeLevel.ADMIN)
   async def _cmdf_viewenabled(self, substr, msg, privilege_level):
      """`{cmd}` - View the state of the pseudorandomizer."""
      channel_id = msg.channel.id
      pick_counts = self._randomized_picks[channel_id]
      buf = textwrap.dedent("""\
         **How the pseudorandomizer works:**
         A counter for each player in the channel's game is kept.
         Every time the randomizer picks a player, it 
         """).strip()
      return

   ################################
   ### TOPIC STRING ABSTRACTION ###
   ################################

   def _get_participants(self, channel):
      topic = channel.topic
      if topic is None:
         return []
      return topic.split(self._PARTICIPANT_DELIMITER)
   
   # PRECONDITION: participant_str contains printable characters.
   # PRECONDITION: participant_str does not contain the delimiter.
   async def _add_participant(self, channel, participant_str):
      topic = channel.topic
      new_topic = None
      if topic == "":
         new_topic = participant_str
      else:
         new_topic = topic + self._PARTICIPANT_DELIMITER + participant_str
      await self._client.edit_channel(channel, topic=new_topic)
      return

   # PRECONDITION: participant_str in self._get_participants(channel)
   async def _remove_participant(self, channel, participant_str):
      participants_list = self._get_participants(channel)
      participants_list.remove(participant_str)
      new_topic = self._PARTICIPANT_DELIMITER.join(participants_list)
      await self._client.edit_channel(channel, topic=new_topic)
      return

   async def _new_game(self, channel):
      await self._client.edit_channel(channel, topic="")
      return

   ########################
   ### GENERAL SERVICES ###
   ########################

   async def _abort_if_not_truth_channel(self, channel):
      if not channel.id in self._enabled_channels:
         await self._client.send_msg(channel, "Error: Truth isn't enabled on this channel.")
         raise errors.OperationAborted
      return

   def _pseudorandom_pick(self, channel_id, choices, chooser):
      assert isinstance(channel_id, str) and isinstance(choices, list)
      pick_counts = self._randomized_picks[channel_id]
      choices_set = set(choices)
      choice = None

      # TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO 
      # TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO 
      # TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO 
      # TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO 
      # TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO 
      # TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO TODO 

      # Anyone who has 2 picks cannot be picked again.
      # When everyone has 2 picks, everyone will reset back to 0.

      # Reset the picks count if the set of choices has changed.
      if (len(pick_counts) != len(choices))
            or (not all((k in choices_set) for (k, v) in pick_counts.items())):
         pick_counts = {x: 0 for x in pick_counts}
         print("TRUTHGAME: Picks reset!")

      choices = [] # Fresh new list.
      for (player, picks) in pick_counts.items():
         if (picks < 2) and (not player == chooser):
            choices.append(player)
      if len(choices) == 0:
         choice = chooser
      else:
         choice = random.choice(choices)
      assert pick_counts[choice] < 2
      pick_counts[choice] += 1
      self._randomized_picks[channel_id] = pick_counts
      return (choice, list(choices_set))

   