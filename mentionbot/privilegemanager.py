import discord

from . import errors
from .enums import PrivilegeLevel

# Since users often have multiple roles, it's the highest role that counts.
# TODO: Allow for polling of server owner (in case of owner swap)?
class PrivilegeManager:

   # PRECONDITION: default_privilege is a PrivilegeLevel
   def __init__(self, botowner_ID, serverowner_ID, default_privilege=PrivilegeLevel.NORMAL):
      self._botowner_ID = botowner_ID
      self._serverowner_ID = serverowner_ID
      self._default_privilege_level = PrivilegeLevel.NORMAL

      # THESE ARE CURRENTLY UNUSED UNTIL THE NEXT COMMIT.
      self._role_privileges = {} # FORMAT: Maps role name -> privilege level
      self._user_privileges = {} # FORMAT: Maps user ID -> privilege level
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

   # PARAMETER: member = A member object to query.
   def get_privilege_level(self, member):
      # Highest priority is bot owner and server owner.
      if member.id == self._botowner_ID:
         return PrivilegeLevel.BOT_OWNER
      elif member.id == self._serverowner_ID:
         return PrivilegeLevel.SERVER_OWNER

      # Assigned user privilege level has next priority.
      try:
         user_priv = self._user_privileges[member.id]
         return user_priv
      except KeyError:
         pass

      # Role privilege level has next priority.
      # If the member has been assigned (either directly as a member privilege level,
      # or through role privilege levels) a privilege level lower than the default, the
      # lowest of these levels is the overall level. Else, if the user has been assigned
      # a privilege level higher or equal than the default, then the highest of those
      # levels is the overall level. Else, if the user is not assigned a privilege level,
      # then they get the default privilege level.

      lower_priv = self._default_privilege_level
      higher_priv = self._default_privilege_level - 1
      for role in member.roles:
         try:
            role_priv = self._role_privileges[role.name]
            if role_priv < lower_priv:
               lower_priv = role_priv
            elif role_priv >= higher_priv:
               higher_priv = role_priv
         except KeyError:
            pass

      if lower_priv < self._default_privilege_level:
         return lower_priv
      elif higher_priv >= self._default_privilege_level:
         return higher_priv
      else:
         # And finally, assign default if no privilege levels have been found.
         return self._default_privilege_level

   # This gets a json-serializable data structure of the privilege settings.
   def get_json_settings_struct(self):
      serialized_role_privileges = {}
      for (role_name, priv_level) in self._role_privileges.items():
         serialized_role_privileges[role_name] = int(priv_level)

      serialized_user_privileges = {}
      for (user_ID, priv_level) in self._user_privileges.items():
         serialized_user_privileges[user_ID] = int(priv_level)

      settings = {
         "role privileges": serialized_role_privileges,
         "user privileges": serialized_user_privileges,
      }
      return settings

   # PRECONDITION: settings is a dict.
   def apply_json_settings_struct(self, settings):
      self._role_privileges = {}
      try:
         for (role_name, priv_int) in settings["role privileges"].items():
            self._role_privileges[role_name] = PrivilegeLevel.int_to_enum_rounddown(priv_int)
      except KeyError:
         print("WARNING: No role privileges settings found. Setting up empty map.")
         # TODO: Improve data verification!!!

      self._user_privileges = {}
      try:
         for (user_ID, priv_int) in settings["user privileges"].items():
            self._user_privileges[user_ID] = PrivilegeLevel.int_to_enum_rounddown(priv_int)
      except KeyError:
         print("WARNING: No user privileges settings found. Setting up empty map.")
         # TODO: Improve data verification!!!
      return

   # PARAMETER: role_name - The role name to be assigned the privilege level.
   #                        This should be a valid role name, though it still works otherwise.
   # PARAMETER: privilege_level - The privilege level to be assigned to the role.
   #                              if it's None, then the privilege level is instead unassigned.
   # PRECONDITION: role_name is a string.
   # PRECONDITION: PrivilegeLevel.NO_PRIVILEGE <= privilege_level < PrivilegeLevel.SERVER_OWNER
   #               Please never assign anything outside of that range.
   # THROWS: errors.NoRecordExists - Thrown if unassigning an already not assigned role a
   #                                 privilege level.
   def assign_role_privileges(self, role_name, privilege_level):
      if privilege_level is None:
         try:
            del self._role_privileges[role_name]
         except KeyError:
            raise errors.NoRecordExists
      else:
         self._role_privileges[role_name] = privilege_level
      return

   # PARAMETER: user_ID - The user ID to be assigned the privilege level.
   #                      This should be an existing user, though it still works otherwise.
   # PARAMETER: privilege_level - The privilege level to be assigned to the user.
   #                              if it's None, then the privilege level is instead unassigned.
   # PRECONDITION: user_ID is a string.
   # PRECONDITION: PrivilegeLevel.NO_PRIVILEGE <= privilege_level < PrivilegeLevel.SERVER_OWNER
   #               Please never assign anything outside of that range.
   # THROWS: errors.NoRecordExists - Thrown if unassigning an already not assigned user a
   #                                 privilege level.
   def assign_user_privileges(self, user_ID, privilege_level):
      if privilege_level is None:
         try:
            del self._user_privileges[user_ID]
         except KeyError:
            raise errors.NoRecordExists
      else:
         self._user_privileges[user_ID] = privilege_level
      return

   def get_role_privileges(self):
      return self._role_privileges.items()

   def get_user_privileges(self):
      return self._user_privileges.items()

