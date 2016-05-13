import re

from . import utils, errors

class ServerModuleGroup:

   # TODO: Implement more efficient data structures. Too much linear searching is going on.

   # PRECONDITION: initial_modules is a list of unique modules.
   # PRECONDITION: initial_modules is already sorted by desired appearance
   #               when getting summary help content.
   def __init__(self, initial_modules=[]):
      # Initialize our module collections.
      # Two collections for efficiency (dict for calling commands, list for iterating).
      self._modules_cmd_dict = {}
      self._modules_list = initial_modules
      for module in self._modules_list:
         for cmd_name in module.all_cmd_aliases:
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

   async def process_cmd(self, substr, msg, privilege_level, silentfail=False):
      (left, right) = utils.separate_left_word(substr)
      try:
         await self._modules_cmd_dict[left].process_cmd(right, msg, privilege_level, left)
      except KeyError:
         if silentfail:
            raise errors.SilentUnknownCommandError
         else:
            raise errors.UnknownCommandError
      return

   # Module is referenced by its module name.
   def module_is_installed(self, module_name):
      for module in self._modules_list:
         if module.module_name == module_name:
            return True
      return False

   # PRECONDITION: Module isn't already installed.
   #               This means duplicates are allowed in the same ServerModuleGroup,
   #               but its use often requires
   async def add_server_module(self, new_module):
      self._modules_list.append(new_module)
      for cmd_name in new_module.all_cmd_aliases:
         self._modules_cmd_dict[cmd_name] = new_module

   # Installs the module referenced by its base command name.
   # PRECONDITION: Module is currently installed.
   async def remove_server_module(self, module_name):
      module_to_remove = None
      for module in self._modules_list:
         if module.module_name == module_name:
            module_to_remove = module
            break
      for cmd_name in module_to_remove.all_cmd_aliases:
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
   def get_help_content(self, substr, privilege_level):
      if substr == "":
         # This serves a summary of commands.
         buf = ""
         for module in self._modules_list:
            content = module.get_help_summary(privilege_level)
            if content != "":
               buf += content + "\n"
         buf = buf[:-1] # Remove extra newline.
      else:
         # This serves detailed help content for a module.
         # It passes the arguments in as well to allow modules to display
         # different help content as they wish. How this is handled is
         # all up to the module.
         (left, right) = utils.separate_left_word(substr)
         try:
            content = self._modules_cmd_dict[left].get_help_detail(right, privilege_level)
            if content == "":
               raise errors.NoHelpContentExists
            buf = content
         except KeyError:
            raise errors.NoHelpContentExists
      return buf

   # Returns list of all installed modules in this instance.
   # RETURNS: A list of tuples, each tuple in the format:
   #          (module_name, module_short_description, is_active)
   def gen_module_info(self):
      for module in self._modules_list:
         yield (module.module_name, module.module_short_description, module.is_active())

   # PRECONDITION: module_is_installed(module_name)
   def module_is_active(self, module_name):
      for module in self._modules_list:
         if module.module_name == module_name:
            return module.is_active()
      raise RuntimeError("No such server module exists.")

   # PRECONDITION: module_is_installed(module_name)
   async def activate_module(self, module_name):
      for module in self._modules_list:
         if module.module_name == module_name:
            await module.activate()
            return
      raise RuntimeError("No such server module exists.")

   # PRECONDITION: module_is_installed(module_name)
   async def kill_module(self, module_name):
      for module in self._modules_list:
         if module.module_name == module_name:
            await module.kill()
            return
      raise RuntimeError("No such server module exists.")



# servermodules.mentions.notify.MentionNotifyModule(client, enabled=self.INIT_MENTIONS_NOTIFY_ENABLED),
# servermodules.mentions.search.MentionSearchModule(client),
# servermodules.mentions.summary.MentionSummaryModule(client)


