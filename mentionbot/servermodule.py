import utils
import cmd

# Abstract Class (would've been an interface...)
# All server modules are subclasses of ServerModule.
class ServerModule:
   """
   The base class of all server modules.

   This abstract class contains some overrideable services for building server
   modules.
   """

   MODULE_NAME = NotImplemented
   MODULE_SHORT_DESCRIPTION = NotImplemented
   RECOMMENDED_CMD_NAMES = NotImplemented
   
   # Must instantiate a token class. Recommended: utils.SecretToken()
   _SECRET_TOKEN = NotImplemented

   # Must instantiate an empty dictionary unless overriding all the following
   # methods (usually to implement a more complex bot command heirarchy):
   #     get_help_summary()
   #     get_help_detail()
   #     process_cmd()
   _cmd_dict = NotImplemented

   # Must instantiate a new cmd.CMDPreprocessorFactory instance unless overriding
   # the service.
   # It is this class that the cmd preprocessor decorators operate on.
   _cmd_prep_factory = NotImplemented
   
   # A string, potentially multi-line, giving a brief summary of the module.
   # Formatting arguments "modhelp", "mod", and "p" are used here, evaluated
   # when processing this string.
   _HELP_SUMMARY = NotImplemented

   ##############################################################################
   # THE BELOW MUST NOT BE OVERRIDDEN ###########################################
   ##############################################################################

   @classmethod
   async def get_instance(cls, cmd_names, resources):
      inst = cls(cls._SECRET_TOKEN, cmd_names)
      inst._cmd_prep = inst._cmd_prep_factory.get_preprocessor(inst.cmd_names[0])
      await inst._initialize(resources)
      return inst

   def __init__(self, token, cmd_names):
      self._cmd_names = cmd_names
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
      return

   # Return a list of strings to be used to invoke a module command.
   # For example, if command_names=["foo","baz"], then subcommands
   # "foo example" or "baz example" SHOULD both cause the ServerModule
   # process_cmd() function to be called with substr="example".
   @property
   def cmd_names(self):
      return self._cmd_names

   ##############################################################################
   # THE BELOW USE EXISTING SERVICES THAT MAY BE OVERRIDDEN #####################
   ##############################################################################

   # Get a help-message string summarising the module functionality,
   # or at least directing the user to more detailed help.
   # Returned string has no leading/trailing whitespace.
   def get_help_summary(self, privilege_level):
      return cmd.format_mod_evaluate(self._HELP_SUMMARY, mod=self.cmd_names[0])

   # Get a detailed help-message string about the module.
   # String has no leading/trailing whitespace.
   def get_help_detail(self, substr, privilege_level):
      buf = cmd.compose_help_summary(self._cmd_dict, privilege_level)
      return buf.format(b=self.cmd_names[0] + " ", p="{p}")

   # Every module has the opportunity to pre-process the contents of a message.
   # This is carried out after all modules have carried out their on_message()
   # methods.
   # The msg_preprocessor() methods for all installed server modules
   # are daisy-chained, i.e. the output from the first module.msg_preprocessor()
   # is the input into the next module.msg_preprocessor(). This means that
   # this method MAY receive an alread-processed command by another module!
   # Thus, it is important to ensure no preprocessor methods collide.
   # If you're not sure how to use this method, don't worry about implementing
   # it.
   #
   # This method is often used for processing command shortcuts.
   #     Example:
   #        Server module "Random" has the command "/rng choose [args]".
   #        invocation_shortcuts("something") -> returns -> "something"
   #        invocation_shortcuts("/choose A;B;C") -> returns -> "/rng choose A;B;C"
   # Some modules may even be entirely build around pre-processing.
   #     For example, a module may be a dedicated standin for another bot.
   #     That module may detect if that bot is offline or not responding,
   #     and if so, the module will process messages to redirect
   #     commands to itself to serve them.
   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      # TODO: Consider optimizing this by bypassing it if the service is not being
      #       used (i.e. the preprocessor won't do anything).
      return self._cmd_prep.perform_transformation(content, default_cmd_prefix)

   # This method is called if a command is to be handled by the module.
   # By default, it processes a command in _cmd_dict.
   # Overriding to add further pre-processing and other things would
   # usually involve calling this with super() rather than rewriting
   # it completely.
   # Complete rewrite should only happen if implementing a more complicated
   # bot command heirarchy (which should be never).
   async def process_cmd(self, substr, msg, privilege_level):
      (left, right) = utils.separate_left_word(substr)
      cmd_to_execute = cmd.get(self._cmd_dict, left, privilege_level)
      await cmd_to_execute(self, right, msg, privilege_level)
      return

   ##############################################################################
   # THE METHODS BELOW ARE UNUSED UNLESS OVERRIDDEN. ############################
   ##############################################################################

   # Do whatever initialization you wish here.
   async def _initialize(self, resources):
      pass

   # This method is always called every time a message from the module's associated
   # server is received.
   async def on_message(self, msg):
      pass




