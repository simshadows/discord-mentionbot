from enums import PrivilegeLevel
import errors

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
      try:
         if privilege_level < cmd_to_execute.minimum_privilege:
            raise errors.CommandPrivilegeError
      except AttributeError:
         pass
      return cmd_to_execute
   except KeyError:
      raise errors.InvalidCommandArgumentsError

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

# (CURRENTLY NOT USED...)
# # Decorator adds an attribute named "help_summary" to a function object.
# # This attribute is read when compiling help messages.
# # If a minimum privilege is also assigned, then it is possible to filter
# # unnecessary help content before displaying them.
# #
# # The "text" parameter is also specifically formatted.
# # Please see examples of this formatting in serverbotinstance.py.
# #
# # This decorator may also be deactivated with parameter "show" but still
# # used to act as a consistent form of documentation.
# #
# # PRECONDITION:
# def help_summary(text, *, show=True):
#    def function_decorator(function):
#       if show:
#          function.help_summary = text
#       return function
#    return function_decorator



