import asyncio
from copy import deepcopy

import discord

from . import utils

class ServerModuleResources:

   def __init__(self, module_name, server_bot_instance, module_wrapper):
      self._sbi = server_bot_instance
      self._client = server_bot_instance.client
      self._module_wrapper = module_wrapper

      self._server = self._sbi.server
      self._data_directory = self._sbi.data_directory + utils.remove_whitespace("m-" + module_name) + "/"
      self._shared_directory = self._sbi.shared_directory + utils.remove_whitespace("m-" + module_name) + "/"
      
      self._settings_filepath = self._data_directory + "settings.json"
      self._shared_settings_filepath = self._shared_directory + "settings.json"

      # Ensure the data and shared directories exist.
      utils.mkdir_recursive(self._data_directory)
      utils.mkdir_recursive(self._shared_directory)
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
   def shared_directory(self):
       return self._shared_directory
   
   @property
   def cmd_prefix(self):
      return self._sbi.cmd_prefix

   @property
   def module_cmd_aliases(self):
      return list(self._module_wrapper.module_cmd_aliases)

   def get_config_ini_copy(self):
      return self._client.get_config_ini_copy()
   
   # Get the server to process text again.
   async def server_process_text(self, substr, msg):
      return await self._sbi.process_text(substr, msg)

   # Get module settings.
   # If no settings are found and no default was supplied, None is returned.
   # If no settings were found and a default was supplied, then a deepcopy
   # of the default object is returned.
   def get_settings(self, default=None):
      try:
         return utils.json_read(self._settings_filepath)
      except FileNotFoundError:
         if default is None:
            return None
         else:
            return deepcopy(default)

   # Save module settings.
   def save_settings(self, data):
      utils.json_write(self._settings_filepath, data=data)
      return

   # Similar to get_settings, but shared across all instances of the module.
   def get_shared_settings(self, default=None):
      try:
         return utils.json_read(self._shared_settings_filepath)
      except FileNotFoundError:
         if default is None:
            return None
         else:
            return deepcopy(default)

   def save_shared_settings(self, data):
      utils.json_write(self._shared_settings_filepath, data=data)
      return

   def message_cache_read(self, server_id, ch_id):
      return self.client.message_cache_read(server_id, ch_id)

   async def start_nonreturning_coro(self, coro):
      await self._module_wrapper.start_user_nonreturning_coro(coro)
      return

   ####################
   # Shortcut-methods #
   ####################

   @property
   def botowner_ID(self):
      return self._sbi.client.get_bot_owner_id()

   @property
   def me_ID(self):
      return self._sbi.client.user.id

   #########
   # Flags #
   #########

   # Suppresses the auto-killing of the module.
   # Default value is False.
   #
   # IMPORTANT: Only set this if suppressing auto-kill is safe to do so.
   #            Depending on the operation, errors may cause irreversible
   #            and serious damage to server or bot data. Auto-kill is a way
   #            to minimize further damage, hence the default value of False.
   def suppress_autokill(self, value):
      self._module_wrapper.set_suppress_autokill(bool(value))
      return
   
