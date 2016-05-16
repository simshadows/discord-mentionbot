import abc
import asyncio
import sys
import concurrent

from . import utils, errors, cmd
from .servermoduleresources import ServerModuleResources

class ServerModuleWrapper(abc.ABC):
   """
   Wraps the operations of a server module.

   The wrapper has two states:
      Active
         The module instance is running as intended.
      Inactive
         The module is not running. The wrapper holds no reference to the
         module. Calls to methods that would've been served by the module
         instance vary. This behaviour is found at the beginning of function
         definitions.
   The wrapper always begins in the inactive state, and is to be activated
   using `ServerModuleWrapper.activate()`.
   However, the wrapper of a core module CANNOT BE DEACTIVATED.

   Handling exceptions raised by module methods is handled differently between
   regular and core module wrappers.
      Regular module errors are caught, reported, and may automatically
      deactivate the module.
      Core module errors simply continue propagation, and thus have no special
      error handling.
   """

   _SECRET_TOKEN = utils.SecretToken()

   # Note that the initial state of ServerModuleWrapper is deactivated.
   @classmethod
   async def get_instance(cls, module_class, server_bot_instance, *args, core=False):
      wrapper_class = None
      if core:
         wrapper_class = CoreModuleWrapper
      else:
         wrapper_class = RegularModuleWrapper
      return await wrapper_class.conc_get_instance(module_class, server_bot_instance, *args)

   # This abstract method implements some basic infrastructure common to all
   # implementations, and so must be called with super().
   @classmethod
   @abc.abstractmethod
   async def conc_get_instance(cls, module_class, server_bot_instance, *args):
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

      # Initialize self._shortcut_cmd_aliases
      self._shortcut_cmd_aliases = {}
      for cmd_fn in self._module_class.get_cmd_functions():
         if not hasattr(cmd_fn, "top_level_alias_type"):
            continue
         module_cmd_alias = cmd_fn.cmd_names[0]
         top_level_aliases = None
         if cmd_fn.top_level_alias_type is cmd.TopLevelAliasAction.USE_EXISTING_ALIASES:
            top_level_aliases = cmd_fn.cmd_names
         elif cmd_fn.top_level_alias_type is cmd.TopLevelAliasAction.USE_NEW_ALIASES:
            top_level_aliases = cmd_fn.top_level_aliases
         else:
            raise RuntimeError("Not a recognized enum value.")
         for top_level_alias in top_level_aliases:
            self._shortcut_cmd_aliases[top_level_alias] = module_cmd_alias
      return self

   # NOT TO BE OVERRIDDEN
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

   @abc.abstractmethod
   def is_core(self):
      raise NotImplementedError

   @abc.abstractmethod
   def is_active(self):
      raise NotImplementedError

   @abc.abstractmethod
   async def activate(self):
      raise NotImplementedError

   @abc.abstractmethod
   async def kill(self):
      raise NotImplementedError

   ########################################################################################
   # METHODS USED FOR OTHER MODULE SERVICES ###############################################
   ########################################################################################

   # If setting=True, then module auto-kill will be less aggressive.
   @abc.abstractmethod
   def set_suppress_autokill(self, setting):
      raise NotImplementedError

   # Non-returning coroutines are to be started here.
   # This ensures correct error handling.
   # TODO: Somehow synchronize this. The decorator has been commented out.
   # @synchronized_with_state_lock
   @abc.abstractmethod
   async def start_user_nonreturning_coro(self, coro):
      raise NotImplementedError

   ########################################################################################
   # METHODS SERVED BY THE MODULE #########################################################
   ########################################################################################

   @abc.abstractmethod
   async def get_help_summary(self, privilege_level):
      return "!!!PLACEHOLDER!!!"

   @abc.abstractmethod
   async def get_help_detail(self, substr, privilege_level):
      return "!!!PLACEHOLDER!!!"

   @abc.abstractmethod
   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      return content

   # PARAMETER: upper_cmd_alias is the command alias that was split off before
   #            the substring was passed into this function.
   #            E.g. if the full command was `/random choice A;B;C`, ServerBotInstance
   #            would pass in substr="choice A;B;C" and upper_cmd_alias="random".
   @abc.abstractmethod
   async def process_cmd(self, substr, msg, privilege_level, upper_cmd_alias):
      pass

   @abc.abstractmethod
   async def on_message(self, msg):
      pass

   @abc.abstractmethod
   async def on_member_join(self, member):
      pass

   @abc.abstractmethod
   async def on_member_remove(self, member):
      pass

# RegularModuleWrapper helper decorator
def synchronized_with_state_lock(function):
   async def wrapper_function(*args, **kwargs):
      self = args[0]
      await self._state_lock.acquire()
      ret = None
      try:
         ret = await function(*args, **kwargs)
      finally:
         self._state_lock.release()
      return ret
   return wrapper_function

