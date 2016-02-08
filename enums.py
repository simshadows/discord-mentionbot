import enum

class PrivilegeLevel(enum.IntEnum):
   UR_MOM = -1
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

   def to_string(self):
      return _privilegelevel_dict[self]

   # Returns a list of triple-tuples. Example of tuple format:
   #     (PrivilegeLevel.BOT_OWNER, 9001, "Literally God")
   @classmethod
   def get_all_values(self):
      all_values = []
      for (enum_type, enum_str) in _privilegelevel_dict.iteritems():
         all_values.append((enum_type, int(enum_type), enum_str))
      return get_all_values

# IMPORTANT: This dict must match up exactly to the PrivilegeLevel types.
_privilegelevel_dict = {
   PrivilegeLevel.UR_MOM: "ur mom",
   PrivilegeLevel.NO_PRIVILEGE: "No Privileges",
   PrivilegeLevel.RESTRICTED_1: "Restricted #1",
   PrivilegeLevel.RESTRICTED_2: "Restricted #2",
   PrivilegeLevel.NEWBIE: "Newbie",
   PrivilegeLevel.NORMAL: "Normal",
   PrivilegeLevel.REGULAR: "Regular",
   PrivilegeLevel.TRUSTED: "Trusted",
   PrivilegeLevel.MODERATOR: "Moderator",
   PrivilegeLevel.ADMIN: "Admin",
   PrivilegeLevel.SERVER_OWNER: "Server Owner",
   PrivilegeLevel.BOT_OWNER: "Literally God"
}