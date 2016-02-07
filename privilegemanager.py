# TODO: Replace this placeholder implementation.
class PrivilegeManager:

   def __init__(self, client):
      self._BOTOWNER_ID = client.BOTOWNER_ID
      return

   def get_privilege_level(self, user_ID):
      if user_ID == self._BOTOWNER_ID:
         return 1
      else:
         return 0