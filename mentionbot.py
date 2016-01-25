

import discord # pip install --upgrade git+https://github.com/Rapptz/discord.py@legacy
import datetime
import sys
import copy
import time
import re
import os

LOGIN_DETAILS_FILENAME = "../mentionbot_botlogin1" # This file is used to login. Only contains two lines. Line 1 is email, line 2 is password.
MESSAGE_MAX_LEN = 2000
LOCALTIMEZONE_HOUR_OFFSET = 11 # Timestamps are either in GMT or the system timezone.
LOCALTIMEZONE_ABBR = "AEDT" # Name of system timezone
BOTOWNER_ID = str(119384097473822727) # User ID of the owner of this bot
INITIAL_GAME_STATUS = "INFP is master race"

INITIAL_GLOBALENABLED_MENTIONS_NOTIFY = False

def initialize_global_variables():

   global re_alldigits
   global re_mentionstr
   global re_chmentionstr
   re_alldigits = re.compile("\d+")
   re_mentionstr = re.compile("<@\d+>")
   re_chmentionstr = re.compile("<#\d+>")

   # For matching command options.
   global re_option_ch
   global re_option_m
   global re_option_r
   re_option_ch = re.compile("ch=[\w\W]+") # e.g. "ch=<#124672134>"
   re_option_m = re.compile("m=\d+") # e.g. "m=100"
   re_option_r = re.compile("r=\d+") # e.g. "m=1000"

   if re_option_ch.fullmatch("ch=<#23rcq2c>"):
      print("SUCCESS!!!")
   else:
      print("FAIL WHALE")

   # Global enabled/disabled
   global globalenabled_mentions_notify
   globalenabled_mentions_notify = INITIAL_GLOBALENABLED_MENTIONS_NOTIFY

   # The others
   global mentionSummaryCache
   global bot_mention
   global bot_name
   global botowner_mention
   global botowner
   global initialization_timestamp
   mentionSummaryCache = MentionSummaryCache()
   bot_mention = get_mention_str(client.user.id)
   bot_name = client.user.name
   botowner_mention = get_mention_str(BOTOWNER_ID)
   botowner = search_for_user(BOTOWNER_ID)
   initialization_timestamp = datetime.datetime.now()
   
   return

###########################################################################################

# Log in to discord
print("\nAttempting to log in using file '" + LOGIN_DETAILS_FILENAME + "'.")
if not os.path.isfile(LOGIN_DETAILS_FILENAME):
   print("File does not exist. Terminating.")
   sys.exit()
login_file = open(LOGIN_DETAILS_FILENAME, "r")
email = login_file.readline().strip()
password = login_file.readline().strip()
print("Email: " + email)
print("Password: " + len(password) * "*")
print("Logging in...", end="")
client = discord.Client()
client.login(email, password)
print(" success.")


@client.event
def on_ready():
   initialize_global_variables()
   set_game_status(INITIAL_GAME_STATUS)
   print("")
   print("LOGIN_DETAILS_FILENAME = '{}'".format(LOGIN_DETAILS_FILENAME))
   print("MESSAGE_MAX_LEN = '{}'".format(MESSAGE_MAX_LEN))
   print("LOCALTIMEZONE_HOUR_OFFSET = '{}'".format(LOCALTIMEZONE_HOUR_OFFSET))
   print("LOCALTIMEZONE_ABBR = '{}'".format(LOCALTIMEZONE_ABBR))
   print("BOTOWNER_ID = '{}'".format(BOTOWNER_ID))
   print("INITIAL_GAME_STATUS = '{}'".format(INITIAL_GAME_STATUS))
   print("")
   print("INITIAL_GLOBALENABLED_MENTIONS_NOTIFY = '{}'".format(INITIAL_GLOBALENABLED_MENTIONS_NOTIFY))
   print("")
   print("Bot owner: " + botowner.name)
   print("Bot name: " + bot_name)
   print("")
   print("Initialization complete.")
   print("")

   
