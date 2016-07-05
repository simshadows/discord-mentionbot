import sys
import re
import os
import json
import datetime
import asyncio
import traceback
import urllib.request
import http.client
import random

import discord

re_user_mention = re.compile("<@!?\d+>")
re_ch_mention = re.compile("<#\d+>")

re_digits = re.compile("\d+")
re_int = re.compile("[-\+]?\d+")

# These two regexes must both be used to verify a folder name.
re_dirname_fullmatch = re.compile("[a-z0-9_-]+") # This must be full-matched.
re_dirname_once = re.compile("[a-z0-9]") # There must be at least one match.

#################################################################################
# SECRET TOKEN ##################################################################
#################################################################################

# Simple class for use to prevent external instantiation where necessary.
class SecretToken:
   def __init__(self):
      return

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
      return buf
   return buf[2:-1]

# # PARAMETER: original_str: The string to be operated on.
# # PARAMETER: *args: Strings to find within original_str, and replacements.
# #                   Must have an even number of *args (except 0, and not
# #                   counting original_str).
# #                   First string in each pair is the string to find.
# #                   The second string is the string to replace it with.
# def str_replace_safe(original_str, *args):
#    if len(args) == 0 or len(args) % 2 == 1:
#       raise RuntimeError("len(args) must be even and non-zero.")
#    def recursive_op(str, replacements):
#       # TODO
#       return
#    return recursive_op(original_str, args)

#################################################################################
# DISCORD #######################################################################
#################################################################################

def user_to_str(user):
   return "{0} (ID: {1})".format(str(user.name), str(user.id))

def role_to_str(role):
   return "{0} (ID: {1})".format(str(role.name), str(role.id))

# Currently unused
# # This can take either an ID string or a channel object.
# def ch_to_str(obj):
#    ch_id = None
#    if isinstance(obj, basestring):
#       ch_id = obj
#    else:
#       ch_id = obj.id # Assumed to be a channel object
#    return "<#{0}> (ID: {0})".format(str(ch_id))

# PRECONDITION: The text full-matches re_user_mention.
def umention_str_to_id(text):
   assert re_user_mention.fullmatch(text)
   assert text.startswith("<@") and text.endswith(">")
   ret = None
   if text[2] == "!":
      ret = text[3:-1]
   else:
      ret = text[2:-1]
   assert len(ret) > 0
   return ret

def get_all_mentions(text):
   mentions = []
   for mention_string in re_user_mention.findall(text):
      mentions.append(umention_str_to_id(mention_string))
   return mentions

#################################################################################
# WEB HELPER FUNCTIONS ##########################################################
#################################################################################

# RETURNS: Bytes object of the file.
def download_from_url(url):
   request = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
   response = urllib.request.urlopen(request)
   return response.read()

#################################################################################
# FILE I/O ######################################################################
#################################################################################

_CWD = os.getcwd()
_ENCODING = "utf-8"

# This overwrites whatever file is specified with the data.
def json_write(relfilepath, data=None):
   mkdir_recursive(relfilepath)
   with open(relfilepath, encoding=_ENCODING, mode="w") as f:
      f.write(json.dumps(data, sort_keys=True, indent=3))
   return

def json_read(relfilepath):
   with open(relfilepath, encoding=_ENCODING, mode="r") as f:
      return json.loads(f.read())

def mkdir_recursive(relfilepath):
   absfilepath = os.path.join(_CWD, relfilepath)
   absdir = os.path.dirname(absfilepath)
   try:
      os.makedirs(absdir)
   except FileExistsError:
      pass
   return

###############################################################################
# COMMON SERVER MANAGEMENT OPERATIONS #########################################
###############################################################################

async def close_channel(client, channel, bot_flair_names):
   print("A CHANNEL CLOSED.")
   everyone = channel.server.default_role
   allow = discord.Permissions.none()
   deny = discord.Permissions.all()
   overwrite = discord.PermissionOverwrite.from_pair(allow=allow, deny=deny)
   try:
      await ensure_bot_permissions(client, channel, bot_flair_names)
      await client.edit_channel_permissions(channel, everyone, overwrite=overwrite)
   except discord.errors.Forbidden as e:
      raise e
   except:
      print(traceback.format_exc())
      print("CHANNEL FAILED TO CLOSE.")
      await client.send_msg(channel, "This channel failed to close.")
   return

async def open_channel(client, channel_name, server, bot_flair_names):
   channel = client.search_for_channel_by_name(channel_name, server)
   if channel is None:
      try:
         channel = await client.create_channel(server, channel_name)
      except discord.errors.Forbidden:
         await client.send_msg(msg, "Permission error: I'm not allowed to create channels.")
         raise errors.OperationAborted

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
   overwrite = discord.PermissionOverwrite.from_pair(allow=allow, deny=deny)
   for target in targets:
      await client.edit_channel_permissions(channel, target, overwrite=overwrite)
   return

#################################################################################
# FLAIRS ########################################################################
#################################################################################

def flair_names_to_object(server, flair_names):
   flair_objects = []
   for flair_object in server.roles:
      if flair_object.name in flair_names:
         flair_objects.append(flair_object)
         continue
   return flair_objects

# A non-list version of the function...
def flair_name_to_object(server, flair_name, case_sensitive=True):
   if case_sensitive:
      for flair_object in server.roles:
         if flair_object.name == flair_name:
            return flair_object
   else:
      flair_name = flair_name.lower()
      for flair_object in server.roles:
         if flair_object.name.lower() == flair_name:
            return flair_object
   return None

async def remove_flairs_by_name(client, member, *flair_names, case_sensitive=True):
   to_remove = []
   if case_sensitive:
      for flair_object in member.roles:
         if flair_object.name in flair_names:
            to_remove.append(flair_object)
   else:
      flair_names_lower = [e.lower() for e in flair_names]
      for flair_object in member.roles:
         if flair_object.name.lower() in flair_names_lower:
            to_remove.append(flair_object)
   await client.remove_roles(member, *to_remove)
   return

def role_is_unused(server, role_obj):
   for member in server.members:
      for member_role in member.roles:
         if member_role == role_obj:
            return False
   return True

#################################################################################
# ASYNCIO AND SYNCHRONIZATION ###################################################
#################################################################################

def synchronized(lock_attr_name):
   def function_decorator(function):
      async def wrapper_function(self, *args, **kwargs):
         lock = getattr(self, lock_attr_name)
         await lock.acquire()
         ret = None
         try:
            ret = await function(self, *args, **kwargs)
         finally:
            lock.release()
         return ret
      return wrapper_function
   return function_decorator

# Allows the starting of coroutines anywhere, even in non-async functions.
# This may also be useful in async functions as it schedules a callback, then
# returns,
def start_coroutine(future):
   loop = asyncio.get_event_loop()
   async def coro():
      await future
      loop.call_soon()
      return
   loop.create_task(coro())
   return

# async def asyncio_small_pipeline(*args, *kwargs):
#    TODO

#################################################################################
# OTHERS ########################################################################
#################################################################################

_true_strings = ["true","1","t","y", "yes", "ye"]
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

# TODO: Consider guaranteeing uniqueness of the filename.
def generate_temp_filename():
   return "temp" + str(random.getrandbits(128))

# Returns True if text is considered to be a safe directory name.
# Note that it is stricter than the actual naming restrictions.
# For instance, it doesn't allow spaces to be used.
# This function is usually used for double-verification.
def is_safe_directory_name(text):
   if re_dirname_once.search(text) and re_dirname_fullmatch.fullmatch(text):
      return True
   else:
      return False

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

