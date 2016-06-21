import abc

from .errors import *

class CompiledNode(abc.ABC):
   _all_basic_types = [type(None), str, int, float, bool]
   _all_accepted_types = _basic_types + [list, dict]
   
   _all_basic_types_set = set(_all_basic_types)
   _all_accepted_types_set = set(_all_accepted_types)

   def __init__(self, schema):
      self._initialize(schema)
      return

   # Chooses the appropriate type of node to compile automatically.
   @classmethod
   def compile(cls, schema):
      assert type(schema) in cls._all_accepted_types_set
      to_compile = None
      basic_type = cls._get_basic_type(schema)
      if not basic_type is None:
         to_compile = BasicTypeNode
      elif isinstance(schema, list):
         to_compile = ListTypeNode
      else:
         assert isinstance(schema, dict)
         if "$class" in schema:
            to_compile = DictObjTypeNode
            # A bad $class value will be caught in the node constructor.
         else:
            # Then the object is not to be treated as an object of arbitrary
            # keys.
            to_compile = ObjTypeNode
      return to_compile(schema)

   # If the object is a basic type, return exactly what the basic
   # type is. This handles inheritance.
   #     E.g. if obj is some defaultdict, then this method returns
   #     the dict class.
   # If the object is not a basic type, returns None.
   @classmethod
   def _get_basic_type(cls, obj):
      for basic_type in cls._all_basic_types:
         if isinstance(obj, basic_type):
            return basic_type
      return None

   # Sets up the specific type of node.
   @abc.abstractmethod
   def _initialize(self, schema):
      raise NotImplementedError

   # Verifies the data object against the schema object.
   @abc.abstractmethod
   def verify(self, data, schema):
      raise NotImplementedError


class BasicTypeNode(CompiledNode):
   def _initialize(self, schema):
      raise NotImplementedError

   def verify(self, data, schema):
      raise NotImplementedError


class ListTypeNode(CompiledNode):
   def _initialize(self, schema):
      raise NotImplementedError

   def verify(self, data, schema):
      raise NotImplementedError


class DictObjTypeNode(CompiledNode):
   def _initialize(self, schema):
      raise NotImplementedError

   def verify(self, data, schema):
      raise NotImplementedError


class ObjTypeNode(CompiledNode):
   def _initialize(self, schema):
      raise NotImplementedError

   def verify(self, data, schema):
      raise NotImplementedError


