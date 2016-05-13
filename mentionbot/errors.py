class MentionbotException(Exception):
   def __init__(self):
      return

################################
### COMMAND HANDLING SIGNALS ###
################################

class CommandHandlingSignal(MentionbotException):
   def __init__(self):
      return

class UnknownCommandError(CommandHandlingSignal):
   def __init__(self):
      return

class SilentUnknownCommandError(UnknownCommandError):
   def __init__(self):
      return

class InvalidCommandArgumentsError(CommandHandlingSignal):
   def __init__(self):
      return

class CommandPrivilegeError(CommandHandlingSignal):
   def __init__(self):
      return

class NoHelpContentExists(CommandHandlingSignal):
   def __init__(self):
      return

##################################
### General-purpose exceptions ###
##################################

class GeneralMentionbotException(MentionbotException):
   def __init__(self):
      return

class DoesNotExist(GeneralMentionbotException):
   def __init__(self):
      return

class NoRecordExists(GeneralMentionbotException):
   def __init__(self):
      return

class OperationAborted(GeneralMentionbotException):
   def __init__(self):
      return

# Proposed but unused.
# ##########################
# ### Special exceptions ###
# ##########################

# class SpecialMentionbotException(MentionbotException):
#    def __init__(self):
#       return

# class ServerModuleUninitialized(SpecialMentionbotException):
#    def __init__(self, module_name):
#       self._module_name = module_name
#       return

#    @property
#    def module_name(self):
#       return self._module_name
