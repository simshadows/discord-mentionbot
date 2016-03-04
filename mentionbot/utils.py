import sys
import re
import os
import json
import datetime
import asyncio
import traceback

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

def separate_right_word(text): # TYPE: Tuple<String>
   substrings = text.rsplit(maxsplit=1) # "how r u?" -> ["how r", "u?"]
   if len(substrings) == 0:
      return ("","")
   elif len(substrings) == 1:
      substrings.insert(0, "")
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

###############################################################################
# COMMON SERVER MANAGEMENT OPERATIONS #########################################
###############################################################################

async def close_channel(client, channel, bot_flair_names):
   print("A CHANNEL CLOSED.")
   everyone = channel.server.default_role
   allow = discord.Permissions.none()
   deny = discord.Permissions.all()
   try:
      await ensure_bot_permissions(client, channel, bot_flair_names)
      await client.edit_channel_permissions(channel, everyone, allow=allow, deny=deny)
   except discord.errors.Forbidden as e:
      raise e
   except:
      print(traceback.format_exc())
      print("CHANNEL FAILED TO CLOSE.")
      await client.send_msg(channel, "This channel failed to close.")
   return

async def open_channel(client, channel, server, bot_flair_names):
   print("A CHANNEL OPENED.")
   try:
      await ensure_bot_permissions(client, channel, bot_flair_names)
      await client.delete_channel_permissions(channel, server)
   except discord.errors.Forbidden as e:
      raise e
   except:
      print(traceback.format_exc())
      print("CHANNEL FAILED TO OPEN.")
      await client.send_msg(channel, "This channel failed to open.")
   return

async def ensure_bot_permissions(client, channel, bot_flair_names):
   targets = flair_names_to_object(channel.server, bot_flair_names)
   if len(targets) == 0:
      targets = [channel.server.me]
   allow = discord.Permissions.all()
   deny = discord.Permissions.none()
   for target in targets:
      await client.edit_channel_permissions(channel, target, allow=allow, deny=deny)
   return

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

_re_non_alnum_or_dash = re.compile("[^-0-9a-zA-Z]")
def convert_to_legal_channel_name(text):
   text.replace(" ", "-")
   if len(text) != 0 and text[:1] == "-":
      text = text[1:]
   return _re_non_alnum_or_dash.sub("", text)

def member_is_offline(member):
   return str(member.status) == str(discord.Status.offline)

def member_is_idle(member):
   return str(member.status) == str(discord.Status.idle)

def member_is_online(member):
   return str(member.status) == str(discord.Status.online)

def remove_blank_strings(string_list):
   return list(filter(None, string_list))

def flair_names_to_object(server, flair_names):
   flair_objects = []
   for flair_object in server.roles:
      if flair_object.name in flair_names:
         flair_objects.append(flair_object)
         continue
   return flair_objects

# A non-list version of the function...
def flair_name_to_object(server, flair_name):
   for flair_object in server.roles:
      if flair_object.name == flair_name:
         return flair_object
   return None

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

def timedelta_to_string(td, include_us=False):
   (hours, remainder) = divmod(td.seconds, 3600)
   (minutes, seconds) = divmod(remainder, 60)
   buf = ""
   keep_showing = False
   if td.days != 0:
      buf += str(td.days) + "d "
      keep_showing = True
   if keep_showing or (hours != 0):
      buf += str(hours) + "h "
      keep_showing = True
   if keep_showing or (minutes != 0):
      buf += str(minutes) + "m "
      keep_showing = True
   if keep_showing or (seconds != 0):
      buf += str(seconds) + "s "
      keep_showing = True
   if (include_us and keep_showing) or (len(buf) == 0):
      buf += str(td.microseconds) + "μs "
   return buf[:-1]


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

