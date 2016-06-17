import os, asyncio
from . import utils, errors

_errors_dirname = "unreported_errors/"
_file_extension = ".txt"

# Only use this if there is no chance for another logical execution line to
# enter this object simultaneously.
def unsynced_add_to_holding(text, cache_dirname):
   assert isinstance(text, str) and len(text) != 0
   dir_path = cache_dirname + _errors_dirname
   highest_number = -1
   for file_name in os.listdir(dir_path):
      if file_name.endswith(file_extension):
         no_extension = file_name[:-len(_file_extension)]
         file_number = None
         try:
            file_number = int(no_extension)
         except ValueError:
            continue
         if file_number > highest_number:
            highest_number = file_number
   fname_to_write = dir_path + str(highest_number + 1)
   fname_to_write += _file_extension
   with open(fname_to_write, "w") as f:
      f.write(text)
   return

# If the bot catches errors that it is unable to report back to the owner via
# PM, it should pass a string containing information to an instance of
# ErrorReportHolder, to be messaged to the owner later when the bot is able
# to do so.
class ErrorReportHolder:
   def __init__(self, cache_dirname):
      # This lock protects the concurrent modification of files in the
      # unreported_errors directory, as well as the _last_taken attribute.
      self._dir_lock = asyncio.Lock()
      self._dir_path = cache_dirname + _errors_dirname
      self._cache_dirname = cache_dirname
      self._last_taken = -1
      return

   def _int_to_filename(self, number):
      return self._dir_path + str(number) + _file_extension

   @utils.synchronized("_dir_lock")
   async def add_to_holding(self, text):
      unsynced_add_to_holding(text, self._cache_dirname)
      return

   # Returns a list of error reports in chronological order, starting from the
   # earliest.
   # However, the first item is a list of files in the unreported_errors
   # directory.
   # TODO: Turn this into a generator maybe?
   # TODO: Also consider running this in a generator?
   @utils.synchronized("_dir_lock")
   async def items(self):
      items_list = ["\n".join(os.listdir(self._dir_path))]
      old_last_taken = self._last_taken # Used for an assert.
      file_number = 0
      while True:
         file_name = self._int_to_filename(file_number)
         if not os.path.isfile(file_name):
            break
         buf = None
         with open(file_name, "r") as f:
            buf = f.read()
         items_list.append(buf)
         self._last_taken = file_number
         file_number += 1
      assert old_last_taken <= self._last_taken
      return items_list

   # Clears all items that have been taken via items().
   # (The motivation for the existence of this method is to only flush data
   # if the data has been delivered.)
   @utils.synchronized("_dir_lock")
   async def flush(self):
      # First remove all existing files.
      file_number = 0
      while file_number <= self._last_taken:
         file_name = self._int_to_filename(file_number)
         assert os.path.isfile(file_name)
         os.remove(file_name)
         file_number += 1
      # Then, shift down the remaining.
      offset = file_number - 1
      while True:
         file_name = self._int_to_filename(file_number)
         if not os.path.isfile(file_name):
            break
         new_file_name = self._int_to_filename(file_number - offset)
         os.rename(file_name, new_file_name)
         file_number += 1
      return
