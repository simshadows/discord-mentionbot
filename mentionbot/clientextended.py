import asyncio
import re

import discord

import errors

# To provide additional functionality.
class ClientExtended(discord.Client):

   def __init__(self, **kwargs):
      super(ClientExtended, self).__init__(**kwargs)
      self._MESSAGE_MAX_LEN = 2000
      self._re_alldigits = re.compile("\d+")
      self._re_mentionstr = re.compile("<@\d+>")
      self._re_chmentionstr = re.compile("<#\d+>")

      self._normal_game_status = ""
      return

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
   def search_for_user(self, text, enablenamesearch=False, serverrestriction=None): # TYPE: User
      if self._re_mentionstr.fullmatch(text):
         searchkey = lambda user : user.id == str(text[2:-1])
      elif self._re_alldigits.fullmatch(text):
         searchkey = lambda user : user.id == str(text)
      elif enablenamesearch:
         searchkey = lambda user : user.name == str(text)
      else:
         return None

      if serverrestriction is None:
         servers = self.servers
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
   def search_for_channel(self, text, enablenamesearch=False, serverrestriction=None): # Type: Channel
      if self._re_chmentionstr.fullmatch(text):
         return self.get_channel(text[2:-1])
      elif self._re_alldigits.fullmatch(text):
         return self.get_channel(text)
      elif enablenamesearch:
         searchkey = lambda channel : channel.name == str(text)
      else:
         return None

      if serverrestriction is None:
         servers = self.servers
      else:
         servers = [serverrestriction]

      for server in servers:
         for channel in server.channels:
            if discord.ChannelType.text != "text":
               continue
            if searchkey(channel):
               return channel
      return None

   def search_for_channel_by_name(self, text, server):
      for channel in server.channels:
         if discord.ChannelType.text != channel.type:
            continue
         if channel.name == str(text):
            print("CHANNEL TYPE: " + str(type(channel)))
            return channel
      print("CHANNEL NONE")
      return None


   # Sets game status. Clears it if None is passed.
   async def set_game_status(self, text):
      self._normal_game_status = text
      if text is None:
         await self.change_status(game=None)
      else:
         await self.change_status(discord.Game(name=text))
      return

   async def set_temp_game_status(self, text):
      if text is None:
         await self.change_status(game=None)
      else:
         await self.change_status(discord.Game(name=text))
      return

   async def remove_temp_game_status(self):
      if self._normal_game_status == "":
         await self.change_status(game=None)
      else:
         await self.change_status(discord.Game(name=self._normal_game_status))
      return

   # Send a message to a channel specified by a Channel, PrivateChannel, Server, or Message object.
   # TODO: Consider renaming this. It's kinda awkward to have both send_msg() and send_message().
   # TODO: self.send_message has other optional parameters. Pls include them somehow...
   async def send_msg(self, destination, text):
      text = str(text)
      if len(text) > 2000:
         text_to_append = "\nSorry m8, can't send more than " + str(self._MESSAGE_MAX_LEN) + " characters."
         content_len = self._MESSAGE_MAX_LEN - len(text_to_append)
         text = text[:content_len] + text_to_append

      if destination.__class__.__name__ is "Message":
         destination = destination.channel

      print("SENDING MESSAGE...")
      try:
         await self.send_message(destination, text)
      except:
         print("MESSAGE FAILED TO SEND!!!")
      return

   # This method also handles permission issues.
   async def perm_send_file(self, destination, fp, filename=None):
      try:
         await self.send_file(destination, fp, filename=filename)
      except:
         await send_msg(destination, "Error: Unable to post file. Are permissions set up?")
      return



