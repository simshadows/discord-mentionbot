
import datetime

import discord

import utils
import errors

# TODO: Replace with better data structure, or integrate it into MentionLogger.
#       This version is just horribly inefficient linear searching,
#       , and operates on messages directly.
class MentionSummaryModule:
   
   def __init__(self, client):
      self._client = client
      self._mention_list = [] # FORMAT: list<tuple<userID, list<messageObject> >>
      self._initialization_timestamp = datetime.datetime.utcnow()
      return

   # Call this every time a message is received.
   def on_message(self, msg):
      self._add_message(msg)
      return

   # Call this to process a command.
   def process_cmd(self, substr, msg, add_extra_help=False):
      send_as_pm = False
      preserve_data = False
      verbose = False

      # Parse substring for options. Return on invalid option.
      flags = utils.parse_flags(substr)
      for flag in flags:
         if (send_as_pm == False) and ((flag == "p") or (flag == "privmsg")):
            send_as_pm = True
            add_extra_help = False # Never attach extra help message if sent via PM.
         elif (preserve_data == False) and ((flag == "k") or (flag == "preservedata")):
            preserve_data = True
         elif (verbose == False) and ((flag == "v") or (flag == "verbose")):
            verbose = True
         else: # Invalid flag!
            raise errors.InvalidCommandArgumentsError

      if self._user_has_mentions(msg.author.id):
         buf = "Here's a summary of your recent mentions."
         buf += "\nBot current uptime: {}. ".format(utils.seconds_to_string(self._get_uptime()))
         if add_extra_help:
            buf += " (`/help` for more commands.)"
         buf += "\n\n" + _msg_list_to_string(self._get_user_latest(msg.author.id), verbose=verbose)
         if not preserve_data:
            self._delete_user_data(msg.author.id)
      else:
         buf = "sry m8 no mentions to see"
         buf += "\nBot current uptime: {}".format(utils.seconds_to_string(self._get_uptime()))
         if add_extra_help:
            buf += " (`/help` for more commands.)"
      
      if send_as_pm:
         self._client.send_msg(msg.author, buf)
         self._client.send_msg(msg, "List of mentions sent via PM.")
      else:
         self._client.send_msg(msg, buf)
      return

   # Adds a message to the collection (and removes redundant data).
   def _add_message(self, msg):

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
   def _delete_user_data(self, user_ID):
      for i in self._mention_list:
         if i[0] == user_ID:
            self._mention_list.remove(i)
            break
      return

   # Gets all messages for a particular user.
   def _get_user_latest(self, user_ID): # FORMAT: list<messageObject>
      user_message_list = [] # FORMAT: tuple<userID, list<messageObject> >
      for i in self._mention_list:
         if i[0] == user_ID:
            user_message_list = i[1]
            break
      return user_message_list
   
   def _user_has_mentions(self, user_ID): #TYPE: Boolean
      for i in self._mention_list:
         if i[0] == user_ID:
            return True
      return False

   # RETURNS: Instance uptime in seconds.
   def _get_uptime(self): # TYPE: Int
      return (datetime.datetime.utcnow() - self._initialization_timestamp).seconds



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
