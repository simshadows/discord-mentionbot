import asyncio
import sys
import concurrent
import traceback

from . import utils, errors, cmd
from .helpnode import HelpNode
from .enums import PrivilegeLevel
from .servermoduleresources import ServerModuleResources

class ServerModuleWrapper(HelpNode): #  # TODO Having weird issues here...
   """
   Wraps the operations of a server module.

   Has two states:
      Active
         The module instance is running as intended.
      Inactive
         The module is not running. The wrapper holds no reference to the
         module. Calls to methods that would've been served by the module
         instance vary. This behaviour is found at the beginning of function
         definitions.
   """

   _SECRET_TOKEN = NotImplemented

   SUPPRESS_AUTOKILL_DEFAULT = False

   # Note that the initial state of ServerModuleWrapper is deactivated.
   @classmethod
   async def get_instance(cls, module_class, server_bot_instance, *args):
      self = cls(cls._SECRET_TOKEN)

      # Arguments
      module_cmd_aliases = None
      if len(args) == 1:
         module_cmd_aliases = list(args[0])
      else:
         module_cmd_aliases = module_class.RECOMMENDED_CMD_NAMES

      self._client = server_bot_instance.client
      self._sbi = server_bot_instance
      
      self._module_class = module_class
      self._module_cmd_aliases = module_cmd_aliases
      self._shortcut_cmd_aliases = None # Maps top-level command alias to module command alias.

      self._state_lock = asyncio.Lock()

      self._is_active = False
      self._user_nonreturning_tasks = None # List of tasks
      self._module_instance = None
      self._suppress_autokill = self.SUPPRESS_AUTOKILL_DEFAULT

      # Initialize self._shortcut_cmd_aliases
      self._shortcut_cmd_aliases = {}
      for cmd_fn in self._module_class.get_cmd_functions():
         top_level_aliases = cmd_fn.cmd_meta.get_top_aliases()
         if top_level_aliases is None:
            continue
         for top_level_alias in top_level_aliases:
            self._shortcut_cmd_aliases[top_level_alias] = cmd_fn.cmd_meta.get_aliases()[0]
      return self

   def __init__(self, token):
      if not token is self._SECRET_TOKEN:
         raise RuntimeError("Not allowed to instantiate directly. Please use get_instance().")
      return

   @property
   def module_name(self):
      return self._module_class.MODULE_NAME

   @property
   def module_short_description(self):
      return self._module_class.MODULE_SHORT_DESCRIPTION

   @property
   def module_cmd_aliases(self):
      return self._module_cmd_aliases

   # Returns all top-level commands that are to be directed to this module.
   # This includes all aliases from self.module_cmd_aliases, and the other
   # "shortcut" aliases.
   @property
   def all_cmd_aliases(self):
      aliases = list(self._module_cmd_aliases)
      for (alias, transformation) in self._shortcut_cmd_aliases.items():
         aliases.append(alias)
      return aliases

   def is_active(self):
      return self._is_active

   @utils.synchronized("_state_lock")
   async def activate(self):
      if self.is_active():
         raise RuntimeError("Module is already active.")
      self._is_active = True
      self._user_nonreturning_tasks = []
      self._suppress_autokill = self.SUPPRESS_AUTOKILL_DEFAULT
      res = ServerModuleResources(self._module_class.MODULE_NAME, self._sbi, self)
      self._module_instance = await self._module_class.get_instance(self._module_cmd_aliases, res)
      return

   @utils.synchronized("_state_lock")
   async def kill(self):
      if not self.is_active():
         raise RuntimeError("Module is already inactive.")
      self._is_active = False
      for task in self._user_nonreturning_tasks:
         task.cancel()
         try:
            task.set_result(None)
         except:
            pass
      self._user_nonreturning_tasks = None
      self._module_instance = None
      return

   # PRECONDITION: The function must be called within an except block.
   # PARAMETER: e: Error event that caused the error.
   # RETURNS: A string which may be sent back to a channel for user feedback.
   async def _module_method_error_handler(self, e, cmd_msg=None):
      buf_ei = None
      if self._suppress_autokill:
         buf_ei = "Module autokill is suppressed."
      else:
         buf_ei = "Module autokill is not suppressed."
      buf_fi = "This error occurred within the module `{}`.".format(self.module_name)
      if not self._suppress_autokill:
         await self.kill()
         buf_fi += "\nModule has been automatically killed for safety and must be manually reactivated."
      kwargs = {
         "cmd_msg": cmd_msg,
         "handled_by": "SeverModuleWrapper, in a module-serving method.",
         "extra_info": buf_ei,
         "final_info": buf_fi,
      }
      return await self._client.report_exception(e, **kwargs)

   ########################################################################################
   # METHODS USED FOR OTHER MODULE SERVICES ###############################################
   ########################################################################################

   # If setting=True, then module auto-kill will be less aggressive.
   def set_suppress_autokill(self, setting):
      self._suppress_autokill = bool(setting)
      return

   # Non-returning coroutines are to be started here.
   # This ensures correct error handling.
   # TODO: Somehow synchronize this. The decorator has been commented out.
   # @synchronized_with_state_lock
   async def start_user_nonreturning_coro(self, coro):
      if not self.is_active():
         raise RuntimeError("Module is inactive.")
      loop = asyncio.get_event_loop()
      async def wrapping_coro():
         try:
            await coro
         except concurrent.futures.CancelledError:
            raise # Allow the coroutine to be cancelled.
         except:
            pass
         # The coroutine should never return or raise an exception.
         # If it does, this is a fatal error and MUST cause the server module to be killed.
         await self.kill()
         buf_hb = "SeverModuleWrapper.start_user_nonreturning_coro()"
         buf_fi = "This error occurred within the module `{}`.".format(self.module_name)
         buf_fi += "\nAn exception in a non-returning coroutine is fatal."
         buf_fi += "\nThis module must now be killed."
         await self._client.report_exception(e, handled_by=buf_hb, final_info=buf_fi)
         loop.call_soon()
      task = loop.create_task(wrapping_coro())
      self._user_nonreturning_tasks.append(task)
      return

   ########################################################################################
   # METHODS SERVED BY THE MODULE #########################################################
   ########################################################################################

   # (HelpNode IMPLEMENTATION METHOD)
   async def get_help_detail(self, locator_string, entry_string, privilege_level):
      assert isinstance(locator_string, str) and isinstance(entry_string, str)
      assert isinstance(privilege_level, PrivilegeLevel)
      if not self.is_active():
         return "The `{}` module is not active.".format(self.module_name)
      try:
         print(locator_string)
         print(entry_string)
         if entry_string in self._shortcut_cmd_aliases:
            locator_string = self._shortcut_cmd_aliases[entry_string] + " " + locator_string
            entry_string = self._module_cmd_aliases[0]
         return await self._module_instance.get_help_detail(locator_string, entry_string, privilege_level)
      except Exception as e:
         return await self._module_method_error_handler(e)

   # (HelpNode IMPLEMENTATION METHOD)
   async def get_help_summary(self, privilege_level):
      assert isinstance(privilege_level, PrivilegeLevel)
      if not self.is_active():
         return "(The `{}` module is not active.)".format(self.module_name)
      try:
         return await self._module_instance.get_help_summary(privilege_level)
      except Exception as e:
         await self._module_method_error_handler(e)
         return "(Unable to obtain `{}` help.)".format(self.module_name)

   # (HelpNode IMPLEMENTATION METHOD)
   async def node_min_priv(self):
      if not self.is_active():
         return PrivilegeLevel.get_lowest_privilege()
      try:
         return await self._module_instance.node_min_priv()
      except Exception as e:
         await self._module_method_error_handler(e)
         return PrivilegeLevel.get_lowest_privilege()

   # (HelpNode IMPLEMENTATION METHOD)
   async def node_category(self):
      if not self.is_active():
         return "<<INACTIVE>>"
      try:
         return await self._module_instance.node_category()
      except Exception as e:
         await self._module_method_error_handler(e)
         return "<<ERROR>>"

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      if not self.is_active():
         return content
      try:
         return await self._module_instance.msg_preprocessor(content, msg, default_cmd_prefix)
      except Exception as e:
         await self._module_method_error_handler(e)
         return content

   # PARAMETER: upper_cmd_alias is the command alias that was split off before
   #            the substring was passed into this function.
   #            E.g. if the full command was `/random choice A;B;C`, ServerBotInstance
   #            would pass in substr="choice A;B;C" and upper_cmd_alias="random".
   async def process_cmd(self, substr, msg, privilege_level, upper_cmd_alias):
      if not self.is_active():
         buf = "Error: The `{}` server module is not active.".format(self.module_name)
         buf += "\n\n*(Automatic deactivation is usually caused by an unhandled error within"
         buf += " the module. This is done as a security measure to prevent further damage,"
         buf += " especially from exploitable bugs.)*"
         await self._client.send_msg(msg, buf)
         return
      if upper_cmd_alias in self._shortcut_cmd_aliases:
         substr = self._shortcut_cmd_aliases[upper_cmd_alias] + " " + substr
      try:
         await self._module_instance.process_cmd(substr, msg, privilege_level)
      except errors.CommandHandlingSignal:
         raise # TODO: This is so messy...
      except Exception as e:
         await self._module_method_error_handler(e, cmd_msg=msg)
      return

   async def on_message(self, msg):
      if not self.is_active():
         return
      try:
         return await self._module_instance.on_message(msg)
      except Exception as e:
         await self._module_method_error_handler(e)
         return

   async def on_member_join(self, member):
      if not self.is_active():
         return
      try:
         return await self._module_instance.on_member_join(member)
      except Exception as e:
         await self._module_method_error_handler(e)
         return

   async def on_member_remove(self, member):
      if not self.is_active():
         return
      try:
         return await self._module_instance.on_member_remove(member)
      except Exception as e:
         await self._module_method_error_handler(e)
         return