@client.event
def on_message(msg):

   if msg.author == client.user:
      return # never process own messages.

   text = msg.content.strip()
   (left, right) = separate_left_word(text)
   if msg.channel.__class__.__name__ is "Channel":
      try:
         print("msg rcv #" + msg.channel.name + ": " + str(text.encode("unicode_escape")))
      except Exception:
         print("msg rcv (UNKNOWN DISPLAY ERROR)")

      if text.startswith("/"): 
         cmd1(text[1:].strip(), msg, no_default=True)

      elif left == "$mb":
         cmd1_mentions(right, msg, no_default=False)

      # EASTER EGG REPLY.
      elif left == "$blame" and bot_mention in text:
         send_msg(msg, "no fk u")

      elif (bot_mention in text or text == client.user.name + " pls"):
         cmd1_mentions_summary("", msg, add_extra_help=True)
      
      else:
         mentionSummaryCache.add_message(msg)
         simple_easter_egg_replies(msg)

   else:
      send_msg(msg, "sry m8 im not programmed to do anything fancy with pms yet")
      print("private msg rcv from" + msg.author.name + ": " + text)
   return


def cmd1(substr, msg, no_default=False):
   substr = substr.strip()
   if substr == "" and not no_default:
      cmd1_mentions_summary("", msg, add_extra_help=False)
   else:
      (left, right) = separate_left_word(substr)

      if left == "help":
         cmd_help(right, msg)

      elif (left == "mentions") or (left == "mb") or (left == "mentionbot"):
         cmd1_mentions(right, msg)

      elif left == "avatar":
         cmd1_avatar(right, msg)

      elif left == "source":
         cmd_source(msg)

      elif left == "rip":
         send_msg(msg, "doesnt even deserve a funeral")

      elif left == "status":
         buf = "**Status:**"
         buf += "\nBot current uptime: {}. ".format(seconds_to_string(get_bot_uptime()))
         buf += "\nNotification system enabled = " + str(globalenabled_mentions_notify)
         send_msg(msg, buf)

      elif (left == "admin") or (left == "a"):
         cmd_admin(right, msg)
      
      # else:
      #    cmd_invalidcmd(msg)
   
   return


def cmd1_mentions(substr, msg, no_default=False):
   substr = substr.strip()
   if substr == "" and not no_default:
      cmd1_mentions_summary("", msg, add_extra_help=False)
   else:
      (left, right) = separate_left_word(substr)

      if left == "summary":
         cmd1_mentions_summary(right, msg)

      elif (left == "search") or (left == "s"):
         cmd1_mentions_search(right, msg)

      elif (left == "notify") or (left == "n"):
         cmd1_mentions_notify(right, msg)
      
      else:
         cmd_invalidcmd(msg)
   
   return


def cmd1_mentions_summary(substr, msg, add_extra_help=False):
   send_as_pm = False
   preserve_data = False
   verbose = False

   # Parse substring for options. Return on invalid option.
   flags = parse_flags(substr)
   for flag in flags:
      if (send_as_pm == False) and ((flag == "p") or (flag == "privmsg")):
         send_as_pm = True
         add_extra_help = False # Never attach extra help message if sent via PM.
      elif (preserve_data == False) and ((flag == "k") or (flag == "preservedata")):
         preserve_data = True
      elif (verbose == False) and ((flag == "v") or (flag == "verbose")):
         verbose = True
      else: # Invalid flag!
         return cmd_badargs(msg)

   if mentionSummaryCache.user_has_mentions(msg.author.id):
      buf = "Here's a summary of your recent mentions."
      buf += "\nBot current uptime: {}. ".format(seconds_to_string(get_bot_uptime()))
      if add_extra_help:
         buf += " (`/help` for more commands.)".format(bot_name)
      buf += "\n\n" + mentionSummaryCache.user_data_to_string(msg.author.id, verbose=verbose)
      if not preserve_data:
         mentionSummaryCache.delete_user_data(msg.author.id)
   else:
      buf = "sry m8 no mentions to see"
      buf += "\nBot current uptime: {}".format(seconds_to_string(get_bot_uptime()))
      if add_extra_help:
         buf += " (`/help` for more commands.)".format(bot_name)
   
   if send_as_pm:
      send_msg(msg.author, buf)
      send_msg(msg, "List of mentions sent via PM.")
   else:
      send_msg(msg, buf)
   return


