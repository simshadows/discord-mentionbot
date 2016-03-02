import inspect

import utils
from enums import PrivilegeLevel
import errors

# "{cmd}" -> "{bc}{c}" -> "{p}{b}{c}"

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
   buf = ""
   seen_set = set()
   for (cmd_name, cmd_obj) in cmd_dict.items():
      if not cmd_obj in seen_set:
         if hasattr(cmd_obj, "minimum_privilege"):
            if privilege_level < cmd_obj.minimum_privilege:
               continue
         seen_set.add(cmd_obj)
         help_str = get_help_summary(cmd_obj)
         if len(help_str) != 0:
            buf += help_str + "\n"
   if len(buf) == 0:
      return ""
   else:
      line_list = sorted(buf.splitlines(), key=lambda e: e.lower())
      # Keeping in mind that all lines end in new-line.
      buf = "\n".join(line_list)
      return buf[:-1]

# This method is not normally used anywhere other than compose_help_summary().
# This method also processes "{cmd}" -> "{bc}{c}" and substitutes in the
# value of "{c}".
def get_help_summary(cmd_obj):
   docstr = inspect.getdoc(cmd_obj)
   if docstr is None or len(docstr) == 0:
      return ""
   docstr = docstr.split("\n", 1)[0].format(cmd="{bc}{c}")
   return docstr.format(c=cmd_obj.cmd_names[0], bc="{bc}")

def get_help_detail(cmd_obj):
   docstr = inspect.getdoc(cmd_obj)
   if docstr is None or len(docstr) == 0:
      return ""
   else:
      return docstr


# NO LONGER USED

# def compose_help_summary(cmd_obj_list, privilege_level):
#    # Organize into groups.
#    helps_cats = {}
#    for fn_obj in cmd_obj_list:
#       try:
#          min_privilege = cmd_obj_list.minimum_privilege
#          if privilege_level < min_privilege:
#             continue
#       except AttributeError:
#          pass
#       key_str = None
#       try:
#          key_str = fn_obj.helps_category
#       except AttributeError:
#          key_str = ""
#       helps_str = None
#       try:
#          helps_str = fn_obj.help_summary
#       except AttributeError:
#          continue
#       cat_list = None
#       try:
#          cat_list = helps_cats[key_str]
#       except KeyError:
#          cat_list = helps_cats[key_str] = []
#       cat_list.append(helps_str)

#    # Sort each list of functions and put in a list.
#    helps_cats_list = []
#    for (cat_str, fn_list) in helps_cats.items():
#       to_append = (cat_str, sorted(fn_list, key=lambda e: e.helps_summary.lower()))
#       helps_cats_list.append(to_append)
#    if len(helps_cats_list) == 0:
#       return ""
#    # list is now guaranteed to have something to print.

#    # Sort group list into alphabetical order
#    helps_cats_list = sorted(helps_cats_list, key=lambda e: e[0].lower())

#    # Produce help message
#    buf = ""
#    for (cat_str, fn_list) in helps_cats_list:
#       if len(cat_str) != 0:
#          buf += "**" + cat_str + "**:\n"
#       for fn_obj in fn_list:
#          buf += fn_obj.helps_summary + "\n"
#       buf += "\n"
#    return buf[:-2] # Trim off last two newlines.

#    # buf = ""
#    # for fn_obj in cmd_obj_list:
#    #    try:
#    #       min_privilege = cmd_obj_list.minimum_privilege
#    #       if privilege_level < min_privilege:
#    #          continue
#    #    except AttributeError:
#    #       pass
#    #    buf += fn_obj.help_summary + "\n"
#    # if len(buf) == 0:
#    #    return ""
#    # else:
#    #    return buf[:-1]

# def compose_help_detail(cmd_obj, privilege_level):
#    try:
#       if privilege_level < cmd_to_execute.minimum_privilege:
#          raise errors.CommandPrivilegeError
#    except AttributeError:
#       pass

#    # This should nicely detail the priorities of what gets evaluated

#    try:
#       return cmd_obj.help_detail_fn()
#    except AttributeError:
#       pass

#    try:
#       return cmd_obj.help_detail_str
#    except AttributeError:
#       pass

#    try:
#       return 
   

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


# NO LONGER USED

# # This decorator may also be deactivated with parameter "show" but still
# # used to act as a consistent form of documentation.
# #
# # PARAMETER: help_list - The list in which the command is to be added to.
# # PARAMETER: content - The help content.
# # PARAMETER: show - If False, the decorator doesn't actually add the function to the list.
# def helps(help_list, content, *, show=True):
#    def function_decorator(function):
#       function.help_summary = content
#       if show:
#          help_list.append(function)
#       return function
#    return function_decorator


# # Decorator adds an attribute named "helps_category" to a function object.
# # This attribute is used when composing help messages, for grouping.
# # When no category has been assigned (i.e. the decorator is not used),
# # the composed help message will group the command along with all the
# # other ungrouped commands.
# def helps_category(text):
#    def function_decorator(function):
#       function.helps_category = text
#       return function
#    return function_decorator

# # PARAMETER: help obj - Can be either a string or a function that returns
# #                       a string. For details on how detailed help is
# #                       composed, see compose_help_detail().
# def helpd(content_obj):
#    def function_decorator(function):
#       if isinstance(content_obj, str):
#          function.help_detail_str = content_obj
#       elif callable(content_obj):
#          function.help_detail_fn = content_obj
#       return function
#    return function_decorator










