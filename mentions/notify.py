import asyncio

import discord

import clientextended

class MentionNotifyModule:

   # PARAMETER: enabled - If false, the module is disabled.
   def __init__(self, client, enabled=True):
      self._client = client
      self._enabled = enabled
      return

   # Call this every time a message is received.
   async def on_message(self, msg):
      if not self._enabled:
         return
      
      for member in msg.mentions:
         print("Checking user up... " + member.name + " " + str(member.status))
         if str(member.status) != "offline":
            continue
         buf = "Hello! <@" + msg.author.id + "> mentioned you in <#" + msg.channel.id + "> while you were offline."
         buf += "\n**Message contents are as follows:**"
         buf += "\n" + msg.content
         await self._client.send_msg(member, buf)
         print("MentionNotifyModule: A notification was sent!")

      return

   # Call this to process a command.
   async def process_cmd(self, substr, msg):
      await self._client.send_msg(member, "The notify module is still under development. Sorry!")
      return

   # True if notifications is enabled, False otherwise.
   def is_enabled(self):
      return self._enabled

   # Enable notifications.
   def enable(self):
      self._enabled = True
      return

   # Disable notifications.
   def disable(self):
      self._enabled = False
      return



