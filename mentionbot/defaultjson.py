# This module is written to be a simple alternative to jsonschema.
# Although jsonschema could work for me, it doesn't offer automatic default
# value handling as standard. Additionally, I'm interested in making a concise
# schema representation.

# This functions both as a mini-tutorial and a test case.
sample_schema = {
   "attrA": ["I'm a default value."],
   "attrB": ["I also require the matching data to be a string."],
   "attrC": ["I'm default", None], # But I can also be NULL.
   "attrD": [3, "Number 3 is default, but I can also be a string."],
   "attrE": [42, None, "Default 42, but can be NULL or String."],
   "attrF": [{
      "attr1": "I'm a default value for sample_schema['attrA']['attr1'].",
      "attr2": [42, None, "I work the same as attrE."],
      # Note: This object is itself a schema that follows much the same rules, just
      #       another level higher.
   }],
   "attrG": [["I", "am", "this", "list", "by", "default."]],
   # attrG must also be a list of strings.
   "attrH": [[]], # I am an empty list by default.
   # attrH also will ONLY match to empty lists.
   "attrI": [[], ["I default as and can be empty, but I can have strings and/or ints.", 42]],
   "attrJ": [[{
      "attr1": "attrJ is a list of objects by default.",
      "attr2": "Each of these objects has two attributes: attr1 and attr2.",
   }]],
   # NOTE: The list can actually be empty. A higher-level verification phase is required to
   # check for other conditions, i.e. if the list must never be empty.
   "attrK": [42, 42.0], # My default is 42, and I can be an int or a float.
   "attrL": [{
      "$class": "dict",
      "key1": "$class is an identifier, not an key.",
      "key2": "$class says that this object is to be treated as a dict.",
      "key3": "This is useful if, say, we want to store the privilege level",
      "key4": "of each member of a server.",
      "key5": "However, this object is treated completely differently to",
      "key6": "a regular object used to contain attributes, as we've assumed",
      "key7": "so far. All the keys except anything starting with '$' make up",
      "key8": "the default value of the entire object. However...",
      "$types": [42, "string!!!"],
      "key9": "$types says that the values associated with each key can be",
      "key10": "integers or strings. Thus, we can do:"
      "key11": 9001,
   }], # Note that empty dictionaries don't fail verification.
   "attrM": [[], None], # I am an empty list by default, but can also be NULL.
}
sample_data_success1 = {
   "attrA": "some arbitrary string",
   "attrB": "some arbitrary string",
   "attrC": None,
   "attrD": 9001,
   "attrE": None,
   "attrF": {
      "attr1": "some arbitrary string",
      "attr2": 9001,
   },
   "attrG": ["some arbitrary string", "some arbitrary string"],
   "attrH": [],
   "attrI": ["str", 123, "another arbitrary string", -456],
   "attrJ": [[{
      "attr1": "some arbitrary string",
      "attr2": "some arbitrary string",
   }]],
   "attrK": [420, 420.9001, -298436, -934.11],
   "attrL": [{
      "arbitarrykey1": "arbitraryvalue1",
      "arbitarrykey2": "arbitraryvalue2",
      "arbitarrykey3": 23456435634,
      "arbitarrykey4": -2342,
   }],
   "attrM": None,
}
sample_data_fail1 = {
   "attrA": 123, # FAIL HERE
   "attrB": "some arbitrary string",
   "attrC": None,
   "attrD": 9001,
   "attrE": None,
   "attrF": {
      "attr1": "some arbitrary string",
      "attr2": 9001,
   },
   "attrG": ["some arbitrary string", "some arbitrary string"],
   "attrH": [],
   "attrI": ["str", 123, "another arbitrary string", -456],
   "attrJ": [[{
      "attr1": "some arbitrary string",
      "attr2": "some arbitrary string",
   }]],
   "attrK": [420, 420.9001, -298436, -934.11],
   "attrL": [{
      "arbitarrykey1": "arbitraryvalue1",
      "arbitarrykey2": "arbitraryvalue2",
      "arbitarrykey3": 23456435634,
      "arbitarrykey4": -2342,
   }],
   "attrM": None,
}
sample_data_fail2 = {
   "attrA": "some arbitrary string",
   "attrB": "some arbitrary string",
   "attrC": None,
   "attrD": 9001,
   "attrE": None,
   "attrF": {
      "attr1": "some arbitrary string",
      "attr2": 9001,
   },
   "attrG": ["some arbitrary string", "some arbitrary string"],
   "attrH": [],
   "attrI": ["str", 123, "another arbitrary string", -456],
   "attrJ": [[{
      "attr1": 123, # FAIL HERE
      "attr2": "some arbitrary string",
   }]],
   "attrK": [420, 420.9001, -298436, -934.11],
   "attrL": [{
      "arbitarrykey1": "arbitraryvalue1",
      "arbitarrykey2": "arbitraryvalue2",
      "arbitarrykey3": 23456435634,
      "arbitarrykey4": -2342,
   }],
   "attrM": None,
}
sample_data_fail3 = {
   "attrA": "some arbitrary string",
   "attrB": "some arbitrary string",
   "attrC": None,
   "attrD": 9001,
   "attrE": None,
   "attrF": {
      "attr1": "some arbitrary string",
      "attr2": 9001,
   },
   "attrG": ["some arbitrary string", "some arbitrary string"],
   "attrH": [],
   "attrI": ["str", 123, "another arbitrary string", -456, 125.1], # FAIL HERE
   "attrJ": [[{
      "attr1": "some arbitrary string",
      "attr2": "some arbitrary string",
   }]],
   "attrK": [420, 420.9001, -298436, -934.11],
   "attrL": [{
      "arbitarrykey1": "arbitraryvalue1",
      "arbitarrykey2": "arbitraryvalue2",
      "arbitarrykey3": 23456435634,
      "arbitarrykey4": -2342,
   }],
   "attrM": None,
}
sample_data_success2 = {
   "attrA": "",
   "attrB": "",
   "attrC": None,
   "attrD": 0,
   "attrE": None,
   "attrF": {
      "attr1": "",
      "attr2": 0,
   },
   "attrG": [],
   "attrH": [],
   "attrI": [],
   "attrJ": [],
   "attrK": [],
   "attrL": [{}],
   "attrM": None,
}



