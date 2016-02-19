import asyncio
import re
import datetime

import discord
import dateutil.parser

import utils

ARBITRARILY_LARGE_NUMBER = 10000000000000

class MessageCache:
   _SECRET_TOKEN = utils.SecretToken()

   _CH_JSON_FILENAME = "channel.json"

   @classmethod
   async def get_instance(cls, client, cache_directory):
      inst = cls(cls._SECRET_TOKEN)
      inst._client = client
      inst._data_dir = cache_directory + "messagecache/"
      
      inst._data = {}
      # A tree of dictionaries in this arrangement:
      # server_id -> channel_id -> list of messages stored in tuples
      # Each message entry is a tuple.

      print("Caching messages...")
      print("This will take a while if a lot of messages are being read.")
      await inst._refresh_buffers()
      
      print("DEBUGGING MESSAGE CACHE:")
      for (serv_id, serv_dict) in inst._data.items():
         for (ch_id, ch_data) in serv_dict.items():
            ch = inst._client.search_for_channel(ch_id, enablenamesearch=False, serverrestriction=None)
            print("#" + ch.name + " has len " + str(len(ch_data)))
      print("DEBUGGING MESSAGE CACHE DONE!")

      return inst

   def __init__(self, token):
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
      return

   def record_message(self):
      pass

   async def _refresh_buffers(self):
      for server in self._client.servers:
         server_dict = None
         try:
            server_dict = self._data[server.id]
         except KeyError:
            server_dict = {}
            self._data[server.id] = server_dict

         for ch in server.channels:
            if ch.type is discord.ChannelType.voice:
               continue
            print("FOUND CHANNEL " + ch.name)

            # TODO: Rename these variable names.
            ch_dir = self._get_ch_dir(server.id, ch.id)
            ch_json_filename = ch_dir + self._CH_JSON_FILENAME
            
            ch_json_data = None
            try:
               ch_json_data = utils.json_read(ch_json_filename)
            except FileNotFoundError:
               ch_json_data = {}

            ch_stored_timestamp = None
            try:
               ch_stored_timestamp = dateutil.parser.parse(ch_json_data["last message timestamp"])
            except KeyError:
               ch_stored_timestamp = datetime.datetime(datetime.MINYEAR, 1, 1)
               ch_json_data["last message timestamp"] = ch_stored_timestamp.isoformat()
               utils.json_write(ch_json_filename, data=ch_json_data)

            # This will now fill a buffer all messages of a channel.
            # TODO: Consider filling a file, then reading off the file.
            msg_buffer = []
            try:
               async for msg in self._client.logs_from(ch, limit=ARBITRARILY_LARGE_NUMBER):
                  if msg.timestamp <= ch_stored_timestamp:
                     break
                  msg_buffer.insert(0, self._message_dict(msg))
            except discord.errors.Forbidden:
               pass

            server_dict[ch.id] = msg_buffer

      return

   @classmethod
   def _message_dict(cls, msg):
      i = {}
      i["ti"] = msg.timestamp # Datetime
      i["id"] = msg.id # String
      i["au"] = msg.author.id # String
      i["co"] = msg.content # String
      i["at"] = msg.attachments # List of dictionaries.
      i["em"] = msg.embeds # List of dictionaries
      tmp = ""
      if not msg.edited_timestamp is None:
         tmp += "e" # for "edited"
      if msg.tts:
         tmp += "t"
      if msg.mention_everyone:
         tmp += "m"
      tmp += str(len(msg.mentions)) + "/" + str(len(msg.channel_mentions))
      i["fl"] = tmp
      return i

   def _get_ch_dir(self, server_id, ch_id):
      return self._data_dir + server_id + "/" + ch_id + "/"



