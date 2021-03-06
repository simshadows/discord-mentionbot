import re

from . import utils, errors, cmd
from .helpnode import HelpNode
from .enums import PrivilegeLevel

class ServerModuleGroup(HelpNode):

   # TODO: Implement more efficient data structures. Too much linear searching is going on.

   # PRECONDITION: initial_modules is a list of unique modules.
   # PRECONDITION: initial_modules is already sorted by desired appearance
   #               when getting summary help content.
   def __init__(self, initial_modules=[], core_help_pages=[]):
      # Initialize our module collections.
      # Two collections for efficiency (dict for calling commands, list for iterating).
      self._modules_cmd_dict = {}
      self._modules_list = initial_modules
      for module in self._modules_list:
         for cmd_name in module.all_cmd_aliases:
            self._modules_cmd_dict[cmd_name] = module
      self._core_pages_dict = {}
      self._core_pages_list = list(core_help_pages)
      for help_page in self._core_pages_list:
         for alias in help_page.get_all_aliases():
            self._core_pages_dict[alias] = help_page
      return

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      for module in self._modules_list:
         content = await module.msg_preprocessor(content, msg, default_cmd_prefix)
      return content

   async def on_message(self, msg, privilege_level):
      for module in self._modules_list:
         await module.on_message(msg, privilege_level)
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

   async def on_member_join(self, member):
      for module in self._modules_list:
         await module.on_member_join(member)
      return

   async def on_member_remove(self, member):
      for module in self._modules_list:
         await module.on_member_remove(member)
      return

   async def on_member_ban(self, member):
      for module in self._modules_list:
         await module.on_member_ban(member)
      return

   async def on_member_unban(self, user):
      for module in self._modules_list:
         await module.on_member_unban(user)
      return

   async def on_member_update(self, before, after):
      for module in self._modules_list:
         await module.on_member_update(before, after)
      return

   # Like the original get_extra_user_info method, except the tuple's
   # two fields are lists. Field 1 is a list of field 1 content from the
   # original method, and similarly with field 2.
   async def get_extra_user_info(self, member):
      ret0 = []
      ret1 = []
      for module in self._modules_list:
         info_tuple = await module.get_extra_user_info(member)
         if not info_tuple is None:
            # TODO: Are these asserts redundant?
            assert isinstance(info_tuple, tuple)
            assert len(info_tuple) == 2
            if not info_tuple[0] is None:
               assert isinstance(info_tuple[0], str)
               ret0.append(info_tuple[0])
            if not info_tuple[1] is None:
               assert isinstance(info_tuple[1], str)
               ret1.append(info_tuple[1])
      ret0.sort(key=lambda x: x.lower())
      ret1.sort(key=lambda x: x.lower())
      return (ret0, ret1)

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
         if cmd_name in self._modules_cmd_dict:
            print("WARNING: Module with alias '{}' already exists.".format(cmd_name))
         self._modules_cmd_dict[cmd_name] = new_module

   # Installs the module referenced by its base command name.
   # PRECONDITION: Module is currently installed.
   async def remove_server_module(self, module_name):
      module_to_remove = None
      for module in self._modules_list:
         if module.module_name == module_name:
            module_to_remove = module
            break
      await module_to_remove.kill()
      for cmd_name in module_to_remove.all_cmd_aliases:
         del self._modules_cmd_dict[cmd_name]
      self._modules_list.remove(module_to_remove)

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

   ################################
   ### HelpNode Implementations ###
   ################################

   async def get_help_detail(self, locator_string, entry_string, privilege_level):
      assert isinstance(locator_string, str) and isinstance(entry_string, str)
      assert isinstance(privilege_level, PrivilegeLevel)
      buf = None
      if locator_string is "":
         # Serve module help content.
         buf = ""
         if len(self._core_pages_list) > 0:
            buf += await cmd.summarise_server_modules(self._core_pages_list, privilege_level)
            buf += "\n\n"
         buf += await cmd.summarise_server_modules(self._modules_list, privilege_level)
      else:
         # Get the next node's help content.
         (left, right) = utils.separate_left_word(locator_string)
         if left in self._core_pages_dict:
            buf = await self._core_pages_dict[left].get_help_detail(right, left, privilege_level)
            if not buf is None:
               buf = buf.format(p="{p}", grp="")
         if left in self._modules_cmd_dict:
            buf = await self._modules_cmd_dict[left].get_help_detail(right, left, privilege_level)
            if not buf is None:
               buf = buf.format(p="{p}", grp="{grp}" + left + " ")
      return buf

   async def get_help_summary(self, privilege_level):
      assert isinstance(privilege_level, PrivilegeLevel)
      return "ServerModuleGroup objects have no help summary yet."

   async def node_min_priv(self):
      return PrivilegeLevel.get_lowest_privilege()

   async def node_category(self):
      return ""
