import asyncio
import re
import datetime
import os
import copy

import discord
import dateutil.parser

from . import utils

ARBITRARILY_LARGE_NUMBER = 10000000000000

class MessageCache:
   _SECRET_TOKEN = utils.SecretToken()

   _CH_JSON_FILENAME = "channel.json"

   @classmethod
   async def get_instance(cls, client, cache_directory):
      inst = cls(cls._SECRET_TOKEN)
      inst._client = client
      inst._data_dir = cache_directory + "messagecache/"
      inst._messages_before_initialization = []
      
      inst._data = {}
      # A tree of dictionaries in this arrangement:
      # server_id -> channel_id -> list of messages stored in tuples
      # Each message entry is a tuple.

      print("Caching messages...")
      print("This will take a while if a lot of messages are being read.")
      await inst._fill_buffers()
      
      print(inst.get_debugging_info())
      return inst

   def __init__(self, token):
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
      return

   # PRECONDITION: Currently not operating on the buffers.
   async def record_message(self, msg):
      if not isinstance(msg.channel, discord.Channel):
         return # Never caches private messages.

      ch_dict = None
      try:
         ch_dict = self._data[msg.server.id]
      except KeyError:
         ch_dict = {}
         self._data[msg.server.id] = ch_dict

      ch_list = None
      try:
         ch_list = ch_dict[msg.channel.id]
      except KeyError:
         ch_list = []
         ch_dict[msg.channel.id] = ch_list

      ch_list.append(self._message_dict(msg))

      # Move to file if buffer is large enough.
      if len(self._data[msg.server.id][msg.channel.id]) >= 200:
         self._move_to_disk(msg.server.id, msg.channel.id)

      return

   # Generator reads cached messages from a channel, starting from the earliest.
   def read_messages(self, server_id, ch_id):
      ch_dir = self._get_ch_dir(server_id, ch_id)

      file_number = 0
      while True:
         file_number += 1
         file_contents = None
         try:
            file_contents = utils.json_read(ch_dir + str(file_number) + ".json")
         except FileNotFoundError:
            break
         for msg_dict in file_contents:
            msg_dict["t"] = dateutil.parser.parse(msg_dict["t"])
            yield msg_dict

      # After having read all files, output buffered messages.
      try:
         for msg_dict in self._data[server_id][ch_id]:
            yield msg_dict
      except KeyError:
         pass

   async def _fill_buffers(self):
      await self._client.set_temp_game_status("filling cache buffers.")
      loop = asyncio.get_event_loop()
      
      async def cache_server(server):
         ch_dict = None
         ch_dict_lock = asyncio.Lock()
         try:
            ch_dict = self._data[server.id]
         except KeyError:
            ch_dict = {}
            self._data[server.id] = ch_dict

         async def cache_channel(ch):
            if ch.type is discord.ChannelType.voice:
               return
            print("MessageCache caching messages in #" + ch.name)

            # TODO: Rename these variable names.
            # TODO: Turn this into a function? (see duplicated code...)
            ch_dir = self._get_ch_dir(server.id, ch.id)
            ch_json_filepath = ch_dir + self._CH_JSON_FILENAME
            
            ch_json_data = None
            try:
               ch_json_data = utils.json_read(ch_json_filepath)
            except FileNotFoundError:
               ch_json_data = {}

            # TODO: Turn this into a function? (see duplicated code...)
            ch_stored_timestamp = None
            try:
               ch_stored_timestamp = dateutil.parser.parse(ch_json_data["last message timestamp"])
            except KeyError:
               ch_stored_timestamp = datetime.datetime(datetime.MINYEAR, 1, 1)
               ch_json_data["last message timestamp"] = ch_stored_timestamp.isoformat()
               utils.json_write(ch_json_filepath, data=ch_json_data)

            # This will now fill a buffer all messages of a channel.
            # TODO: Consider filling a file, then reading off the file.
            msg_buffer = []
            try:
               async for msg in self._client.logs_from(ch, limit=ARBITRARILY_LARGE_NUMBER):
                  if msg.timestamp <= ch_stored_timestamp:
                     break
                  # Insert in front since we're reading messages starting from most recent.
                  msg_buffer.insert(0, self._message_dict(msg))
            except discord.errors.Forbidden:
               print("MessageCache unable to read #" + ch.name)
               return

            await ch_dict_lock.acquire()

            ch_dict[ch.id] = msg_buffer

            # Move every 5000 messages to disk.
            while len(ch_dict[ch.id]) >= 5000:
               self._move_to_disk(server.id, ch.id, messages=5000)

            # Move every 1000 messages to disk.
            while len(ch_dict[ch.id]) >= 1000:
               self._move_to_disk(server.id, ch.id, messages=1000)

            # Now move every 200 messages to disk.
            while len(ch_dict[ch.id]) >= 200:
               self._move_to_disk(server.id, ch.id, messages=200)

            ch_dict_lock.release()

            return

         chcache_futures = []
         for j in server.channels:
            chcache_futures.append(loop.create_task(cache_channel(j)))
         await asyncio.gather(*chcache_futures)

      scache_futures = []
      for i in self._client.servers:
         scache_futures.append(loop.create_task(cache_server(i)))
      await asyncio.gather(*scache_futures)

      await self._client.remove_temp_game_status()
      return

   # Moves specified channel's messages to disk.
   # PARAMETER: messages - Number of earlier messages to move to a single file.
   #                       If None, then all messages are moved.
   # PRECONDITION: messages > 0
   # PRECONDITION: server_id and ch_id are both valid keys.
   def _move_to_disk(self, server_id, ch_id, messages=None):
      print("MessageCache moving messages to disk.")
      ch_dir = self._get_ch_dir(server_id, ch_id)
      ch_json_filepath = ch_dir + self._CH_JSON_FILENAME

      # TODO: Turn this into a function? (see duplicated code...)
      ch_json_data = None
      try:
         ch_json_data = utils.json_read(ch_json_filepath)
      except FileNotFoundError:
         ch_json_data = {}

      # TODO: Turn this into a function? (see duplicated code...)
      ch_stored_timestamp = None
      try:
         ch_stored_timestamp = dateutil.parser.parse(ch_json_data["last message timestamp"])
      except KeyError:
         ch_stored_timestamp = datetime.datetime(datetime.MINYEAR, 1, 1)
         ch_json_data["last message timestamp"] = ch_stored_timestamp.isoformat()
         utils.json_write(ch_json_filepath, data=ch_json_data)

      ch_dict = self._data[server_id]

      # Split off the messages to be stored.
      if messages is None:
         to_store = ch_dict[ch_id]
         ch_dict[ch_id] = []
      else:
         to_store = ch_dict[ch_id][:messages]
         ch_dict[ch_id] = ch_dict[ch_id][messages:]

      latest_message = to_store[-1:][0]
      latest_timestamp_isoformat = latest_message["t"].isoformat()
      ch_json_data["last message timestamp"] = latest_timestamp_isoformat

      for msg_dict in to_store:
         # TODO: I still don't know what's causing this to be a string...
         # This temporary fix will have to do for now.
         if isinstance(msg_dict["t"], str):
            print("WARNING: msg_dict[t] is already a string. contents: " + msg_dict["t"])
         else:
            msg_dict["t"] = msg_dict["t"].isoformat() # Make serializable

      # Check the highest numbered json file.
      highest_json_file_number = 0
      for file_name in os.listdir(ch_dir):
         if file_name.endswith(".json"):
            file_number = None
            try:
               file_number = int(file_name[:-5])
            except ValueError:
               continue
            if file_number > highest_json_file_number:
               highest_json_file_number = file_number

      # Store data in the next available json file number
      file_name = str(highest_json_file_number + 1) + ".json"
      utils.json_write(ch_dir + file_name, data=to_store)

      # Save latest message timestamp.
      utils.json_write(ch_json_filepath, data=ch_json_data)
      return

   @classmethod
   def _message_dict(cls, msg):
      i = {}
      i["t"] = msg.timestamp # Datetime (must convert before storing!!!)
      i["i"] = msg.id # String
      i["a"] = msg.author.id # String
      i["c"] = msg.content # String
      i["h"] = msg.attachments # List of dictionaries.
      i["e"] = msg.embeds # List of dictionaries
      tmp = ""
      if not msg.edited_timestamp is None:
         tmp += "e" # for "edited"
      if msg.tts:
         tmp += "t"
      if msg.mention_everyone:
         tmp += "m"
      tmp += str(len(msg.mentions)) + "/" + str(len(msg.channel_mentions))
      i["f"] = tmp
      return i

   def _get_ch_dir(self, server_id, ch_id):
      return self._data_dir + server_id + "/" + ch_id + "/"

   def get_debugging_info(self):
      # buf = "**Currently buffered messages:**\n"
      # for (serv_id, serv_dict) in self._data.items():
      #    for (ch_id, ch_data) in serv_dict.items():
      #       ch = self._client.search_for_channel(ch_id, enablenamesearch=False, serverrestriction=None)
      #       buf += str(len(ch_data)) + " (#" + ch.name + ")\n"
      # return buf[:-1]
      buf = "In cache:\n"
      for (serv_id, serv_dict) in self._data.items():
         for (ch_id, ch_data) in serv_dict.items():
            ch = self._client.search_for_channel(ch_id, enablenamesearch=False, serverrestriction=None)
            strcount = 0
            for msg_dict in ch_data:
               if isinstance(msg_dict["t"], str):
                  strcount += 1
            buf += str(len(ch_data)) + " with " + str(strcount) + " str (#" + ch.name + ")\n"
      return buf

