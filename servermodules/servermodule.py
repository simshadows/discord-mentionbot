import re

# Abstract Class (would've been an interface...)
# All server modules are subclasses of ServerModule.
class ServerModule:

   _RE_PRIVLVL_LINE = re.compile(">>> PRIVILEGE LEVEL \d+")

   # Return a list of strings to be used to invoke a module command.
   # For example, if command_names=["foo","baz"], then subcommands
   # "foo example" or "baz example" SHOULD both cause the ServerModule
   # process_cmd() function to be called with substr="example".
   # TODO: Figure out a better way to define abstract attributes!!!
   @property
   def command_names(self):
      raise NotImplementedError

   # Associated setter for command_names property.
   # TODO: Figure out a better way to define abstract attributes!!!
   @command_names.setter
   def command_names(self, value):
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

   # A helper method for preparing help strings.
   # Parses a list of lines, producing a single string with the lines
   # combined, appropriate for the privilege level.
   # TODO: Add examples on this method's usage.
   @classmethod
   def _prepare_help_content(cls, raw_lines, cmd_prefix, privilegelevel=0):
      help_content = ""
      line_privlvl = 0
      for line in raw_lines:
         match = ServerModule._RE_PRIVLVL_LINE.match(line) # TODO: Is there nicer class attribute syntax?
         if match:
            line_privlvl = int(match.group(0)[len(">>> PRIVILEGE LEVEL "):])
         elif (privilegelevel >= line_privlvl):
            help_content += line + "\n"
      return help_content[:-1].format(pf=cmd_prefix)




