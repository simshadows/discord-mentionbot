import inspect

import utils
from enums import PrivilegeLevel
import errors

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

# This should no
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
def add(cmd_dict, *cmd_names):
   def function_decorator(function):
      function.cmd_names = cmd_names
      for cmd_name in cmd_names:
         cmd_dict[cmd_name] = function
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

def preprocess(cmd_preprocessor_factory, cmd_name=None):
   def function_decorator(function):
      def preprocessor_setup(cmd_preprocessor, module_cmd_name):
         input_cmds = None
         if cmd_name is None:
            input_cmds = function.cmd_names
         else:
            input_cmds = [cmd_name]
         output_cmd = module_cmd_name + " " + function.cmd_names[0]
         for input_cmd in input_cmds:
            cmd_preprocessor.add_transformation(input_cmd, output_cmd)
         return
      cmd_preprocessor_factory.add_setup_function(preprocessor_setup)
      return function
   return function_decorator

###########################################################################################
# CMD PREPROCESSOR CLASS AND FACTORY ######################################################
###########################################################################################

class CMDPreprocessorFactory:
   """
   Produces CMDPreprocessor instances catering to a module instance's needs.

   Reasons for this class:
      1: Server module instances may have different module command names during runtime.
         Having a factory class allows us to keep this flexibility.
      2: Allows command function decorators to be used in any order.
   """

   def __init__(self):
      self._setup_functions = []
      return

   def get_preprocessor(self, module_cmd_name):
      new_preprocessor = CMDPreprocessor()
      for setup_function in self._setup_functions:
         setup_function(new_preprocessor, module_cmd_name)
      return new_preprocessor

   def add_setup_function(self, setup_function):
      self._setup_functions.append(setup_function)
      return


class CMDPreprocessor:
   """
   This class allows simple processing of "core command name" into a module command.

   One instance is attached to each server module instance (not the class).
   (The reasons for this are detailed in CMDPreprocessorFactory.)
   """

   def __init__(self):
      self._simple_transformations = {} # FORMAT: {string: function string->string}
      return

   def perform_transformation(self, content, cmd_prefix):
      if content.startswith(cmd_prefix):
         new_content = content[len(cmd_prefix):]
         (left, right) = utils.separate_left_word(new_content)
         # Expected that they key will seldom-match, so we check for the key.
         if left in self._simple_transformations:
            content = cmd_prefix + self._simple_transformations[left]
            if len(right) != 0:
               content += " " + right
      return content

   def add_transformation(self, input_cmd, output_cmd):
      self._simple_transformations[input_cmd] = output_cmd
      return