def cmd1_mentions_search(substr, msg):
   # return send_msg(msg, "This command is temporarily unavailable due to possible abuse.") # TEMPORARY.
   send_as_pm = False # TYPE: Boolean
   verbose = False # TYPE: Boolean
   ch = None # TYPE: String, or None. This is a channel name, channel mention, or channel ID.
   mentions_to_get = None # TYPE: Int, or None. This is the number of mentions this function will try to fetch.
   search_range = None # TYPE: Int, or None. This is the number of messages the function will search through.

   flags = parse_flags(substr)
   for flag in flags:
      if (send_as_pm == False) and ((flag == "p") or (flag == "privmsg")):
         send_as_pm = True
      elif (verbose == False) and ((flag == "v") or (flag == "verbose")):
         verbose = True
      elif (ch is None) and re_option_ch.fullmatch(flag):
         ch = flag[3:]
      elif (mentions_to_get == None) and re_option_m.fullmatch(flag):
         mentions_to_get = int(flag[2:])
      elif (search_range == None) and re_option_r.fullmatch(flag):
         search_range = int(flag[2:])
      else: # Invalid flag!
         return cmd_badargs(msg)

   # Get channel object from ch (and handle the default value)
   if ch is None:
      channel = msg.channel
   else:
      server_to_search = msg.server
      if server_to_search == None:
         return send_msg(msg, "Sorry, the --ch option is unusable in private channels.")
      channel = search_for_channel(ch, enablenamesearch=True, serverrestriction=server_to_search)
      if channel is None:
         return send_msg(msg, "Channel not found. Search failed.")
   # Handle other default values or invalid inputs.
   if mentions_to_get == None:
      mentions_to_get = 3
   elif mentions_to_get == 0:
      return cmd_badargs(msg)
   if search_range == None:
      search_range = 2000
   elif search_range == 0:
      return cmd_badargs(msg)

   # Search
   search_results = []
   searched = 0 # Used for feedback on how many messages were searched.
   mentions_left = mentions_to_get
   search_before = None # Used for generating more logs after the limit is reached.
   while True:
      print("RETRIEVING 100 MESSAGES FROM " + channel.name + "...")
      client.send_typing(msg.channel) # Feedback that the bot is still running.
      more_left_to_search = False
      for retrieved_msg in client.logs_from(channel, limit=search_range, before=search_before):
         if searched >= search_range:
            break
         searched += 1
         prev_retrieved_msg = retrieved_msg # Used for generating more logs after the limit is reached.
         more_left_to_search = True # Used for generating more logs after the limit is reached.
         if msg.author in retrieved_msg.mentions:
            search_results.append(retrieved_msg)
            mentions_left -= 1
            if mentions_left == 0:
               break
      if (searched >= search_range) or not (more_left_to_search and (mentions_left > 0)):
         break
      search_before = prev_retrieved_msg
   
   # Report search results
   if len(search_results) == 0:
      buf = "No results found."
      buf += "\nLooked through " + str(searched) + " messages in <#" + channel.id + ">."
      buf += "\n(mentions_to_get=" + str(mentions_to_get) + ", range=" + str(search_range) + ")"
   else:
      mentions_found = mentions_to_get - mentions_left
      buf = "Here are your " + str(mentions_found) + " latest mentions in <#" + channel.id + ">."
      buf += "\n(mentions_to_get=" + str(mentions_to_get) + ", range=" 
      buf += str(search_range) + ", searched=" + str(searched) + "):"
      buf += "\n\n"
      buf += msg_list_to_string(search_results, verbose=verbose)

   return send_msg(msg, buf)


def cmd1_mentions_notify(substr, msg):
   return send_msg(msg, "This feature has not yet been implemented.")


def cmd1_avatar(substr, msg):
   (left, right) = separate_left_word(substr)
   user = None
   if len(left) > 0:
      user = search_for_user(left, enablenamesearch=True, serverrestriction=msg.server)
      if user is None:
         return send_msg(msg, left + " doesn't even exist m8")
   else:
      user = msg.author

   # Guaranteed to have a user.
   avatar = user.avatar_url()
   if avatar == "":
      return send_msg(msg, left + " m8 get an avatar")
   else:
      return send_msg(msg, avatar)


