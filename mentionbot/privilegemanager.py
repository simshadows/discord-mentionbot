import discord

from enums import PrivilegeLevel

# Since users often have multiple roles, it's the highest role that counts.
# TODO: Allow for polling of server owner (in case of owner swap)?
class PrivilegeManager:

   # PRECONDITION: default_privilege is a PrivilegeLevel
   def __init__(self, botowner_ID, serverowner_ID, default_privilege=PrivilegeLevel.NORMAL):
      self._BOTOWNER_ID = botowner_ID
      self._SERVER_OWNER_ID = serverowner_ID
      self._DEFAULT_PRIVILEGE_LEVEL = default_privilege
      # self._role_privileges = {} # FORMAT: Dict<role_ID -> PrivilegeLevel>
      return

   # For now, we will only give bot owner and server owner additional privilege.
   # # Note: This will silently overwrite an existing privilege level.
   # # PRECONDITION: privilege is a PrivilegeLevel
   # # PRECONDITION: @everyone should **NEVER** **EVER** be assigned a privilege level.
   # #               (It will make everyone have, at minimum, that privilege level.)
   # # TODO: Implement a check for @everyone assignment. This is a critical security gate!
   # def set_role_privilege(self, role_ID, privilege):
   #    if privilege >= PrivilegeLevel.SERVER_OWNER:
   #       # This critical security check may save a lot of pain later on.
   #       raise RuntimeError("Please don't assign someone a role >= SERVER_OWNER.")
   #    self._role_privileges[role_ID] = privilege
   #    return

   # PARAMETER: user = A user object to query.
   def get_privilege_level(self, user):
      if user.id == self._BOTOWNER_ID:
         return PrivilegeLevel.BOT_OWNER
      elif user.id == self._SERVER_OWNER_ID:
         return PrivilegeLevel.SERVER_OWNER
      else:
         return self._DEFAULT_PRIVILEGE_LEVEL