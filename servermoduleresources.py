import asyncio
import copy

import discord

import utils

class ServerModuleResources:

   def __init__(self, module_name, server_bot_instance):
      self._sbi = server_bot_instance

      self._server = self._sbi.server
      self._data_directory = self._sbi.data_directory + utils.remove_whitespace("m-" + module_name) + "/"
      self._shared_directory = self._sbi.shared_directory + utils.remove_whitespace("m-" + module_name) + "/"
      
      self._settings_filepath = self._data_directory + "settings.json"
      self._shared_settings_filepath = self._shared_directory + "settings.json"
      return

   @property
   def client(self):
       return self._sbi.client

   @property
   def server(self):
      return self._server

   @property
   def data_directory(self):
       return self._data_directory
   
   @property
   def cmd_prefix(self):
      return self._sbi.cmd_prefix
   
   # Get the server to process text again.
   async def process_text(self, substr, msg):
      return await self._sbi.process_text(substr, msg)

   # Get module settings.
   # Returns None if no settings were found.
   def get_settings(self):
      try:
         return utils.json_read(self._settings_filepath)
      except FileNotFoundError:
         return None

   # Save module settings.
   def save_settings(self, data):
      utils.json_write(self._settings_filepath, data=data)
      return

   def get_shared_settings(self):
      try:
         return utils.json_read(self._shared_settings_filepath)
      except FileNotFoundError:
         return None

   def save_shared_settings(self, data):
      utils.json_write(self._shared_settings_filepath, data=data)
      return