def cmd_help(substr, msg):
   include_privileged_commands = is_privileged_user(msg.author.id)

   (left1, right1) = separate_left_word(substr)
   if (left1 == "mentions") or (left1 == "mb") or (left1 == "mentionbot"):
      (left2, right2) = separate_left_word(right1)
      if left2 == "summary":
         buf = "`/mentions summary [options]` or `/mb summary` - Get summary of all latest mentions."
         buf += "\noption: `--privmsg` or `-p` - Send mentions via PM instead."
         buf += "\noption: `--preservedata` or `-k` - Cache entries will not be deleted."
         buf += "\noption: `--verbose` or `-v` - Include extra information."
      elif (left2 == "search") or (left2 == "s"):
         buf = "`/mentions search [options]` or `/mb s [options]` - Search mentions."
         buf += "\noption: `--privmsg` or `-p` - Send mentions via PM instead."
         buf += "\noption: `--ch=[channel]` - Channel to search (this channel by default)."
         buf += "\noption: `--m=[num]` - Number of mentions to search for."
         buf += "\noption: `--r=[num]` - Number of messages to be searched through."
         buf += "\noption: `--verbose` or `-v` - Include extra information."
      # elif (left2 == "notify") or (left2 == "n"):
      #    buf = "`/mentions notify` or `/mb n` - View and change settings of PM notification system."
      #    if include_privileged_commands:
      #       buf += "\n\n`/a toggle mentions notify` (The short version does not work.)"
      else:
         return cmd_invalidcmd(msg)
   elif (left1 == "admin") or (left1 == "a"):
      if include_privileged_commands:
         buf = "`/a say [text]`"
         buf += "\n`/a iam [@user] [cmd]`"
         buf += "\n`/a toggle mentions notify` (The short version does not work.)"
         buf += "\n`/a gettime`"
         buf += "\n`/a setgame [text]`"
         buf += "\n`/a setusername [text]`"
         buf += "\n`/a getemail`"
         buf += "\n`/a throwexception`"
      else:
         return cmd_badprivileges(msg)
   else:
      buf = "**The following commands are available:**"

      buf += "\n\n`/mentions summary [options]` or `/mb summary` - Get summary of all latest mentions."
      buf += "\n(For help on usage, type `/help mentions summary`.)"
      
      buf += "\n\n`/mentions search [options]` or `/mb s [options]` - Search mentions."
      buf += "\n(For help on usage, type `/help mentions search`.)"

      # buf += "\n\n`/mentions notify` or `/mb n` - View and change settings of PM notification system."
      # buf += "\n(For help on usage, type `/help mentions notify`.)"

      buf += "\n\n`/avatar [usermention]` - Get the avatar URL of the user."

      buf += "\n\n`/source` - Where to get source code."

      buf += "\n\n`/rip` - Rest in pieces."

      buf += "\n\n`/status` - Get bot's current status."

      if include_privileged_commands:
         buf += "\n\n`/admin [cmd]` or `/a [cmd]` - Bot admin commands. Must have permission to use."
         buf += "\n(Type `/help admin` for more information.)"

   return send_msg(msg, buf)


def cmd_source(msg):
   # buf = "https://github.com/simshadows/discord-mentionbot"
   buf = "idk, ask sim."
   return send_msg(msg, buf)


def cmd_admin(substr, msg):
   if not is_privileged_user(msg.author.id):
      cmd_badprivileges(msg)
      return

   substr = substr.strip()
   if substr == "" and not no_default:
      cmd_invalidcmd(msg)
   else:
      (left1, right1) = separate_left_word(substr)

      if left1 == "say":
         send_msg(msg, right1)

      elif left1 == "iam":
         cmd_admin_iam(right1, msg)

      elif left1 == "toggle":
         (left2, right2) = separate_left_word(right1)
         if (left2 == "mentions") or (left2 == "mb") or (left2 == "mentionbot"):
            (left3, right3) = separate_left_word(right2)
            if (left3 == "notify") or (left3 == "n"):
               global globalenabled_mentions_notify # TODO: Is this actually needed?
               globalenabled_mentions_notify = not globalenabled_mentions_notify
               send_msg(msg, "Notification system enabled = " + str(globalenabled_mentions_notify))
            else:
               cmd_invalidcmd(msg)
         else:
            cmd_invalidcmd(msg)

      elif left1 == "gettime":
         send_msg(msg, datetime.datetime.now().strftime("My current system time: %c " + LOCALTIMEZONE_ABBR))

      elif left1 == "setgame":
         set_game_status(right1)
         send_msg(msg, "Game set to: " + right1)

      elif left1 == "setusername":
         client.edit_profile(password, username=right1)
         bot_name = right1 # TODO: Consider making this a function. Or stop using bot_name...
         send_msg(msg, "Username set to: " + right1)

      elif left1 == "getemail":
         send_msg(msg, "My email is: " + email)

      elif left1 == "throwexception":
         raise Exception
      
      else:
         cmd_invalidcmd(msg)
   return


