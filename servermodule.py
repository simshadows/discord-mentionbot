import re

# Abstract Class (would've been an interface...)
# All server modules are subclasses of ServerModule.
class ServerModule:

   RECOMMENDED_CMD_NAMES = NotImplemented

   # TODO: Is it possible or even practical to define a standard constructor?
   # def __init__(self, cmd_names, client):

   # Return a list of strings to be used to invoke a module command.
   # For example, if command_names=["foo","baz"], then subcommands
   # "foo example" or "baz example" SHOULD both cause the ServerModule
   # process_cmd() function to be called with substr="example".
   # TODO: Figure out a better way to define abstract attributes!!!
   @property
   def cmd_names(self):
      raise NotImplementedError

   # Get a help-message string summarising the module functionality,
   # or at least directing the user to more detailed help.
   # Returned string has no leading/trailing whitespace.
   # NOTE: cmd_prefix is sensitive to leading/trailing whitespace.
   #       For example, cmd_prefix="/" will make module commands show
   #       up as "/examplecommand", while "$mb " will make the same
   #       module command show up as "$mb examplecommand".
   def get_help_summary(self, cmd_prefix, privilegelevel=0):
      raise NotImplementedError

   # Get a detailed help-message string about the module.
   # String has no leading/trailing whitespace.
   # NOTE: cmd_prefix works the same as in get_help_summary.
   def get_help_detail(self, substr, cmd_prefix, privilegelevel=0):
      raise NotImplementedError

   # This method is always called every time a message from the module's associated
   # server is received.
   async def on_message(self, msg):
      raise NotImplementedError

   # This method is called if a command is to be handled by the module.
   async def process_cmd(self, substr, msg, privilegelevel=0):
      raise NotImplementedError




