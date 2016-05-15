import asyncio
import datetime

import discord
import dateutil.parser

from .. import utils, errors, cmd
from ..servermodule import ServerModule
from ..enums import PrivilegeLevel

class Voting(ServerModule):

   MODULE_NAME = "Voting"
   MODULE_SHORT_DESCRIPTION = "Facilities for simple votes/polls."
   RECOMMENDED_CMD_NAMES = ["voting"]
   
   _SECRET_TOKEN = utils.SecretToken()
   _cmd_dict = {}

   _HELP_SUMMARY = """
See `{modhelp}` for voting commands.
   """.strip()

   DEFAULT_SETTINGS = {
      "enabled channels": []
   }

   async def _initialize(self, resources):
      self._client = resources.client
      self._res = resources

      self._vote_instances = {} # FORMAT: {vote ID: voting objects}
      self._load_settings()
      return

   def _load_settings(self):
      # Every file that is not settings.json is a vote json file.
      data_dir = self._res.data_directory
      for file_name in os.listdir(ch_dir):
         if (file_name == "settings.json") or (not file_name.endswith(".json")):
            continue
         # File names are also the vote IDs
         vote_instance = VoteInstance(json_data=utils.json_read(data_dir + file_name))
         self._vote_instances[file_name[:-5]] = vote_instance
      return

   def _save_settings(self):
      for (vote_ID, vote_obj) in self._vote_instances.items():
         utils.jsonwrite(data_dir + vote_ID + ".json", data=vote_obj)
      return

   async def process_cmd(self, substr, msg, privilege_level):
      if substr == "": # Default Case
         substr = "newgame"
      return await super(Voting, self).process_cmd(substr, msg, privilege_level)

   @cmd.add(_cmd_dict, "rules")
   async def _cmdf_enable(self, substr, msg, privilege_level):
      """`{cmd}` - View game rules."""
      await self._client.send_msg(channel, self._RULES_STRING)
      return

   ########################
   ### GENERAL SERVICES ###
   ########################
   



