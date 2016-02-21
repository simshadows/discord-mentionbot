import sys
import re
import os
import json
import datetime

import discord

_RE_PRIVLVL_LINE = re.compile(">>> PRIVILEGE LEVEL \d+")

#################################################################################
# BASIC STRING OPERATIONS #######################################################
#################################################################################

# E.g. "hi    how   r u" -> ("hi","how   r u")
#      "hi"              -> ("hi","")
def separate_left_word(text): # TYPE: Tuple<String>
   substrings = text.split(maxsplit=1) # "how r u?" -> ["how", "r u?"]
   if len(substrings) == 0:
      return ("","")
   elif len(substrings) == 1:
      substrings.append("")
   return tuple(substrings)

def remove_whitespace(text):
   return "".join(text.split()) # TODO: Find a nicer implementation.

def str_asciionly(text):
   buf = ""
   try:
      buf = str(text.encode("unicode_escape"))
   except:
      buf = ">>>>>>>>>>>>>>>>>>>>>>>>UNKNOWN"
      print("ERROR: Failed to convert string.")
   return buf[2:-1]

#################################################################################
# FILE I/O ######################################################################
#################################################################################

_CWD = os.getcwd()
_ENCODING = "utf-8"

# This overwrites whatever file is specified with the data.
def json_write(relfilepath, data=None):
   _mkdir_recursive(relfilepath)
   with open(relfilepath, encoding=_ENCODING, mode="w") as f:
      f.write(json.dumps(data, sort_keys=True, indent=3))
   return

def json_read(relfilepath):
   with open(relfilepath, encoding=_ENCODING, mode="r") as f:
      return json.loads(f.read())

def _mkdir_recursive(relfilepath):
   absfilepath = os.path.join(_CWD, relfilepath)
   absdir = os.path.dirname(absfilepath)
   try:
      os.makedirs(absdir)
   except FileExistsError:
      pass
   return

#################################################################################
# COMMAND PREPROCESSOR HELPER FUNCTIONS #########################################
#################################################################################

# E.g. add_base_command("/choose A;B;C", "/", "rnd")
#      returns: "/rnd choose A;B;C"
# The function automatically cuts off the original base command at the first
# space.
# E.g. add_base_command("/chooseA;B;C", "/", "rnd")
#      returns: "/rnd" 
# PRECONDITION: The function's inputs are guaranteed to produce a change such as
#               above. Incorrect inputs (such as wrong prefix) are not handled.
#               For example, behaviour when passing in an empty content parameter
#               is not defined.
def add_base_cmd(content, cmd_prefix, new_base_command):
   return cmd_prefix + new_base_command + " " + content[len(cmd_prefix):]

# E.g. change_base_command("/choose A;B;C", "/", "rnd")
#      returns: "/rnd A;B;C"
# Similarly to add_base_cmd(), this function also cuts off the original base
# command at the first space.
# PRECONDITION: same precondition as add_base_command().
def change_base_cmd(content, cmd_prefix, new_base_command):
   (left, right) = separate_left_word(content[len(cmd_prefix):])
   return cmd_prefix + new_base_command + " " + right

# E.g. change_cmd_prefix("/choose A;B;C", old="/", new="$")
#      returns: "$choose A;B;C"
def change_cmd_prefix(content, old="/", new="$"):
   return new + content[len(old):]

#################################################################################
# OTHERS ########################################################################
#################################################################################

# Simple class for use to prevent external instantiation where necessary.
class SecretToken:
   def __init__(self):
      return

_true_strings = ["true","1","t","y", "yes"]
def str_says_true(text):
   return text.lower() in _true_strings

def member_is_offline(member):
   return str(member.status) == str(discord.Status.offline)

def member_is_idle(member):
   return str(member.status) == str(discord.Status.idle)

def member_is_online(member):
   return str(member.status) == str(discord.Status.online)

# A helper method for preparing help strings.
# Parses a list of lines, producing a single string with the lines
# combined, appropriate for the privilege level.
# TODO: Add examples on this method's usage.
def prepare_help_content(raw_lines, cmd_prefix, privilegelevel=0):
   help_content = ""
   line_privlvl = 0
   for line in raw_lines:
      match = _RE_PRIVLVL_LINE.match(line)
      if match:
         line_privlvl = int(match.group(0)[len(">>> PRIVILEGE LEVEL "):])
      elif (privilegelevel >= line_privlvl):
         help_content += line + "\n"
   return help_content[:-1].format(pf=cmd_prefix)

def remove_blank_strings(string_list):
   return list(filter(None, string_list))

def datetime_rounddown_to_day(datetime_object):
   date_object = datetime_object.date()
   return datetime.datetime(year=date_object.year, month=date_object.month, day=date_object.day)

def datetime_rounddown_to_hour(datetime_object):
   hour = datetime_object.hour
   date_object = datetime_object.date()
   return datetime.datetime(
      year=date_object.year,
      month=date_object.month,
      day=date_object.day,
      hour=hour,
   )

_re_mention = re.compile("<@\d+>")
def get_all_mentions(text):
   mentions = []
   for mention_string in _re_mention.findall(text):
      mentions.append(mention_string[2:-1])
   return mentions


# Parses a block of text, returns a list of flags.
# For every non-flag, "invalid" is instead appended.
# E.g. "-l hello --flag" -> ["l","invalid","flag"]
# E.g. "--flag" -> ["flag"]
# E.g. "-flag" -> ["f","l","a","g"]
# E.g. "flag" -> ["invalid"]
# E.g. "" -> []
# PARAMETER: text = String
# RETURNS: List of flags as strings (without the leading hyphens)
def parse_flags(text):
   flags = []
   args = text.split(" ")
   for arg in args:
      if (len(arg) > 1) and (arg[0] == "-"):
         if (len(arg) > 2) and (arg[1] == "-"):
            flags.append(arg[2:])
         else:
            # Append all characters as separate flags.
            for i in arg[1:]:
               flags.append(i)
      elif arg != "":
         flags.append("invalid")
   return flags


# Returns a string that:
#     is the time in seconds if time is <1 minute (e.g. "36 seconds ago"),
#     is the time in minutes if time is <1 hour (e.g. "8 minutes ago"), or
#     is the time in hours (e.g. "12 hours ago").
def seconds_to_string(seconds):
   if seconds >= 0:
      if seconds < 60:
         return str(seconds) + " seconds"
      elif seconds < (60*60):
         return str(round(seconds/60, 2)) + " minutes"
      else:
         return str(round(seconds/(60*60), 2)) + " hours"
   else:
      return str(seconds) + " seconds (uhh... I don't think this should be negative.)"


# Opens, puts file contents in a string, and closes it.
# If file doesn't exist, returns None.
# def quick_fileread(filename):
#    if os.path.isfile(filename):
#       f = open(filename)
#       buf = f.read()
#       f.close()
#       return buf
#    else:
#       return None

