import inspect
import enum
import abc

from . import utils, errors
from .enums import PrivilegeLevel

# Help message string formatting arguments:
#     Everywhere:
#        "{cmd}" -> "{bc}{c}" -> "{p}{b}{c}"
#           "{cmd}", "{c}", and "{bc}"->"{p}{b}" are evaluated in get_help_summary().
#           "{b}" is evaluated where the help summary is composed from the command
#              objects themselves.
#           "{p}" is evaluated last, before sending off the final string.
#     In modules:
#        "{modhelp}" -> "{p}help {mod}"
#           "{modhelp}" and "{mod}" are evaluated where the help summary is composed
#              from the command objects themselves, in a module method.
#           "{p}" is evaluated last, before sending off the final string.

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
def get(cmd_dict, cmd_name, privilege_level):
   try:
      cmd_to_execute = cmd_dict[cmd_name]
      if privilege_level < cmd_to_execute.cmd_meta.get_min_priv():
            raise errors.CommandPrivilegeError
      return cmd_to_execute
   except KeyError:
      raise errors.InvalidCommandArgumentsError

def compose_help_summary(cmd_dict, privilege_level):
   # Make separate help strings for each group.
   seen_set = set()
   cats_dict = {} # FORMAT: category name string -> help content string
   for (cmd_name, cmd_obj) in cmd_dict.items():
      if not cmd_obj in seen_set:
         if privilege_level < cmd_obj.cmd_meta.get_min_priv():
            continue
         seen_set.add(cmd_obj)
         help_str = get_help_summary(cmd_obj)
         if len(help_str) != 0:
            cat_name = cmd_obj.cmd_meta.get_help_summary()[1] # TODO: Messy...
            if cat_name is None:
               cat_name = ""
            cat_buf = None
            if cat_name in cats_dict:
               cat_buf = cats_dict[cat_name]
            else:
               cat_buf = ""
            cats_dict[cat_name] = cat_buf + help_str + "\n"

   # Sort each category and put into a list.
   cats_list = [] # FORMAT: [(cat_name, cat_buf)]
   no_cat_buf = None # String for commands with no/blank category.
   for (cat_name, cat_buf) in cats_dict.items():
      cat_buf = "\n".join(sorted(cat_buf.splitlines(), key=lambda e: e.lower()))
      if len(cat_name) == 0:
         no_cat_buf = cat_buf
      else:
         cats_list.append((cat_name, cat_buf))
   
   # Sort the categories list
   if len(cats_list) != 0:
      cats_list = sorted(cats_list, key=lambda e: e[0].lower())

   # Put together and return help content string.
   buf = None
   if not no_cat_buf is None:
      buf = no_cat_buf
   else:
      buf = ""
   for (cat_name, cat_buf) in cats_list:
      buf += "\n\n**" + cat_name + "**:\n" + cat_buf
   if no_cat_buf is None:
      return buf[2:] # Strip off first two newlines.
   else:
      return buf

# This method is not normally used anywhere other than compose_help_summary().
# This method also processes "{cmd}" -> "{bc}{c}" and substitutes in the
# value of "{c}".
def get_help_summary(cmd_obj):
   kwargs = {
      "cmd": "{p}{b}" + cmd_obj.cmd_meta.get_aliases()[0],
      "bc": "{p}{b}",
      "p": "{p}",
      "b": "{b}",
      "c": cmd_obj.cmd_meta.get_aliases()[0],
   }
   return cmd_obj.cmd_meta.get_help_summary()[0].format(**kwargs)

def get_help_detail(cmd_obj):
   return cmd_obj.cmd_meta.get_help_detail()

# Carries out "{modhelp}" -> "{p}help {mod}" evaluation, while also
# substituting "{mod}".
def format_mod_evaluate(content_str, *, mod=None):
   return content_str.format(modhelp="{p}help " + mod, mod=mod, p="{p}")

###########################################################################################
# FUNCTION DECORATORS #####################################################################
###########################################################################################

# IMPORTANT: Command function decorators must never wrap!
#            Wrapping functions may hide other decorated attributes.

