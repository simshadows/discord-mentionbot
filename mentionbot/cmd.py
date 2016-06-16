import inspect
import enum
import abc
import collections

from . import utils, errors
from .helpnode import HelpNode
from .enums import PrivilegeLevel
from .servermodulewrapper import ServerModuleWrapper

###########################################################################################
# UTILITY FUNCTIONS #######################################################################
###########################################################################################

# Returns the appropriate function object from a dictionary of function objects filled
# by the "add()" decorator while also handling checks. As long as the dictionary has
# been filled correctly with properly decorated function objects, it is guaranteed to
# either return a working command function, or raise appropriate exceptions.
# 
# THROWS: UnknownCommandError - Thrown if cmd_name is not in the dictionary.
# THROWS: CommandPrivilegeError - Thrown if cmd_name is in the dictionary, but
#                                 privilege_level is not high enough to execute it.
async def get(cmd_dict, cmd_name, privilege_level):
   try:
      cmd_to_execute = cmd_dict[cmd_name]
      if privilege_level < (await cmd_to_execute.cmd_meta.node_min_priv()):
            raise errors.CommandPrivilegeError
      return cmd_to_execute
   except KeyError:
      raise errors.InvalidCommandArgumentsError

# Produces a help content string out of a dictionary of command functions.
async def summarise_commands(cmd_dict, privilege_level=None):
   # TODO: NOTHING IS ACTUALLY DONE WITH THE PRIVILEGE LEVEL YET.
   if privilege_level is None:
      privilege_level = Privilege_level.get_lowest_privilege()

   seen = set() # Seen CommandMeta objects
   cats_dict = collections.defaultdict(lambda: [])
   # cats_dict - Maps category names to lists of command help summaries.
   #             Those without categories are in the "" category.
   for (cmd_name, cmd_obj) in cmd_dict.items():
      node = cmd_obj.cmd_meta
      if node in seen: continue
      seen.add(node)
      cat_name = await node.node_category()
      # Compose the string to append to the list within the relevant category.
      buf = await node.get_help_summary(privilege_level)
      cats_dict[cat_name].append(buf)

   # Separate the no-category category. This will be dealt with separately.
   no_cat = cats_dict[""]
   del cats_dict[""]

   # Sort each category and put the category names into a list.
   cat_name_list = []
   for (cat_name, cat) in cats_dict.items():
      cat_name_list.append(cat_name)
      cat.sort(key=lambda e: e.lower())

   # Sort the category names
   cat_name_list.sort(key=lambda e: e.lower())

   # Put it all together
   buf = ""
   if len(no_cat) > 0:
      no_cat.sort(key=lambda e: e.lower())
      buf += "\n".join(no_cat)
   for cat_name in cat_name_list:
      buf += "\n\n**{}**\n".format(cat_name)
      buf += "\n".join(cats_dict[cat_name])
   return buf

# Produces a help content string out of a list of ServerModuleWrapper objects
# and CoreCommandsHelpPage objects.
async def summarise_server_modules(modules, privilege_level):
   assert isinstance(privilege_level, PrivilegeLevel)
   cats_dict = collections.defaultdict(lambda: [])
   # cats_dict - Maps category names to lists of module summaries.
   #             Those without categories are in the "" category.
   for module in modules:
      cat_name = await module.node_category()
      # Compose the string to append to the list within the relevant category.
      buf = await module.get_help_summary(privilege_level)
      if isinstance(module, ServerModuleWrapper):
         buf = buf.format(p="{p}", grp="{grp}" + module.module_cmd_aliases[0] + " ")
      cats_dict[cat_name].append(buf)

   # Separate the no-category category. This will be dealt with separately.
   no_cat = cats_dict[""]
   del cats_dict[""]

   # Sort each category and put the category names into a list.
   cat_name_list = []
   for (cat_name, cat) in cats_dict.items():
      cat_name_list.append(cat_name)
      cat.sort(key=lambda e: e.lower())

   # Sort the category names
   cat_name_list.sort(key=lambda e: e.lower())

   # Put it all together
   buf = ""
   if len(no_cat) > 0:
      no_cat.sort(key=lambda e: e.lower())
      buf += "\n".join(no_cat)
   for cat_name in cat_name_list:
      buf += "\n\n**{}**\n".format(cat_name)
      buf += "\n".join(cats_dict[cat_name])
   return buf