class VoteInstance:
   def __init__(self, **kwargs):
      """
      Manages voting data.

      To keep things simple, this class will wrap json data object.

      It is initialized either with an existing json data object (json_data), or
      all other arguments.

      """
      # Set up defaults.
      self._start_date = None
      self._continuation_date = None
      self._json_data = None
      if "json_data" in kwargs:
         json_data = kwargs["json_data"]
         self._start_date = dateutil.parser.parse(json_data["start"])
         if not json_data["continuation"] is None:
            self._continuation_date = dateutil.parser.parse(json_data["continuation"])
         self._json_data = json_data
      else:
         # Fill in default values for other arguments.
         if not "title" in kwargs:
            kwargs["title"] = "Untitled"
         if not "description" in kwargs:
            kwargs["description"] = "No description."
         if not "period_seconds" in kwargs:
            kwargs["period_seconds"] = 1
         if not "period_days" in kwargs:
            kwargs["period_days"] = 1

         self._start_date = datetime.datetime.utcnow()
         self._continuation_date = None
         self._json_data = {
            "title": kwargs["title"],
            "description": kwargs["description"],
            "start": self._start_date.isoformat(),
            "continuation": None,
            "period seconds": kwargs["period_seconds"],
            "period days": kwargs["period_days"],
            "votes": {},
            # Structure of each vote:
            #     member id string: {
            #        "option id": string, # This matches the id under "options".
            #     }
            "options": {},
            # Structure of each option:
            #     option id string: {
            #        "name": string,
            #     }
            "history": [], # Human-readable strings documenting important changes.
            # These strings are not machine-read.
            # This is useful for when there's a dispute (though it doesn't protect
            # against malicious editing of the data files themselves).
         }
      return

   # The returned object must *NOT* be edited.
   def get_json_serializable(self):
      return self._json_data

   ######################################
   ### GETTERS AND STATUS INFORMATION ###
   ######################################

   @property
   def title(self):
      return self._json_data["title"]

   @property
   def description(self):
      return self._json_data["description"]

   @property
   def period_seconds(self):
      return self._json_data["period seconds"]

   @property
   def period_days(self):
      return self._json_data["period days"]

   def is_ended(self):
      return self.get_period_elapsed() >= datetime.timedelta(days=self.period_days, seconds=self.period_seconds)

   # RETURNS: timedelta object of the time elapsed.
   def get_period_elapsed(self):
      now_date = datetime.datetime.utcnow()
      start_or_cont_date = self._continuation_date
      if start_or_cont_date is None:
         start_or_cont_date = self._start_date
      return now_date - start_or_cont_date

   # RETURNS: datetime object representing end date.
   def get_end_date(self):
      start_or_cont_date = self._continuation_date
      if start_or_cont_date is None:
         start_or_cont_date = self._start_date
      return start_or_cont_date + datetime.timedelta(days=self.period_days, seconds=self.period_seconds)

   # RETURNS: The options dict representing all options.
   def get_options_dict(self):
      return self._json_data["options"]

   # RETURNS: The options dict representing all options.
   def get_votes_dict(self):
      return self._json_data["votes"]

   # RETURNS: The options dict representing all options.
   def get_history_list(self):
      return self._json_data["history"]

   def is_valid_option_id(self, option_id):
      return option_id in self._json_data["options"]

   ###############
   ### SETTERS ###
   ###############

   def set_title(self, new_title, *, executing_member=None):
      buf = "Set title to '{}'.".format(new_title)
      self._add_history(buf, executing_member=executing_member)
      self._json_data["title"] = new_title
      return

   def set_description(self, new_desc, *, executing_member=None):
      buf = "Set description to '{}'.".format(new_desc)
      self._add_history(buf, executing_member=executing_member)
      self._json_data["description"] = new_desc
      return

   #####################
   ### OTHER METHODS ###
   #####################

   # PRECONDITION: option_name is not an empty string.
   def add_option(self, option_name, *, executing_member=None):
      options_dict = self._json_data["options"]
      new_option_id = -1
      for (option_id, option_dict) in options_dict.items():
         option_id = int(option_id)
         if new_option_id < option_id:
            new_option_id = option_id
      new_option_id = str(new_option_id + 1)

      options_dict[new_option_id] = {"name": option_name}

      # Add into history.
      buf = "Added option '{}' (ID: {}).".format(option_name, new_option_id)
      self._add_history(buf, executing_member=executing_member)
      return

   # Executing member should be the voter themselves.
   # PRECONDITION: The option exists.
   def add_vote(self, option_id, voter_id, *, executing_member=None):
      buf = "User ID {} voted option {}.".format(voter_id, option_id)
      self._add_history(buf, executing_member=executing_member)
      self._json_data["votes"][voter_id] = {"option id": option_id}
      return

   def end_vote(self, *, executing_member=None):
      self._add_history("Ended the vote.", executing_member=executing_member)
      new_period = self.get_period_elapsed()
      self.period_days = new_period.days
      self.period_seconds = new_period.seconds
      return

   # Note: If a vote is still running, you'd probably want to extend it instead.
   #       The continuation facilities are intended to allow continuation of a
   #       vote that has ended.
   # PRECONDITION: days<0, seconds<0, and they can't both be zero.
   def continue_vote(self, *, days=0, seconds=0, executing_member=None):
      buf = "Continued the vote. days={}, sec={}".format(str(days), str(seconds))
      self._add_history(buf, executing_member=executing_member)
      self._continuation_date = datetime.datetime.utcnow()
      self._json_data["continuation"] = self._continuation_date.isoformat()
      self._json_data["period seconds"] = seconds
      self._json_data["period days"] = days
      return

   # PRECONDITION: Vote hasn't ended.
   # PRECONDITION: days<0, seconds<0, and they can't both be zero.
   def extend_vote_from_now(self, *, days=0, seconds=0, executing_member=None):
      buf = "Extended vote from now. days={}, sec={}".format(str(days), str(seconds))
      self._add_history(buf, executing_member=executing_member)
      new_period = self.get_period_elapsed() + datetime.timedelta(days=days, seconds=seconds)
      self.period_days = new_period.days
      self.period_seconds = new_period.seconds
      return

   # PRECONDITION: Vote hasn't ended.
   # PRECONDITION: days<0, seconds<0, and they can't both be zero.
   def extend_vote_from_start(self, *, days=0, seconds=0, executing_member=None):
      buf = "Extended vote from start. days={}, sec={}".format(str(days), str(seconds))
      self._add_history(buf, executing_member=executing_member)
      self.period_days = self.period_days + days
      self.period_seconds = self.period_seconds + seconds
      return

   ########################
   ### PRIVATE SERVICES ###
   ########################

   def _add_history(self, text, *, executing_member=None):
      date_str = datetime.datetime.utcnow().isoformat()
      buf = "({} id={} name={}): ".format(date_str, executing_member.id, executing_member.name) + text
      self._json_data["history"].append(buf)
      return



