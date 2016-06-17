import asyncio
import logging
import datetime
import sys
import copy
import time
import re
import os
import traceback
import functools
import textwrap
from concurrent.futures import ThreadPoolExecutor

import discord # pip install git+https://github.com/Rapptz/discord.py@async
# pip install git+https://github.com/Julian/jsonschema

from . import utils, errors, clientextended

from .serverbotinstance import ServerBotInstance
from .messagecache import MessageCache

discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.CRITICAL)
logger = logging.getLogger()
logger.setLevel(logging.CRITICAL)
handler = logging.FileHandler(filename="mentionbot.log", encoding="utf-8", mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s"))
logger.addHandler(handler)

class MentionBot(clientextended.ClientExtended):
   CACHE_DIRECTORY = "cache/" # This MUST end with a forward-slash. e.g. "cache/"
   
   def __init__(self, **kwargs):
      super(MentionBot, self).__init__(**kwargs)

      self.on_message_lock = asyncio.Lock()
      self.on_member_join_lock = asyncio.Lock()
      self.on_member_remove_lock = asyncio.Lock()

      print("CACHE_DIRECTORY = '{}'".format(MentionBot.CACHE_DIRECTORY))

      self._conf = kwargs["config_dict"]
      assert isinstance(self._conf, dict)

      self._kill_bot_on_message_exception = self._conf["error_handling"]["kill_bot_on_message_exception"]
      
      self._message_bot_owner_on_init = self._conf["misc"]["message_bot_owner_on_init"]
      self._message_bot_owner_on_error = self._conf["error_handling"]["message_bot_owner_on_error"]

      self._default_status = self._conf["misc"]["default_status"]
      self._init_status = self._conf["misc"]["initialization_status"]

      self._bot_owner_id = self._conf["DEFAULT"]["bot_owner_id"]
      self._bot_owner_obj = None

      self._bot_instances = None
      return

   async def on_ready(self):
      try:
         await self.set_game_status(self._init_status)
         self._bot_owner_obj = self.search_for_user(self.get_bot_owner_id())
         if self._bot_owner_obj is None:
            buf = textwrap.dedent("""
               Failed to find the bot owner.
               
               Either:
                  - You haven't entered a valid ID in config.ini bot_owner_id,
                  - That ID isn't associated with a real user, or
                  - The owner exists, but this bot is not present in a server with them.

               As of right now, this bot is not designed to function without being able to see its owner.

               Please solve this before relaunching.
               """).strip()
            print(buf)
            sys.exit(0)

         self.message_cache = await MessageCache.get_instance(self, self.CACHE_DIRECTORY)

         self._bot_instances = {}
         for server in self.servers:
            new_args = [self, server, self._conf]
            self._bot_instances[server] = await ServerBotInstance.get_instance(*new_args)

         await self.set_game_status(self._default_status)
         try:
            botowner = self.search_for_user(self.get_bot_owner_id())
            print("Bot owner: " + self._bot_owner_obj.name)
         except:
            print("Bot owner: (NOT FOUND. UNKNOWN ERROR.)")
            print("Bot owner ID: " + self.get_bot_owner_id())
         print("Bot name: " + self.user.name)
         print("")
         self.on_message_lock.release()
         self.on_member_join_lock.release()
         self.on_member_remove_lock.release()
         if self._message_bot_owner_on_init:
            try:
               await self.send_msg(self._bot_owner_obj, "Initialization complete.")
            except:
               print("FAILED TO SEND BOTOWNER INITIALIZATION NOTIFICATION.")
         logging.info("Initialization complete.")
         print("Initialization complete.")
      except (SystemExit, KeyboardInterrupt):
         raise
      except BaseException as e:
         print(traceback.format_exc())
         sys.exit(1)
      return

   # General routine for uncaught exceptions from events (called by the API).
   # However, event handler routines should ideally implement their own.
   async def on_error(self, event, *args, **kwargs):
      try:
         buf_hb = "MentionBot.on_error()."
         buf_ei = "EVENT:\n" + str(event)
         buf_ei += "\nARGS:\n"
         if len(args) == 0:
            buf_ei += "(none)\n"
         else:
            for arg in args:
               buf_ei += str(arg) + "\n"
         buf_ei += "KWARGS:\n"
         if not kwargs:
            buf_ei += "(none)\n"
         else:
            for (kwarg, item) in kwargs.items():
               buf_ei += "{0}: {1}\n".format(str(kwarg), str(item))
         buf_fi = "Attempting to exit with code 1."
         await self.report_exception(event, handled_by=buf_hb, extra_info=buf_ei, final_info=buf_fi)
      except:
         buf = "ERROR WITHIN on_error()!\n" + traceback.format_exc()
         print(buf, file=sys.stderr)
         logging.critical(buf)
      sys.exit(1)

   async def on_message(self, msg):
      await self.on_message_lock.acquire()
      try:
         await self._on_message(msg)
      finally:
         self.on_message_lock.release()
      return

   # TODO: Ensure this method actually lets in messages in a queued fashion...
   async def _on_message(self, msg):
      await self.message_cache.record_message(msg)
      if msg.author == self.user:
         return # Should no longer process own messages.

      # Common code for exception handling in _on_message().
      async def handle_general_error(e, msg, *, close_bot=True):
         buf_hb = "MentionBot._on_message()."
         buf_fi = None
         if close_bot:
            buf_fi = "**THIS BOT WILL NOW RESTART.**"
         await self.report_exception(e, cmd_msg=msg, handled_by=buf_hb, final_info=buf_fi)
         if close_bot:
            sys.exit(1)
         return

      try:
         text = msg.content.strip()
         if isinstance(msg.channel, discord.Channel):
            await self._bot_instances[msg.server].process_text(text, msg)
            try:
               print("msg rcv #" + msg.channel.name + ": " + utils.str_asciionly(text))
            except Exception:
               print("msg rcv (CAUGHT EXCEPTION; UNKNOWN DISPLAY ERROR)")
         else: # Assumed to be a private message.
            await self.send_msg(msg, "sry m8 im not programmed to do anything fancy with pms yet")
            try:
               print("private msg rcv from" + utils.str_asciionly(msg.author.name) + ": " + utils.str_asciionly(text))
            except Exception:
               print("private msg rcv (CAUGHT EXCEPTION; UNKNOWN DISPLAY ERROR)")
      
      except errors.SilentUnknownCommandError:
         print("Caught SilentUnknownCommandError.")
      except errors.UnknownCommandError:
         print("Caught UnknownCommandError.")
         await self.send_msg(msg, "Error: Unknown command.")
      except errors.InvalidCommandArgumentsError as e:
         print("Caught InvalidCommandArgumentsError.")
         if str(e) == "":
            buf = "Error: Invalid command arguments."
         else:
            buf = str(e)
         await self.send_msg(msg, buf)
      except errors.CommandPrivilegeError:
         print("Caught CommandPrivilegeError.")
         await self.send_msg(msg, "Error: Permission denied.")
      except errors.NoHelpContentExists:
         print("Caught NoHelpContentExists.")
         await self.send_msg(msg, "No help content exists.")
      except errors.OperationAborted:
         print("Caught OperationAborted.")
      except Exception as e:
         await handle_general_error(e, msg, close_bot=self._kill_bot_on_message_exception)
      except (SystemExit, KeyboardInterrupt):
         raise
      except BaseException as e:
         await handle_general_error(e, msg, close_bot=True)
      return

   async def on_member_join(self, member):
      await self.on_member_join_lock.acquire()
      try:
         await self._on_member_join(member)
      finally:
         self.on_member_join_lock.release()
      return

   async def _on_member_join(self, member):
      await self._bot_instances[member.server].on_member_join(member)
      return

   async def on_member_remove(self, member):
      await self.on_member_remove_lock.acquire()
      try:
         await self._on_member_remove(member)
      finally:
         self.on_member_remove_lock.release()
      return

   async def _on_member_remove(self, member):
      await self._bot_instances[member.server].on_member_remove(member)
      return

   async def on_server_join(self, server):
      raise RuntimeError("Undefined behaviour on server join. Must restart.")

   async def on_server_remove(self, server):
      raise RuntimeError("Undefined behaviour on server leave. Must restart.")

   ##################
   # Other Services #
   ##################

   def get_bot_owner_id(self):
      return self._bot_owner_id

   def get_config_ini_copy(self):
      return copy.deepcopy(self._conf)
   
   # Common code for handling an error.
   # Does:
   #  - Printing stacktrace to stderr
   #  - Logging the error report
   #  - Sending the error report to the bot owner
   #  - Give user feedback in the channel if a command caused the error.
   # And for clarity, this function does NOT:
   #  - Reraise errors
   #  - Exit the program
   #  - Kill bot modules
   #
   # PARAMETERS:
   #    e: Error event that caused the error.
   #    cmd_msg: If the error involved a command, this is the message object
   #             of the command that triggered this error.
   #             If this is supplied, a message will be automatically sent to
   #             the channel to inform the user of the error.
   #    extra_info: An additional message content (string) to attach to the
   #                error report. This is useful for reporting more information
   #                about an error.
   #                This only appears in the error report.
   #    final_info: A string to append to the end of the error report.
   #                This string will appear in both the error report and
   #                command feedback message.
   #                For example, "THIS BOT WILL NOW RESTART."
   #
   # RETURNS: A string which may be sent back to a channel for user feedback.
   async def report_exception(self, e, **kwargs):
      try:
         traceback_str = traceback.format_exc()
         print(traceback_str, file=sys.stderr)

         # Obtain keyword arguments
         cmd_msg = kwargs.get("cmd_msg", None) # Discord Message Object
         handled_by = str(kwargs.get("handled_by", "")).strip()
         extra_info = str(kwargs.get("extra_info", "")).strip()
         final_info = str(kwargs.get("final_info", "")).strip()

         # STEP 1: Log error report and, if set to notify the bot owner, message
         #         them the error via PM.

         buf = "**EXCEPTION**"

         if len(handled_by) != 0:
            buf += "\n\n**This error is being handled by:**\n" + handled_by

         if not cmd_msg is None:
            buf0 = textwrap.dedent("""
               **The error was triggered by a command.**
               **From:** <#{msg.channel.id}> **in** {msg.server.name}
               **Command issued by:** <@{msg.author.id}>
               **Full Message:**
               {msg.content}
               """)
            buf0 = buf0.format(msg=cmd_msg).strip()
            buf += "\n\n" + buf0

         if len(extra_info) != 0:
            buf += "\n\n**Extra Info:**\n" + extra_info

         buf0 = textwrap.dedent("""\
            **Traceback:**
            ```
            {traceback_str}
            ```
            """)
         buf0 = buf0.format(traceback_str=traceback_str).strip()
         buf += "\n\n" + buf0

         if len(final_info) != 0:
            buf += "\n\n" + final_info

         logging.critical(buf)
         if self._message_bot_owner_on_error:
            try:
               await self.send_msg(self._bot_owner_obj, buf)
            except:
               buf = "FAILED TO SEND BOTOWNER STACKTRACE."
               logging.critical(buf)
               print(buf, file=sys.stderr)

         # STEP 2: Create user feedback, and if a command message was supplied,
         #         send this message into that channel.

         buf = None
         if e is None:
            buf = "**AN UNKNOWN ERROR OCCURRED.**"
         else:
            buf = textwrap.dedent("""\
               **AN ERROR OCCURRED.**
               **EXCEPTION:** {e_name}
               {e_des}
               """)
            buf = buf.format(e_name=type(e).__name__, e_des=str(e)).strip()

         buf += "\n<@{}> Check it out, will ya?".format(self.get_bot_owner_id())

         if len(final_info) != 0:
            buf += "\n\n" + final_info

         if not cmd_msg is None:
            try:
               await self.send_msg(cmd_msg, buf)
            except:
               buf0 = "FAILED TO MESSAGE BOT TERMINATION BACK TO THE CHANNEL."
               logging.critical(buf0)
               print(buf0, file=sys.stderr)
      except:
         buf = "ERROR WITHIN report_exception()!\n" + traceback.format_exc()
         buf += "\nThis error is completely unrecoverable."
         buf += "\nExiting with code 1."
         print(buf, file=sys.stderr)
         logging.critical(buf)
         sys.exit(1)
      return buf

   def message_cache_read(self, server_id, ch_id):
      return self.message_cache.read_messages(server_id, ch_id)

   def message_cache_debug_str(self):
      return self.message_cache.get_debugging_info()

async def _client_login(client, token):
   await client.on_message_lock.acquire() # To be released when ready.
   await client.on_member_join_lock.acquire() # To be released when ready.
   await client.on_member_remove_lock.acquire() # To be released when ready.
   # TODO: Acquire the lock elsewhere. It's a little out-of-place here...
   await client.login(token)
   await client.connect()
   return

def run(config_dict):
   loop = asyncio.get_event_loop()

   executor = ThreadPoolExecutor(5)
   loop.set_default_executor(executor)

   client = MentionBot(config_dict=config_dict)
   bot_user_token = config_dict["DEFAULT"]["bot_user_token"]
   print("Logging in...") # print("Logging in...", end="")
   try:
      loop.run_until_complete(_client_login(client, bot_user_token))
   except Exception as e:
      loop.run_until_complete(client.logout())
      print("Error launching client!")
      print(traceback.format_exc())
   finally:
      try:
         loop.close()
      except:
         print(traceback.format_exc())
   sys.exit(1) # Should only return on error.

if __name__ == '__main__':
   run()