###########################################################################################
# FUNCTION DECORATORS #####################################################################
###########################################################################################

# IMPORTANT: Command function decorators must never wrap!
#            Wrapping functions may hide other decorated attributes.

# Decorator for adding commands to a dictionary.
# PARAMETER: cmd_dict - The dictionary in which the command is to be added to.
# PARAMETER: *cmd_names - List of names the command is to be mapped to.
# PARAMETER: default - (bool) If true, list the command as a default command.
# PARAMETER: top - (bool or list<str>) For defining top-level aliases.
#                  If False, command does not have any top-level aliases.
#                  If True, all of the aliases are also top-level aliases.
#                  If it's a string or a non-empty list of strings, then those
#                  strings are used as top-level aliases.
# PARAMETER: category - (str or None) For defining a category name, useful by
#                       certain HelpNode aggregators for organizing lines.
#                       If None, then no category.
#                       If a string, then that string is used as the category
#                       name.
# PARAMETER: minimum_privilege - A minimum privilege level normally required
#                                to use the command.
#                                (Implementation note: If minimum_privilege
#                                is None, then the default value in the
#                                CommandMeta object is kept.)
#     # THE FOLLOWING PARAMETER IS CURRENTLY STILL PLANNED AND THUS UNUSED.
#     # PARAMETER: help_pages - A CommandHelpPage object (or list of) in which the
#     #                         command is to be added to.
# Note: minimum_privilege is still used as 
def add(cmd_dict, *cmd_names, **kwargs):
   assert isinstance(cmd_dict, dict)

   # Get kwargs
   default = bool(kwargs.get("default", False))
   top_kwarg = kwargs.get("top", False)
   category = kwargs.get("category", None)
   minimum_privilege = kwargs.get("minimum_privilege", None)

   def function_decorator(function):
      _ensure_cmd_obj(function)
      function.cmd_meta.set_aliases(cmd_names)
      top = top_kwarg
      if isinstance(top, bool):
         if top:
            function.cmd_meta.set_top_aliases_existing()
      else:
         if isinstance(top, str):
            top = [top]
         function.cmd_meta.set_top_aliases_explicitly(list(top))
      if not category is None:
         assert isinstance(category, str)
         function.cmd_meta.set_help_category(category)
      if not minimum_privilege is None:
         assert isinstance(minimum_privilege, PrivilegeLevel)
         function.cmd_meta.set_min_priv(minimum_privilege_level)

      # Add the function to cmd_dict
      for cmd_name in cmd_names:
         assert isinstance(cmd_name, str)
         if cmd_name in cmd_dict:
            raise RuntimeError("Command with alias '{}' already exists.".format(cmd_name))
         cmd_dict[cmd_name] = function
      if default:
         if "" in cmd_dict:
            raise RuntimeError("A default command has already defined.")
         cmd_dict[""] = function
      return function
   return function_decorator

# Decorator adds an attribute named "privilege_gate" to a function object.
# This attribute is simply checked before execution.
def minimum_privilege(minimum_privilege_level):
   assert isinstance(minimum_privilege_level, PrivilegeLevel)
   def function_decorator(function):
      _ensure_cmd_obj(function)
      function.cmd_meta.set_min_priv(minimum_privilege_level)
      return function
   return function_decorator

# Decorator adds an attribute named "help_category" to a function object.
# This attribute is used when composing help messages, for grouping.
# When no category has been assigned (i.e. the decorator is not used),
# the composed help message will group the command along with all the
# other ungrouped commands.
def category(text):
   assert isinstance(text, str)
   def function_decorator(function):
      _ensure_cmd_obj(function)
      function.cmd_meta.set_help_category(text)
      return function
   return function_decorator

###########################################################################################
###########################################################################################
###########################################################################################

def _ensure_cmd_obj(function):
   if not hasattr(function, "cmd_meta"):
      function.cmd_meta = CommandMeta(function)
   return

