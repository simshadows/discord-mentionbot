import sys

# E.g. "hi    how   r u" -> ("hi","how   r u")
#      "hi"              -> ("hi","")
def separate_left_word(text): # TYPE: Tuple<String>
   substrings = text.split(maxsplit=1) # "how r u?" -> ["how", "r u?"]
   if len(substrings) == 0:
      return ("","")
   elif len(substrings) == 1:
      substrings.append("")
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