# Decorator for adding commands to a dictionary.
# PARAMETER: dict - The dictionary in which the command is to be added to.
# PARAMETER: *cmd_names - List of names the command is to be mapped to.
def add(cmd_dict, *cmd_names, default=False):
   def function_decorator(function):
      _ensure_cmd_obj(function)
      function.cmd_meta.set_aliases(cmd_names)

      # Add the function to cmd_dict
      for cmd_name in cmd_names:
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
   assert type(minimum_privilege_level) is PrivilegeLevel
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
   assert type(text) is str
   def function_decorator(function):
      _ensure_cmd_obj(function)
      function.cmd_meta.set_help_category(text)
      return function
   return function_decorator

# Defines top-level aliases of the command.
def top_level_alias(*aliases):
   def function_decorator(function):
      _ensure_cmd_obj(function)
      if len(aliases) == 0:
         function.cmd_meta.set_top_aliases_existing()
      else:
         function.cmd_meta.set_top_aliases_explicitly(aliases)
      return function
   return function_decorator

###########################################################################################
###########################################################################################
###########################################################################################

def _ensure_cmd_obj(function):
   if not hasattr(function, "cmd_meta"):
      function.cmd_meta = CommandMeta(function)
   return

class HelpNode(abc.ABC):
   """
   This defines an object that can be referenced as a node in a directed graph
   of help node objects.

   HelpNode implementors:
      - ServerModuleGroup (as this is an entrypoint)
      - ServerModuleWrapper
      - CommandMeta
   """

   # Get help content specified by the locator string.
   # RETURNS: Either a string containing help content, or None if no help
   #          content exists.
   def get_node(self, locator_string):
      path = locator_string.split()
      curr = self
      for location in path:
         curr = curr.get_next_node(location)
         if curr is None:
            break
      return curr

   # Get the node's detail help content as a string.
   # POSTCONDITION: Will always produce help content.
   #                This implies no NoneTypes or empty strings.
   @abc.abstractmethod
   def get_help_detail(self):
      raise NotImplementedError

   # Get the node's summary help content as a string.
   # POSTCONDITION: Will always produce help content.
   #                This implies no NoneTypes or empty strings.
   # RETURNS: Tuple with two items:
   #              [0]: The help summary content. Guaranteed to 
   #              [1]: A "category" string that may help nodes aggregating
   #                   other help nodes to organize their help content.
   #                   Value is None if there is no catgory.
   @abc.abstractmethod
   def get_help_summary(self):
      raise NotImplementedError

   # Get the next IHelpNode object, given a locator string specifying this next
   # object. If no such object exists, returns None.
   # PRECONDITION: The locator string only specifies a "single traversal" to
   #               the next node, i.e. no spaces.
   @abc.abstractmethod
   def get_next_node(self, locator_string):
      # Please insert this assert in implementations.
      assert not " " in locator_string
      raise NotImplementedError


class CommandMeta(HelpNode):
   """
   Stores information about a command.

   MOTIVATION

   The original implementation of command functions involved "duct taping" new
   attributes to command functions, with no clear organization of this. Not
   only is data neatness an issue, but the code to handle these command
   function objects has to explicitly check for the existence of these
   attributes, so data access is also an issue.

   CommandSpecification is designed to tidy all of this up.
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
      self._help_category = None
      self._help_summary = None

      # Parsing the docstring to get _help_detail and _help_summary
      docstr = inspect.getdoc(cmd_fn)
      if docstr is None or len(docstr) == 0:
         # Give the default value.
         self._help_detail = self._help_summary = self.DEFAULT_HELP_STR
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
      assert type(string) is str and len(string) > 0
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

   def get_min_priv(self):
      return self._minimum_privilege

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
   
   def get_help_detail(self):
      return self._help_detail

   def get_help_summary(self):
      cat = self._help_category
      assert (type(cat) is str and len(cat) > 0) or cat is None
      return (self._help_summary, cat)

   def get_next_node(self, locator_string):
      assert not " " in locator_string
      return None # This is a leaf node.