class CommandMeta(HelpNode):
   """
   Stores information about a command.

   MOTIVATION

   The original implementation of command functions involved "duct taping" new
   attributes to command functions, with no clear organization of this. Not
   only is data neatness an issue, but the code to handle these command
   function objects has to explicitly check for the existence of these
   attributes, so data access is also an issue.

   CommandMeta is designed to tidy all of this up.
   """

   DEFAULT_HELP_STR = "`{cmd}`"

   class TopLevelAliasAction(enum.Enum):
      NO_TOP_LEVEL_ALIASES = 0
      USE_EXISTING_ALIASES = 1
      USE_NEW_ALIASES = 2

   def __init__(self, cmd_fn):
      self._cmd_fn = cmd_fn

      # Attributes for aliases
      self._aliases = None
      self._top_level_alias_action = self.TopLevelAliasAction.NO_TOP_LEVEL_ALIASES
      self._top_level_aliases = None

      # Attributes for privilege levels
      self._minimum_privilege = PrivilegeLevel.get_lowest_privilege()

      # Attributes for leaf help content
      self._help_detail = None

      # Attributes for module help content
      self._help_category = "" # No category by default
      self._help_summary = None

      # Parsing the docstring to get _help_detail and _help_summary
      docstr = inspect.getdoc(cmd_fn)
      if docstr is None or len(docstr) == 0:
         # Give the default value.
         self._help_detail = self.DEFAULT_HELP_STR
         self._help_summary = self.DEFAULT_HELP_STR
      else:
         docstr = docstr.strip()
         self._help_detail = docstr # TODO: Is it necessary?
         # Summaries include the first few lines of the string up until the first
         # empty line.
         lines = []
         for line in docstr.splitlines():
            if len(line) == 0:
               break
            lines.append(line)
         assert len(lines) > 0
         assert len(lines[0].strip()) > 0
         self._help_summary = "\n".join(lines)
      return

   def set_aliases(self, string_list):
      self._aliases = list(string_list)
      return

   def set_min_priv(self, privilege_level):
      self._minimum_privilege = privilege_level
      return

   def set_help_category(self, string):
      assert isinstance(string, str) and len(string) > 0
      self._help_category = string
      return

   # Make top-level aliases match the existing aliases.
   def set_top_aliases_existing(self):
      self._top_level_alias_action = self.TopLevelAliasAction.USE_EXISTING_ALIASES
      return

   # Sets top-level aliases explicitly.
   def set_top_aliases_explicitly(self, str_list):
      self._top_level_alias_action = self.TopLevelAliasAction.USE_NEW_ALIASES
      self._top_level_aliases = list(str_list)
      return

   def get_aliases(self):
      return list(self._aliases)

   def get_top_aliases(self):
      if self._top_level_alias_action is self.TopLevelAliasAction.USE_EXISTING_ALIASES:
         return list(self._aliases)
      elif self._top_level_alias_action is self.TopLevelAliasAction.USE_NEW_ALIASES:
         return list(self._top_level_aliases)
      else:
         return None

   ################################
   ### HelpNode Implementations ###
   ################################
   
   async def get_help_detail(self, locator_string, entry_string, privilege_level):
      assert isinstance(locator_string, str) and isinstance(entry_string, str)
      assert isinstance(privilege_level, PrivilegeLevel)
      buf = None
      if self._top_level_alias_action is self.TopLevelAliasAction.NO_TOP_LEVEL_ALIASES:
         buf = self._help_detail.format(p="{p}", grp="{grp}", cmd="{p}{grp}" + self._aliases[0])
      else:
         buf = self._help_detail.format(p="{p}", grp="{grp}", cmd="{p}" + self.get_top_aliases()[0])
      buf += "\n\n"
      buf0 = ""
      if not self._minimum_privilege is PrivilegeLevel.get_lowest_privilege():
         buf0 = "**Required privilege level:** "
         buf0 += self._minimum_privilege.get_commonname()
      if (not privilege_level is None) and (privilege_level < self._minimum_privilege):
         buf += "**You do not have the correct privilege level to use this command.**\n"
         buf += buf0 + "\n**Your privilege level:** "
         buf += privilege_level.get_commonname()
      else:
         buf = (buf + buf0).strip()
      return buf

   async def get_help_summary(self, privilege_level):
      assert isinstance(privilege_level, PrivilegeLevel)
      if self._top_level_alias_action is self.TopLevelAliasAction.NO_TOP_LEVEL_ALIASES:
         return self._help_summary.format(p="{p}", grp="{grp}", cmd="{p}{grp}" + self._aliases[0])
      else:
         return self._help_summary.format(p="{p}", grp="{grp}", cmd="{p}" + self.get_top_aliases()[0])

   async def node_min_priv(self):
      return self._minimum_privilege

   async def node_category(self):
      return self._help_category