def cmd_admin_iam(substr, msg):
   substr = substr.strip()
   (left, right) = separate_left_word(substr)
   
   if re_mentionstr.fullmatch(left):
      user_to_pose_as = left[2:-1]
      replacement_msg = copy.deepcopy(msg)
      replacement_msg.author = search_for_user(user_to_pose_as)
      if replacement_msg.author == None:
         return send_msg(msg, "Unknown user.")
      replacement_msg.content = right
      send_msg(msg, "Executing command as {}: {}".format(replacement_msg.author, replacement_msg.content))
      send_msg(msg, "**WARNING: There are no guarantees of the safety of this operation.**")
      on_message(replacement_msg)
   return


# If bad arguments were entered for a command.
def cmd_badargs(msg):
   return send_msg(msg, "soz m8 one or more (or 8) arguments are invalid")


# For attempts to use commands without sufficient privileges
def cmd_badprivileges(msg):
   return send_msg(msg, "im afraid im not allowed to do that for you m8")


# For invalid commands.
def cmd_invalidcmd(msg):
   return send_msg(msg, "sry m8 idk what ur asking") # intentional typos. pls don't lynch me.


def simple_easter_egg_replies(msg):
   if msg.content.startswith("$blame " + botowner_mention) or msg.content.startswith("$blame " + botowner.name):
      send_msg(msg, "he didnt do shit m8")
   return


# TODO: Replace with better data structure, or integrate it into MentionLogger.
#       This version is just horribly inefficient linear searching,
#       , and operates on messages directly.
class MentionSummaryCache:
   
   def __init__(self):
      self._mention_list = [] # FORMAT: list<tuple<userID, list<messageObject> >>
      print("MentionSummaryCache initialized.")
      return

   # Adds a message to the collection (and removes redundant data).
   def add_message(self, msg):

      # Get all users mentioned.
      user_ids_mentioned = [] # TYPE: List<String>
      for user in msg.mentions:
         user_ids_mentioned.append(user.id)

      for user_mentioned in user_ids_mentioned:
         
         # Check if the message's sender is in the list
         user_tuple = None # FORMAT: Tuple<userID, List<messageObject> >
         for j in self._mention_list:
            if j[0] == user_mentioned:
               user_tuple = j
               break
         
         # If user needs to be added to the list, add them.
         # If they're already on the list, check if there's already a message from the current channel.
         if user_tuple == None:
            user_tuple = (user_mentioned, [])
            self._mention_list.append(user_tuple)
         else:
            for i in user_tuple[1]:
               if i.channel.id == msg.channel.id:
                  user_tuple[1].remove(i)
                  print("An older MentionSummaryCache entry was removed!")
                  break

         # Append new message
         user_tuple[1].append(msg)

      return

   # Clears data about a single user from the collection.
   def delete_user_data(self, user_ID):
      for i in self._mention_list:
         if i[0] == user_ID:
            self._mention_list.remove(i)
            break
      return

   # Gets all messages for a particular user.
   def get_user_latest(self, user_ID): # FORMAT: list<messageObject>
      user_message_list = [] # FORMAT: tuple<userID, list<messageObject> >
      for i in self._mention_list:
         if i[0] == user_ID:
            user_message_list = i[1]
            break
      return user_message_list

   # Output is not NL-terminated.
   def user_data_to_string(self, user_ID, verbose=False): # TYPE: String

      return msg_list_to_string(self.get_user_latest(user_ID), verbose=verbose)
   def user_has_mentions(self, user_ID): #TYPE: Boolean
      for i in self._mention_list:
         if i[0] == user_ID:
            return True
      return False


def msg_list_to_string(mentions, verbose=False): # TYPE: String
   now = datetime.datetime.now()
   buf = "" # FORMAT: String
   for i in mentions:
      
      timediff = now - i.timestamp
      seconds = timediff.seconds - (LOCALTIMEZONE_HOUR_OFFSET*60*60)
      
      if verbose:
         buf += "Message ID: " + i.id + "\n"
         # buf += "Timestamp: " + i.timestamp.strftime("%c UTC") + "\n" # Unnecessary
      buf += "By " + i.author.name + " in " + get_chmention_str(i.channel.id) + ", " + seconds_to_string(seconds) + " ago\n"
      buf += i.content + "\n\n"
   if buf != "":
      buf = buf[:-2]
   return buf


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


