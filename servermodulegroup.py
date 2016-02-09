import re

import utils
import errors

class ServerModuleGroup:

   # PRECONDITION: initial_modules is a list of unique modules.
   # PRECONDITION: initial_modules is already sorted by desired appearance
   #               when getting summary help content.
   def __init__(self, initial_modules=[]):
      # Initialize our module collections.
      # Two collections for efficiency (dict for calling commands, list for iterating).
      self._modules_cmd_dict = {}
      self._modules_list = initial_modules
      for module in self._modules_list:
         for cmd_name in module.cmd_names:
            self._modules_cmd_dict[cmd_name] = module
      return

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      for module in self._modules_list:
         content = await module.msg_preprocessor(content, msg, default_cmd_prefix)
      return content

   async def on_message(self, msg):
      for module in self._modules_list:
         await module.on_message(msg)
      return

   async def process_cmd(self, substr, msg, privilegelevel=0):
      (left, right) = utils.separate_left_word(substr)
      try:
         await self._modules_cmd_dict[left].process_cmd(right, msg, privilegelevel)
      except KeyError:
         raise errors.UnknownCommandError
      return

   # Module is referenced by its module name.
   def module_is_installed(self, module_name):
      for module in self._modules_list:
         if module.MODULE_NAME == module_name:
            return True
      return False

   # PRECONDITION: Module isn't already installed.
   #               This means duplicates are allowed in the same ServerModuleGroup,
   #               but its use often requires
   async def add_server_module(self, new_module):
      self._modules_list.append(new_module)
      for cmd_name in new_module.cmd_names:
         self._modules_cmd_dict[cmd_name] = new_module

   # Installs the module referenced by its base command name.
   # PRECONDITION: Module is currently installed.
   async def remove_server_module(self, module_name):
      module_to_remove = None
      for module in self._modules_list:
         if module.MODULE_NAME == module_name:
            module_to_remove = module
            break
      for cmd_name in module_to_remove.cmd_names:
         del self._modules_cmd_dict[cmd_name]
      self._modules_list.remove(module_to_remove)

   # Returns a string containing help message content.
   #     May return an empty string if no help content.
   # If presenting a summary, the returned string will lack
   # a "title", so it might be necessary to do the following:
   #     buf = "**HELP CONTENT:**\n" + modules.get_help_content()
   # This also only presents help content for modules it maintains.
   # If ServerBotInstance has additional functionality, it should append it
   # to the returned string. Depends on what ServerBotInstance wants to do.
   # PRECONDITION: The ServerModuleGroup object is filled with modules.
   def get_help_content(self, substr, cmd_prefix, privilege_level=0):
      if substr == "":
         # This serves a summary of commands.
         buf = ""
         for module in self._modules_list:
            buf += module.get_help_summary(cmd_prefix, privilegelevel=privilege_level) + "\n"
         buf = buf[:-1] # Remove extra newline.
      else:
         # This serves detailed help content for a module.
         # It passes the arguments in as well to allow modules to display
         # different help content as they wish. How this is handled is
         # all up to the module.
         (left, right) = utils.separate_left_word(substr)
         try:
            buf = self._modules_cmd_dict[left].get_help_detail(right, cmd_prefix, privilegelevel=privilege_level)
         except KeyError:
            raise errors.NoHelpContentExists
      return buf

   # Returns list of all installed modules in this instance.
   # RETURNS: A list of tuples, each tuple in the format:
   #          (module_name, module_short_description)
   def get_module_info(self):
      names = []
      for module in self._modules_list:
         names.append((module.MODULE_NAME, module.MODULE_SHORT_DESCRIPTION))
      return names


# servermodules.mentions.notify.MentionNotifyModule(client, enabled=self.INIT_MENTIONS_NOTIFY_ENABLED),
# servermodules.mentions.search.MentionSearchModule(client),
# servermodules.mentions.summary.MentionSummaryModule(client)


