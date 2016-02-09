class MentionbotError(Exception):
   def __init__(self):
      return

class UnknownCommandError(MentionbotError):
   def __init__(self):
      return

class InvalidCommandArgumentsError(MentionbotError):
   def __init__(self):
      return

class CommandPrivilegeError(MentionbotError):
   def __init__(self):
      return

class NoHelpContentExists(MentionbotError):
   def __init__(self):
      return

# General-purpose exception.
class DoesNotExist(MentionbotError):
   def __init__(self):
      return




