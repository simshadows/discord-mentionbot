
import discord

class MentionNotifyModule:

   # PARAMETER: enabled - If false, the module is disabled.
   def __init__(self, client, enabled=True):
      self._client = client
      self._enabled = enabled
      return

   # Call this every time a message is received.
   def on_message(self, msg):
      if not self._enabled:
         return
      
      for member in msg.mentions:
         if member.status != "offline":
            break
         buf = "Hello! <@" + msg.author.id + "> mentioned you in <#" + msg.channel.id + "> while you were offline."
         buf += "\n**Message contents are as follows:**"
         buf += "\n" + msg.content
         self._client.send_msg(member, buf)
         print("MentionNotifyModule: A notification was sent!")

      return

   # Call this to process a command.
   def process_cmd(self, substr, msg):
      self._client.send_msg(member, "The notify module is still under development. Sorry!")

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