class DefaultJSONTypeError(TypeError):
   def __init__(self, attr_name):
      self.json_attrlist = []
      if not attr_name is None:
         assert isinstance(attr_name, str)
         self.json_attrlist.append(attr_name)
      return
   def append_attr(self, attr_name)
      assert isinstance(attr_name, str)
      self.json_attrlist.append(attr_name)
      return


class DefaultJSONVerifier:
   _basic_types = [type(None), str, int, float, bool]

   def __init__(self, schema):
      if not isinstance(schema, dict):
      raise TypeError("Schema object must be a dict.")
      self._compiled = self._compile_object(schema)
      return

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
         for i in v:
            if self._is_basic_data(i):
      return c

   # Returns True if item is a basic data item.
   @classmethod
   def _is_basic_data(cls, item):
      for t in cls._basic_types:
         if isinstance(item, t):
            return True
      return False

      # Returns nothing, or raises an exception.
      def verify_object(sub_schema):
         for (k, v) in sub_schema.items():
            
            
            for i in v:
               if is_basic_data(i):
                  continue
               if isinstance(i, dict):
                  try:
                     verify_object(i)
                  except DefaultJSONTypeError as e:
                     e.append_attr(k)
                     raise
               if isinstance(i, list):
                  for i2 in i:

      try:
         verify_object(schema)
      except DefaultJSONTypeError as e:
         attrs = ", ".join(e.json_attrlist)
         assert len(attrs) > 0
         raise TypeError("Found a bad type: " + attrs)
      return



# Returns nothing.
# Raises an exception if a problem with the schema is found.
def verify_schema(schema):







# Returns nothing.
# Raises an exception if a problem with the data is found.
# PRECONDITION: The schema has been checked with verify_schema().
def verify(data, schema):
   raise NotImplementedError
   return