class RegularModuleWrapper(ServerModuleWrapper):
   SUPPRESS_AUTOKILL_DEFAULT = False

   @classmethod
   async def conc_get_instance(cls, module_class, server_bot_instance, *args):
      self = await super(RegularModuleWrapper, cls).conc_get_instance(module_class, server_bot_instance, *args)
      
      self._state_lock = asyncio.Lock()

      self._is_active = False
      self._user_nonreturning_tasks = None # List of tasks
      self._module_instance = None
      self._suppress_autokill = self.SUPPRESS_AUTOKILL_DEFAULT
      return self

   def is_core(self):
      return False

   def is_active(self):
      return self._is_active

   @synchronized_with_state_lock
   async def activate(self):
      if self.is_active():
         raise RuntimeError("Module is already active.")
      self._is_active = True
      self._user_nonreturning_tasks = []
      self._suppress_autokill = self.SUPPRESS_AUTOKILL_DEFAULT
      res = ServerModuleResources(self._module_class.MODULE_NAME, self._sbi, self)
      self._module_instance = await self._module_class.get_instance(self._module_cmd_aliases, res)
      return

   @synchronized_with_state_lock
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
         "handled_by": "RegularModuleWrapper, in a module-serving method.",
         "extra_info": buf_ei,
         "final_info": buf_fi,
      }
      return await self._client.report_exception(e, **kwargs)

   ########################################################################################
   # METHODS USED FOR OTHER MODULE SERVICES ###############################################
   ########################################################################################

   def set_suppress_autokill(self, setting):
      self._suppress_autokill = bool(setting)
      return

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

   async def get_help_summary(self, privilege_level):
      if not self.is_active():
         return "(The `{}` module is not active.)".format(self.module_name)
      try:
         return self._module_instance.get_help_summary(privilege_level, self._module_cmd_aliases[0])
      except Exception as e:
         await self._module_method_error_handler(e)
         return "(Unable to obtain `{}` help.)".format(self.module_name)

   async def get_help_detail(self, substr, privilege_level):
      if not self.is_active():
         return "The `{}` module is not active.".format(self.module_name)
      try:
         return self._module_instance.get_help_detail(substr, privilege_level, self._module_cmd_aliases[0])
      except Exception as e:
         return await self._module_method_error_handler(e)

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

class CoreModuleWrapper(ServerModuleWrapper):
   @classmethod
   async def conc_get_instance(cls, module_class, server_bot_instance, *args):
      self = await super(CoreModuleWrapper, cls).conc_get_instance(module_class, server_bot_instance, *args)
      self._module_instance = None
      return self

   def is_core(self):
      return True

   def is_active(self):
      return not self._module_instance is None

   async def activate(self):
      if self.is_active():
         raise RuntimeError("Module is already active.")
      res = ServerModuleResources(self._module_class.MODULE_NAME, self._sbi, self)
      self._module_instance = await self._module_class.get_instance(self._module_cmd_aliases, res)
      return

   async def kill(self):
      raise RuntimeError("Core modules cannot be killed.")

   ########################################################################################
   # METHODS USED FOR OTHER MODULE SERVICES ###############################################
   ########################################################################################

   def set_suppress_autokill(self, setting):
      raise RuntimeError("Not supported by core modules.")

   async def start_user_nonreturning_coro(self, coro):
      raise RuntimeError("Not supported by core modules.")

   ########################################################################################
   # METHODS SERVED BY THE MODULE #########################################################
   ########################################################################################

   async def get_help_summary(self, privilege_level):
      return self._module_instance.get_help_summary(privilege_level, self._module_cmd_aliases[0])

   async def get_help_detail(self, substr, privilege_level):
      return self._module_instance.get_help_detail(substr, privilege_level, self._module_cmd_aliases[0])

   async def msg_preprocessor(self, content, msg, default_cmd_prefix):
      return await self._module_instance.msg_preprocessor(content, msg, default_cmd_prefix)

   # PARAMETER: upper_cmd_alias is the command alias that was split off before
   #            the substring was passed into this function.
   #            E.g. if the full command was `/random choice A;B;C`, ServerBotInstance
   #            would pass in substr="choice A;B;C" and upper_cmd_alias="random".
   async def process_cmd(self, substr, msg, privilege_level, upper_cmd_alias):
      if upper_cmd_alias in self._shortcut_cmd_aliases:
         substr = self._shortcut_cmd_aliases[upper_cmd_alias] + " " + substr
      return await self._module_instance.process_cmd(substr, msg, privilege_level)

   async def on_message(self, msg):
      return await self._module_instance.on_message(msg)

   async def on_member_join(self, member):
      return await self._module_instance.on_member_join(member)

   async def on_member_remove(self, member):
      return await self._module_instance.on_member_remove(member)
