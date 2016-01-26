
import os
import re

class HelpMessages:

   # def __init__(self):
   #    content_filepath = "helpmessagescontent"
   #    if not os.path.isfile(self._CONTENT_FILEPATH): # If file doesn't exist
   #       raise IOError
      
   #    contentfile = open(content_filepath, "r")

   #    for line in contentfile:
   #       if line.startswith(">>>"):
   #          f

   def __init__(self):
      self.temp = "hello"
      print("HelpMessages initialized.")
      return


   # Temporary until I can get the help messages thing working.
   def get_message(self, substr, privilegelevel=0):
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
         #    if privilegelevel == 1:
         #       buf += "\n\n`/a toggle mentions notify` (The short version does not work.)"
         else:
            return None
      elif (left1 == "admin") or (left1 == "a"):
         if privilegelevel == 1:
            buf = "`/a say [text]`"
            buf += "\n`/a iam [@user] [cmd]`"
            buf += "\n`/a toggle mentions notify` (The short version does not work.)"
            buf += "\n`/a gettime`"
            buf += "\n`/a setgame [text]`"
            buf += "\n`/a setusername [text]`"
            buf += "\n`/a getemail`"
            buf += "\n`/a joinserver [invitelink]`"
            buf += "\n`/a leaveserver`"
            buf += "\n`/a throwexception`"
         else:
            return None
      else:
         buf = "**The following commands are available:**"

         buf += "\n\n`/mentions summary [options]` or `/mb summary` - Get summary of all latest mentions."
         buf += "\n(For help on usage, type `/help mentions summary`.)"
         
         buf += "\n\n`/mentions search [options]` or `/mb s [options]` - Search mentions."
         buf += "\n(For help on usage, type `/help mentions search`.)"

         # buf += "\n\n`/mentions notify` or `/mb n` - View and change settings of PM notification system."
         # buf += "\n(For help on usage, type `/help mentions notify`.)"

         buf += "\n\n`/avatar [usermention]` - Get the avatar URL of the user."

         buf += "\n\n`/randomcolour`" # TODO: TEMPORARYYYYYY

         buf += "\n\n`/source` - Where to get source code."

         buf += "\n\n`/rip` - Rest in pieces."

         buf += "\n\n`/status` - Get bot's current status."

         if privilegelevel == 1:
            buf += "\n\n`/admin [cmd]` or `/a [cmd]` - Bot admin commands. Must have permission to use."
            buf += "\n(Type `/help admin` for more information.)"

      return buf


# E.g. "hi    how   r u" -> ("hi","how   r u")
#      "hi"              -> ("hi","")
# NOTE: This is a duplicate of a method in mentionbot.py.
def separate_left_word(text): # TYPE: Tuple<String>
   substrings = text.split(" ", maxsplit=1)
   if len(substrings) == 1:
      substrings.append("")
   else:
      substrings[1] = substrings[1].strip()
   return tuple(substrings)