# Search for a Member object.
# Strings that may yield a Member object:
#     A valid user ID
#     A valid user mention string (e.g. "<@12345>")
#     A valid username (only exact matches)
# Note: Multiple users may be using the same username. This function will only return one.
# Note: only guaranteed to work if input has no leading/trailing whitespace (i.e. stripped).
# PARAMETER: enablenamesearch - True -> this function may also search by name.
#                               False -> this function will not search by name.
# PARAMETER: serverrestriction - TYPE: Server, None
#                                If None, search occurs over all reachable searchers.
#                                If it's a valid server, the search is done on only that server.
def search_for_user(text, enablenamesearch=False, serverrestriction=None): # TYPE: User
   if re_mentionstr.fullmatch(text):
      searchkey = lambda user : user.id == str(text[2:-1])
   elif re_alldigits.fullmatch(text):
      searchkey = lambda user : user.id == str(text)
   elif enablenamesearch:
      searchkey = lambda user : user.name == str(text)
   else:
      return None

   if serverrestriction is None:
      servers = client.servers
   else:
      servers = [serverrestriction]

   for server in servers:
      for user in server.members:
         if searchkey(user):
            return user
   return None


# Search for a Channel object.
# Strings that may yield a Channel object:
#     A valid channel ID
#     A valid channel mention string (e.g. "<@12345>")
#     A valid channel name (only exact matches)
# PRECONDITION: Input has no leading/trailing whitespace (i.e. stripped).
# PARAMETER: enablenamesearch - True -> this function may also search by name.
#                               False -> this function will not search by name.
# PARAMETER: serverrestriction - TYPE: Server, None
#                                If None, search occurs over all reachable searchers.
#                                If it's a valid server, the search is done on only that server.
def search_for_channel(text, enablenamesearch=False, serverrestriction=None): # Type: Channel
   if re_chmentionstr.fullmatch(text):
      searchkey = lambda channel : channel.id == str(text[2:-1])
   elif re_alldigits.fullmatch(text):
      searchkey = lambda channel : channel.id == str(text)
   elif enablenamesearch:
      searchkey = lambda channel : channel.name == str(text)
   else:
      return None

   if serverrestriction is None:
      servers = client.servers
   else:
      servers = [serverrestriction]

   for server in servers:
      for channel in server.channels:
         if searchkey(channel):
            return channel
   return None


def is_privileged_user(user_ID):
   return user_ID == BOTOWNER_ID


# E.g. converts "123" into "<@123".
def get_mention_str(user_ID): # TYPE: String
   return "<@" + str(user_ID) + ">"


def get_chmention_str(channel_ID): # TYPE: String
   return "<#" + str(channel_ID) + ">"


# E.g. "hi    how   r u" -> ("hi","how   r u")
#      "hi"              -> ("hi","")
def separate_left_word(text): # TYPE: Tuple<String>
   substrings = text.split(" ", maxsplit=1)
   if len(substrings) == 1:
      substrings.append("")
   else:
      substrings[1] = substrings[1].strip()
   return tuple(substrings)


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


# RETURNS: Bot's current uptime in seconds
def get_bot_uptime():
   timediff = datetime.datetime.now() - initialization_timestamp
   return timediff.seconds


# Sets game status. Clears it if None is passed.
def set_game_status(text):
   if text is None:
      client.change_status(game=None)
   else:
      client.change_status(discord.Game(name=text))
   return


# Send a message to a channel specified by a Channel, PrivateChannel, Server, or Message object.
def send_msg(destination, text):
   text = str(text)
   if len(text) > 2000:
      text_to_append = "\nSorry m8, can't send more than " + str(MESSAGE_MAX_LEN) + " characters."
      content_len = MESSAGE_MAX_LEN - len(text_to_append)
      text = text[:content_len] + text_to_append

   if destination.__class__.__name__ is "Message":
      destination = destination.channel

   return client.send_message(destination, text)

client.run() # let the games begin...


