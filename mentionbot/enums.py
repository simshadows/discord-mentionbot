import enum

import errors

class PrivilegeLevel(enum.IntEnum):
   # IMPORTANT: PrivilegeLevel has two kinds of names:
   #                 1: A "common name" which users refer to the privilege levels by, and
   #                 2: A "canonical name" which the programmer refers to the privilege
   #                    levels by.
   #                 3: The integer value itself used for comparison and json-serializing.

   # UR_MOM = -1
   NO_PRIVILEGE = 0
   RESTRICTED_1 = 1000
   RESTRICTED_2 = 2000
   NEWBIE = 3000
   NORMAL = 4000
   REGULAR = 5000
   TRUSTED = 6000
   MODERATOR = 7000
   ADMIN = 8000
   SERVER_OWNER = 9000
   BOT_OWNER = 9001

   # Returns a list of triple-tuples. Example of tuple format:
   #     (PrivilegeLevel.BOT_OWNER, 9001, "Literally God")
   @classmethod
   def get_all_values(cls):
      all_values = []
      for (enum_type, enum_str) in _privilegelevel_enumtocommonname.items():
         all_values.append((enum_type, int(enum_type), enum_str))
      return get_all_values

   # Converts a PrivilegeLevel to a corresponding name.
   def enum_to_commonname(self):
      try:
         return _privilegelevel_enumtocommonname[self]
      except KeyError:
         raise RuntimeError

   @classmethod
   def commonname_to_enum(cls, text):
      try:
         return _privilegelevel_commonnametoenum[text]
      except KeyError:
         raise errors.DoesNotExist

   # TODO: Redo this better to be less verbose and less typo-prone.
   #       A typo here is a very serious security issue!
   @classmethod
   def int_to_enum_rounddown(self, int_value):
      if int_value > PrivilegeLevel.BOT_OWNER:
         raise RuntimeError # Extra security check.
      if int_value == PrivilegeLevel.BOT_OWNER:
         return PrivilegeLevel.BOT_OWNER
      if int_value >= PrivilegeLevel.SERVER_OWNER:
         return PrivilegeLevel.SERVER_OWNER
      if int_value >= PrivilegeLevel.ADMIN:
         return PrivilegeLevel.ADMIN
      if int_value >= PrivilegeLevel.MODERATOR:
         return PrivilegeLevel.MODERATOR
      if int_value >= PrivilegeLevel.TRUSTED:
         return PrivilegeLevel.TRUSTED
      if int_value >= PrivilegeLevel.REGULAR:
         return PrivilegeLevel.REGULAR
      if int_value >= PrivilegeLevel.NORMAL:
         return PrivilegeLevel.NORMAL
      if int_value >= PrivilegeLevel.NEWBIE:
         return PrivilegeLevel.NEWBIE
      if int_value >= PrivilegeLevel.RESTRICTED_2:
         return PrivilegeLevel.RESTRICTED_2
      if int_value >= PrivilegeLevel.RESTRICTED_1:
         return PrivilegeLevel.RESTRICTED_1
      return PrivilegeLevel.NO_PRIVILEGE

# IMPORTANT: This dict must match up exactly to the PrivilegeLevel types.
_privilegelevel_enumtocommonname = {
   # PrivilegeLevel.UR_MOM: "ur mom",
   PrivilegeLevel.NO_PRIVILEGE: "No Privileges",
   PrivilegeLevel.RESTRICTED_1: "Restricted1",
   PrivilegeLevel.RESTRICTED_2: "Restricted2",
   PrivilegeLevel.NEWBIE: "Newbie",
   PrivilegeLevel.NORMAL: "Normal",
   PrivilegeLevel.REGULAR: "Regular",
   PrivilegeLevel.TRUSTED: "Trusted",
   PrivilegeLevel.MODERATOR: "Moderator",
   PrivilegeLevel.ADMIN: "Admin",
   PrivilegeLevel.SERVER_OWNER: "Server Owner",
   PrivilegeLevel.BOT_OWNER: "Literally God"
}

# It would be nice if we can have bi-directional maps instead of this...
_privilegelevel_commonnametoenum = {v: k for (k, v) in _privilegelevel_enumtocommonname.items()}
