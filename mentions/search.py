
import re
import datetime

import discord

import utils
import errors

class MentionSearchModule:
   def __init__(self, client):
      self.re_option_ch = re.compile("ch=[\w\W]+") # e.g. "ch=<#124672134>"
      self.re_option_m = re.compile("m=\d+") # e.g. "m=100"
      self.re_option_r = re.compile("r=\d+") # e.g. "m=1000"

      self.client = client
      return

   def process_cmd(self, substr, msg):
      send_as_pm = False # TYPE: Boolean
      verbose = False # TYPE: Boolean
      ch = None # TYPE: String, or None. This is a channel name, channel mention, or channel ID.
      mentions_to_get = None # TYPE: Int, or None. This is the number of mentions this function will try to fetch.
      search_range = None # TYPE: Int, or None. This is the number of messages the function will search through.

      flags = utils.parse_flags(substr)
      for flag in flags:
         if (send_as_pm == False) and ((flag == "p") or (flag == "privmsg")):
            send_as_pm = True
         elif (verbose == False) and ((flag == "v") or (flag == "verbose")):
            verbose = True
         elif (ch is None) and self.re_option_ch.fullmatch(flag):
            ch = flag[3:]
         elif (mentions_to_get == None) and self.re_option_m.fullmatch(flag):
            mentions_to_get = int(flag[2:])
         elif (search_range == None) and self.re_option_r.fullmatch(flag):
            search_range = int(flag[2:])
         else: # Invalid flag!
            raise InvalidCommandArgumentsError

      # Get channel object from ch (and handle the default value)
      if ch is None:
         channel = msg.channel
      else:
         server_to_search = msg.server
         if server_to_search == None:
            return self.client.send_msg(msg, "Sorry, the --ch option is unusable in private channels.")
         channel = self.client.search_for_channel(ch, enablenamesearch=True, serverrestriction=server_to_search)
         if channel is None:
            return self.client.send_msg(msg, "Channel not found. Search failed.")
      # Handle other default values or invalid inputs.
      if mentions_to_get == None:
         mentions_to_get = 3
      elif mentions_to_get == 0:
         raise InvalidCommandArgumentsError
      if search_range == None:
         search_range = 2000
      elif search_range == 0:
         raise InvalidCommandArgumentsError

      # Search
      search_results = []
      searched = 0 # Used for feedback on how many messages were searched.
      mentions_left = mentions_to_get
      search_before = None # Used for generating more logs after the limit is reached.
      while True:
         print("RETRIEVING 100 MESSAGES FROM " + channel.name + "...")
         self.client.send_typing(msg.channel) # Feedback that the bot is still running.
         more_left_to_search = False
         for retrieved_msg in self.client.logs_from(channel, limit=search_range, before=search_before):
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

      return self.client.send_msg(msg, buf)


# TODO: There already is a copy of this function in mentionbot.py...
def msg_list_to_string(mentions, verbose=False): # TYPE: String
   now = datetime.datetime.utcnow()
   buf = "" # FORMAT: String
   for i in mentions:
      timediff = now - i.timestamp
      if verbose:
         buf += "Message ID: " + i.id + "\n"
         # buf += "Timestamp: " + i.timestamp.strftime("%c UTC") + "\n" # Unnecessary
      buf += "By " + i.author.name + " in " + "<#{}>".format(i.channel.id) + ", " + utils.seconds_to_string(timediff.seconds) + " ago\n"
      buf += i.content + "\n\n"
   if buf != "":
      buf = buf[:-2]
   return buf





