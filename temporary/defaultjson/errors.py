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
