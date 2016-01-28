
import discord

# TODO: Replace with better data structure, or integrate it into MentionLogger.
#       This version is just horribly inefficient linear searching,
#       , and operates on messages directly.
class MentionSummaryCache:
   
   def __init__(self):
      self._mention_list = [] # FORMAT: list<tuple<userID, list<messageObject> >>
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
