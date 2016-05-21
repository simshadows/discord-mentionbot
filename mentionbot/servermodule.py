import abc
import textwrap

from . import utils, cmd
from .helpnode import HelpNode
from .enums import PrivilegeLevel

module_list = []

# Class decorator for registering server modules
def registered(cls):
   module_list.append(cls)
   return cls

# Abstract Class (would've been an interface...)
# All server modules are subclasses of ServerModule.
class ServerModule(HelpNode):
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
   _cmdd = NotImplemented
   
   # A string, potentially multi-line, giving a brief summary of the module.
   # Formatting arguments "modhelp", "mod", and "p" are used here, evaluated
   # when processing this string.
   _HELP_SUMMARY = "`{modhelp}` <<PLACEHOLDER>>"

   ##############################################################################
   # THE BELOW MUST NOT BE OVERRIDDEN ###########################################
   ##############################################################################

   @classmethod
   async def get_instance(cls, cmd_names, resources):
      inst = cls(cls._SECRET_TOKEN)
      await inst._initialize(resources)
      return inst

   def __init__(self, token):
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
      return

   @classmethod
   def get_cmd_functions(cls):
      if cls._cmdd is NotImplemented:
         raise NotImplementedError
      seen_set = set()
      for (alias, function) in cls._cmdd.items():
         if function not in seen_set:
            seen_set.add(function)
            yield function

   # (HelpNode IMPLEMENTATION METHOD)
   async def node_min_priv(self):
      return PrivilegeLevel.get_lowest_privilege()
      # TODO: Make use of whole-module privilege restrictions in the future.

   async def node_category(self):
      return ""
      # TODO: Make use of categories in the future.

   ##############################################################################
   # THE BELOW USE EXISTING SERVICES THAT MAY BE OVERRIDDEN #####################
   ##############################################################################

   # (HelpNode IMPLEMENTATION METHOD)
   # This may be overwritten completely if you wish.
   async def get_help_detail(self, locator_string, entry_string, privilege_level):
      assert isinstance(locator_string, str) and isinstance(entry_string, str)
      assert isinstance(privilege_level, PrivilegeLevel)
      buf = None
      if locator_string is "":
         # Serve module help content.
         buf = await cmd.summarise_commands(self._cmdd, privilege_level=privilege_level)
         buf0 = await self._get_help_header_text(privilege_level)
         if not buf0 is None:
            buf = buf0 + "\n\n" + buf
      else:
         # Get the next node's help content.
         (left, right) = utils.separate_left_word(locator_string)
         if left in self._cmdd:
            buf = await self._cmdd[left].cmd_meta.get_help_detail(right, left, privilege_level)
      return buf

   # (HelpNode IMPLEMENTATION METHOD)
   # This may be overwritten completely if you wish.
   async def get_help_summary(self, privilege_level):
      assert isinstance(privilege_level, PrivilegeLevel)
      buf = textwrap.dedent(self._HELP_SUMMARY).strip()
      return buf.format(p="{p}", modhelp="{p}help {grp}")

   # This method is called if a command is to be handled by the module.
   # By default, it processes a command in _cmdd.
   # Overriding to add further pre-processing and other things would
   # usually involve calling this with super() rather than rewriting
   # it completely.
   # Complete rewrite should only happen if implementing a more complicated
   # bot command processing system.
   async def process_cmd(self, substr, msg, privilege_level):
      (left, right) = utils.separate_left_word(substr)
      cmd_to_execute = await cmd.get(self._cmdd, left, privilege_level)
      await cmd_to_execute(self, right, msg, privilege_level)
      return

   ##############################################################################
   # THE METHODS BELOW ARE UNUSED UNLESS OVERRIDDEN. ############################
   ##############################################################################

   # Do whatever initialization you wish here.
   async def _initialize(self, resources):
      pass

   # This function adds additional text to get_help_detail() when
   # locator_string="".
   # Any text returned by _get_help_header_text() will be appended above the
   # command summary produced in get_help_summary().
   async def _get_help_header_text(self, privilege_level):
      return None

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
      return content

   # This method is always called every time a message from the module's associated
   # server is received.
   async def on_message(self, msg):
      pass

   async def on_member_join(self, member):
      pass

   async def on_member_remove(self, member):
      pass
