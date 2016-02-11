import copy

# import jsonschema

import utils

class ServerPersistentStorage:

   # Note: "Server Name" is not really a data storage pair.
   #       Its purpose is for human convenience, making it immediately
   #       obvious what the server is when reading the json file.
   # IMPORTANT: Changes to the data structure will need to be
   #            applied 
   DEFAULT_SETTINGS = {
      "Server Name": "",
      "Installed Modules": [
         "Basic Information",
         "Mentions",
         "Random",
         "WolframAlpha",
      ],
   }

   # TODO: Figure out how schemas work.
   # SETTINGS_JSONSCHEMA = {
   #    "title": "Server Settings",
   #    "properties": {
   #       "Server Name": "string",
   #       "Installed Modules": [
   #          "string",
   #       ],
   #    },
   #    "required": [
   #       "Server Name",
   #       "Installed Modules",
   #    ],
   # }

   def __init__(self, settings_filepath, server):
      self._server = server
      self._settings_filepath = settings_filepath
      return

   def get_server_settings(self):
      try:
         data = utils.json_read(self._settings_filepath)
      except FileNotFoundError:
         data = copy.deepcopy(self.DEFAULT_SETTINGS)
         utils.json_write(self._settings_filepath, data=data)
      # Update server name.
      if data["Server Name"] != self._server.name:
         data["Server Name"] = self._server.name
         utils.json_write(self._settings_filepath, data=data)
      # TODO: Add additional data verification with jsonschema
      return data

   def save_server_settings(self, data):
      utils.json_write(self._settings_filepath, data=data)
      return

   # ALL METHODS BELOW ONLY MANIPULATE PERSISTENT STORAGE
   # AND DON'T CHECK FOR EXTERNAL CONSISTENCY.
   # E.g. you can add any module name you wish.

   def add_module(self, module_name):
      data = self.get_server_settings()
      data["Installed Modules"].append(module_name)
      self.save_server_settings(data)
      return

   def remove_module(self, module_name):
      data = self.get_server_settings()
      data["Installed Modules"].remove(module_name)
      self.save_server_settings(data)
      return







