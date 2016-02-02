import asyncio
import re
import datetime

import discord

import utils
import errors

import servermodules.servermodule as servermodule

class MentionSearchModule(servermodule.ServerModule):

   _RE_OPTION_CH = re.compile("ch=[\w\W]+") # e.g. "ch=<#124672134>"
   _RE_OPTION_M = re.compile("m=\d+") # e.g. "m=100"
   _RE_OPTION_R = re.compile("r=\d+") # e.g. "m=1000"

   _HELP_SUMMARY_LINES = """
`{pf}mentions search [options]` or `{pf}mb s [options]` - Search mentions.
   """.strip().splitlines()

   _HELP_DETAIL_LINES = """
`{pf}mentions search [options]` or `{pf}mb s [options]` - Search mentions.
option: `--privmsg` or `-p` - Send mentions via PM instead.
option: `--ch=[channel]` - Channel to search (this channel by default).
option: `--m=[num]` - Number of mentions to search for.
option: `--r=[num]` - Number of messages to be searched through.
option: `--verbose` or `-v` - Include extra information.
   """.strip().splitlines()

   def __init__(self, client):
      self._client = client
      self._command_names = ["s","search"]
      return

   @property
   def command_names(self):
      return self._command_names

   @command_names.setter
   def command_names(self, value):
      self._command_names = value

   def get_help_summary(self, cmd_prefix, privilegelevel=0):
      return self._prepare_help_content(self._HELP_SUMMARY_LINES, cmd_prefix, privilegelevel)

   def get_help_detail(self, substr, cmd_prefix, privilegelevel=0):
      return self._prepare_help_content(self._HELP_DETAIL_LINES, cmd_prefix, privilegelevel)

   # Call this every time a message is received.
   async def on_message(self, msg):
      pass

   # Call this to process a command.
   async def process_cmd(self, substr, msg, privilegelevel=0):
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
         elif (ch is None) and self._RE_OPTION_CH.fullmatch(flag):
            ch = flag[3:]
         elif (mentions_to_get == None) and self._RE_OPTION_M.fullmatch(flag):
            mentions_to_get = int(flag[2:])
         elif (search_range == None) and self._RE_OPTION_R.fullmatch(flag):
            search_range = int(flag[2:])
         else: # Invalid flag!
            raise InvalidCommandArgumentsError

      # Get channel object from ch (and handle the default value)
      if ch is None:
         channel = msg.channel
      else:
         server_to_search = msg.server
         if server_to_search == None:
            return await self._client.send_msg(msg, "Sorry, the --ch option is unusable in private channels.")
         channel = self._client.search_for_channel(ch, enablenamesearch=True, serverrestriction=server_to_search)
         if channel is None:
            return await self._client.send_msg(msg, "Channel not found. Search failed.")
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
      searched = 0
      mentions_left = mentions_to_get
      print("MENTIONS SEARCH IS RETRIEVING {} MESSAGES.".format(str(search_range)))
      async for retrieved_msg in self._client.logs_from(channel, limit=search_range):
         searched += 1
         if msg.author in retrieved_msg.mentions:
            search_results.append(retrieved_msg)
            mentions_left -= 1
            if mentions_left == 0:
               break
      print("MENTIONS SEARCH LOOKED THROUGH {} MESSAGES.".format(str(searched)))
      
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
         buf += _msg_list_to_string(search_results, verbose=verbose)

      return await self._client.send_msg(msg, buf)


# TODO: There already is a copy of this function in mentionbot.py...
def _msg_list_to_string(mentions, verbose=False): # TYPE: String
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





