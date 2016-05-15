import inspect
import enum

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
      if hasattr(cmd_to_execute, "minimum_privilege"):
         if privilege_level < cmd_to_execute.minimum_privilege:
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
         if hasattr(cmd_obj, "minimum_privilege"):
            if privilege_level < cmd_obj.minimum_privilege:
               continue
         seen_set.add(cmd_obj)
         help_str = get_help_summary(cmd_obj)
         if len(help_str) != 0:
            cat_name = None
            if hasattr(cmd_obj, "help_category"):
               cat_name = cmd_obj.help_category
            else:
               cat_name = ""
            cat_buf = None
            try:
               cat_buf = cats_dict[cat_name]
            except KeyError:
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
   docstr = inspect.getdoc(cmd_obj)
   if docstr is None or len(docstr) == 0:
      return ""
   kwargs = {
      "cmd": "{p}{b}" + cmd_obj.cmd_names[0],
      "bc": "{p}{b}",
      "p": "{p}",
      "b": "{b}",
      "c": cmd_obj.cmd_names[0],
   }
   return docstr.split("\n", 1)[0].format(**kwargs)

def get_help_detail(cmd_obj):
   docstr = inspect.getdoc(cmd_obj)
   if docstr is None or len(docstr) == 0:
      return ""
   else:
      return docstr

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
      function.cmd_names = cmd_names
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
   def function_decorator(function):
      function.minimum_privilege = minimum_privilege_level
      return function
   return function_decorator

# Decorator adds an attribute named "help_category" to a function object.
# This attribute is used when composing help messages, for grouping.
# When no category has been assigned (i.e. the decorator is not used),
# the composed help message will group the command along with all the
# other ungrouped commands.
def category(text):
   def function_decorator(function):
      function.help_category = text
      return function
   return function_decorator

# Defines top-level aliases of the command.
def top_level_alias(*aliases):
   def function_decorator(function):
      if len(aliases) == 0:
         # Instructs other components to use the existing aliases as top-level aliases.
         function.top_level_alias_type = TopLevelAliasAction.USE_EXISTING_ALIASES
         function.top_level_aliases = None
      else:
         function.top_level_alias_type = TopLevelAliasAction.USE_NEW_ALIASES
         function.top_level_aliases = list(aliases)
      return function
   return function_decorator

class TopLevelAliasAction(enum.Enum):
   USE_EXISTING_ALIASES = 0
   USE_NEW_ALIASES = 1
