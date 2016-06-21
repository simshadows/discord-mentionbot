from copy import deepcopy

class AttributeDictWrapper:

   # IMPORTANT NOTE: This class modifies the data dictionary it gets passed.
   # These changes, however, are logged and may be retrieved in human-readable
   # text via get_change_log().
   #
   # Arguments:
   #     data_dict: A dictionary used for data.
   #     default_dict: The dictionary used as a fallback if the original
   #        data dictionary is missing it.
   def __init__(self, data_dict, default_dict):
      assert isinstance(data_dict, dict)
      assert isinstance(default_dict, dict)
      self._data = data_dict
      self._default = default_dict

      # This logs the modifications in a human-readable format.
      # Ordinarily, this wrapper provides data recovery by replacing bad or
      # missing values with default values.
      self._modifications_log = [] # List of strings to be appended with "\n".
      return

   def _log_change(self, text):
      assert isinstance(text, str) and len(text) > 0
      self._modifications_log.append(text)
      return
   
   # Arguments:
   #     attr_name: The name of the attribute.
   #     other_types: A list of the other types that will pass verification.
   #        None itself may be part of this list to mean that the value may
   #           be None/null.
   #     accept_if: A function to verify the value.
   #        Function requirements:
   #           Takes only one argument, which is the data.
   #           This argument is guaranteed to be
   #           Returns True if the data is acceptable.
   #           Returns False otherwise.
   def get(self, attr_name, other_types=[], accept_if=None):
      assert isinstance(attr_name, str)
      assert callable(accept_if) or (accept_if is None)
      default_value = self._default[attr_name] # May raise KeyError.
      if (not accept_if is None) and (not accept_if(default_value)):
         raise RuntimeError("The default value didn't pass verification!")

      assert isinstance(other_types, list)
      allowed_types = other_types
      allowed_types.append(type(default_value))

      if attr_name in self._data:
         data = self._data[attr_name]
         def log_replacement(extra_text, old):
            self._log_change("\"{}\" {}".format(attr_name, extra_text))
            self._log_change("   Old value: " + str(old))
            self._log_change("   New value: " + str(default_value))
            return
         def not_an_allowed_type(x):
            for type_obj in allowed_types:
               if isinstance(x, type_obj):
                  return False
            return True
         if not_an_allowed_type(data):
            buf = "is not an acceptable type ({}).".format(type(data).__name__)
            log_replacement(buf, data)
            data = default_value
         elif (not accept_if is None) and (not accept_if(data)):
            log_replacement("didn't pass the verification function.", data)
            data = default_value
         return data
      else:
         self._log_change("Filled missing attribute \"{}\".".format(attr_name))
         self._data[attr_name] = default_value

   def get_change_log(self):
      if len(self._modifications_log) > 0:
         text = "\n".join(self._modifications_log)
         self._modifications_log = [].append(text)
      else:
         text = ""
      return text
