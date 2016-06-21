# This module is written to be a simple alternative to jsonschema.
# Although jsonschema could work for me, it doesn't offer automatic default
# value handling as standard. Additionally, I'm interested in making a concise
# schema representation.

from .errors import *
from .compilednode import CompiledNode

class DefaultJSONVerifier:
   _all_basic_types = [type(None), str, int, float, bool]

   def __init__(self, schema):
      if not isinstance(schema, dict):
      raise TypeError("Schema object must be a dict.")
      self._compiled = self._compile_schema(schema)
      return


   @classmethod
   def _compile_schema(cls, schema):
      assert isinstance(schema, dict)
      c = cls._compile_object(schema)
      return c

   @classmethod
   def _compile_basic_type(cls, x):
      
      def test_args()
         for basic_type in cls._all_basic_types:

         return False
      assert test_type()

      return type(x)

   @classmethod
   def _compile_list(cls, x):
      assert isinstance
      return type(x)

   # Objects get compiled here.
   @classmethod
   def _compile_object(cls, schema):
      c = {}
      for (k, v) in schema.items():
         # Key must be a string.
         if not isinstance(k, str):
            raise DefaultJSONTypeError(None)
         # Value must be a non-empty list.
         if (not isinstance(v, list)) or (len(v) == 0):
               raise DefaultJSONTypeError(k)
         # Prepare a structure for the particular key.
         c[k] = {
            "default": None,
            "basic_types_allowed": set(),
            "lists_allowed": [],
            "dicts_allowed": [],
         }
         
         def list_compile(list_obj):
            ret = []

            return ret

         for i in v:
            if self._is_basic_data(i):
               c["basic_types_allowed"].add(i)
            elif isinstance(i, list):
               c["lists_allowed"].append(list_compile(i))
            elif isinstance(i, dict):
               # We must find out if it's an associative array.

      return c

   

   # Returns True if item is a basic data item.
   @classmethod
   def _is_basic_data(cls, item):
      for t in cls._all_basic_types:
         if isinstance(item, t):
            return True
      return False



