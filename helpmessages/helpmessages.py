
import os
import re

# TODO: Improve the helpmessages module. It's a rather bare class at the moment...
class HelpMessages:
   def __init__(self):
      return

   # Temporary until I can get the help messages thing working.
   def get_message(self, substr, privilegelevel=0):
      (left1, right1) = _separate_left_word(substr)
      if (left1 == "mentions") or (left1 == "mb") or (left1 == "mentionbot"):
         (left2, right2) = _separate_left_word(right1)
         if left2 == "summary":
            filename = "helpmessages/help_mentions_summary.txt"
         elif (left2 == "search") or (left2 == "s"):
            filename = "helpmessages/help_mentions_search.txt"
         elif (left2 == "notify") or (left2 == "n"):
            filename = "helpmessages/help_mentions_notify.txt"
         else:
            filename = None
      elif (left1 == "admin") or (left1 == "a"):
         filename = "helpmessages/help_admin.txt"
      else:
         filename = None
      
      if filename is None:
         filename = "helpmessages/help.txt"

      return _read_helpmessage_file(filename, privilegelevel=privilegelevel)


# E.g. "hi    how   r u" -> ("hi","how   r u")
#      "hi"              -> ("hi","")
# NOTE: This is a duplicate of a method in mentionbot.py.
def _separate_left_word(text): # TYPE: Tuple<String>
   substrings = text.split(maxsplit=1) # "how r u?" -> ["how", "r u?"]
   if len(substrings) == 0:
      return ("","")
   elif len(substrings) == 1:
      substrings.append("")
   return tuple(substrings)


# Parses the specially formatted hm_*.txt file to produce a help message.
# PRECONDITION: File exists, and is not empty.
def _read_helpmessage_file(filename, privilegelevel=0):
   try:
      file_object = open(filename, "r")
   except FileNotFoundError:
      return "ERROR: " + filename + " not found."
   help_message = ""
   line_privlvl = 0
   re_privlvl_line = re.compile(">>> PRIVILEGE LEVEL \d+")
   for line in file_object:
      m = re_privlvl_line.match(line)
      if m:
         line_privlvl = int(m.group(0)[len(">>> PRIVILEGE LEVEL "):])
      elif (privilegelevel >= line_privlvl):
         help_message += line
   file_object.close()
   return help_message



