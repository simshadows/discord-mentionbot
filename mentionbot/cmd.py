import inspect
import enum
import abc

from . import utils, errors
from .enums import PrivilegeLevel

###########################################################################################
# UTILITY FUNCTIONS #######################################################################
###########################################################################################

# Returns the appropriate function object from a dictionary of function objects filled
# by the "add()" decorator while also handling checks. As long as the dictionary has
# been filled correctly with properly decorated function objects, it is guaranteed to
# either return a working command function, or raise appropriate exceptions.
# 
# THROWS: UnknownCommandError - Thrown if cmd_name is not in the dictionary.
# THROWS: CommandPrivilegeError - Thrown if cmd_name is in the dictionary, but
#                                 privilege_level is not high enough to execute it.
def get(cmd_dict, cmd_name, privilege_level):
   try:
      cmd_to_execute = cmd_dict[cmd_name]
      if privilege_level < cmd_to_execute.cmd_meta.get_min_priv():
            raise errors.CommandPrivilegeError
      return cmd_to_execute
   except KeyError:
      raise errors.InvalidCommandArgumentsError

async def compose_help_summary(cmd_dict, privilege_level):
   # Make separate help strings for each group.
   seen_set = set()
   cats_dict = {} # FORMAT: category name string -> help content string
   for (cmd_name, cmd_obj) in cmd_dict.items():
      if not cmd_obj in seen_set:
         if privilege_level < cmd_obj.cmd_meta.get_min_priv():
            continue
         seen_set.add(cmd_obj)
         help_str = await get_help_summary(cmd_obj)
         if len(help_str) != 0:
            cat_name = (await cmd_obj.cmd_meta.get_help_summary())[1] # TODO: Messy...
            if cat_name is None:
               cat_name = ""
            cat_buf = None
            if cat_name in cats_dict:
               cat_buf = cats_dict[cat_name]
            else:
               cat_buf = ""
            cats_dict[cat_name] = cat_buf + help_str + "\n"

   # Sort each category and put into a list.
   cats_list = [] # FORMAT: [(cat_name, cat_buf)]
   no_cat_buf = None # String for commands with no/blank category.
   for (cat_name, cat_buf) in cats_dict.items():
      cat_buf = "\n".join(sorted(cat_buf.splitlines(), key=lambda e: e.lower()))
      if len(cat_name) == 0:
         no_cat_buf = cat_buf
      else:
         cats_list.append((cat_name, cat_buf))
   
   # Sort the categories list
   if len(cats_list) != 0:
      cats_list = sorted(cats_list, key=lambda e: e[0].lower())

   # Put together and return help content string.
   buf = None
   if not no_cat_buf is None:
      buf = no_cat_buf
   else:
      buf = ""
   for (cat_name, cat_buf) in cats_list:
      buf += "\n\n**" + cat_name + "**:\n" + cat_buf
   if no_cat_buf is None:
      return buf[2:] # Strip off first two newlines.
   else:
      return buf

# This method is not normally used anywhere other than compose_help_summary().
# This method also processes "{cmd}" -> "{bc}{c}" and substitutes in the
# value of "{c}".
async def get_help_summary(cmd_obj):
   kwargs = {
      "cmd": "{p}{b}" + cmd_obj.cmd_meta.get_aliases()[0],
      "bc": "{p}{b}",
      "p": "{p}",
      "b": "{b}",
      "c": cmd_obj.cmd_meta.get_aliases()[0],
   }
   return (await cmd_obj.cmd_meta.get_help_summary())[0].format(**kwargs)

async def get_help_detail(cmd_obj):
   return await cmd_obj.cmd_meta.get_help_detail()

# Carries out "{modhelp}" -> "{p}help {mod}" evaluation, while also
# substituting "{mod}".
def format_mod_evaluate(content_str, *, mod=None):
   return content_str.format(modhelp="{p}help " + mod, mod=mod, p="{p}")

###########################################################################################
# FUNCTION DECORATORS #####################################################################
###########################################################################################

# IMPORTANT: Command function decorators must never wrap!
#            Wrapping functions may hide other decorated attributes.

# Decorator for adding commands to a dictionary.
# PARAMETER: cmd_dict - The dictionary in which the command is to be added to.
# PARAMETER: *cmd_names - List of names the command is to be mapped to.
# PARAMETER: default - (bool) If true, list the command as a default command.
# PARAMETER: top - (bool or list<str>) For defining top-level aliases.
#                  If False, command does not have any top-level aliases.
#                  If True, all of the aliases are also top-level aliases.
#                  If it's a string or a non-empty list of strings, then those
#                  strings are used as top-level aliases.
# PARAMETER: category - (str or None) For defining a category name, useful by
#                       certain HelpNode aggregators for organizing lines.
#                       If None, then no category.
#                       If a string, then that string is used as the category
#                       name.
# PARAMETER: minimum_privilege - A minimum privilege level normally required
#                                to use the command.
#                                (Implementation note: If minimum_privilege
#                                is None, then the default value in the
#                                CommandMeta object is kept.)
#     # THE FOLLOWING PARAMETER IS CURRENTLY STILL PLANNED AND THUS UNUSED.
#     # PARAMETER: help_pages - A CommandHelpPage object (or list of) in which the
#     #                         command is to be added to.
# Note: minimum_privilege is still used as 
def add(cmd_dict, *cmd_names, **kwargs):
   assert isinstance(cmd_dict, dict)

   # Get kwargs
   default = bool(kwargs.get("default", False))
   top = kwargs.get("top", False)
   category = kwargs.get("category", None)
   minimum_privilege = kwargs.get("minimum_privilege", None)

   def function_decorator(function):
      _ensure_cmd_obj(function)
      function.cmd_meta.set_aliases(cmd_names)
      if isinstance(top, bool):
         if top:
            function.cmd_meta.set_top_aliases_existing()
      else:
         function.cmd_meta.set_top_aliases_explicitly(list(top))
      if not category is None:
         assert isinstance(category, str)
         function.cmd_meta.set_help_category(category)
      if not minimum_privilege is None:
         assert isinstance(minimum_privilege, PrivilegeLevel)
         function.cmd_meta.set_min_priv(minimum_privilege_level)

      # Add the function to cmd_dict
      for cmd_name in cmd_names:
         assert isinstance(cmd_name, str)
         if cmd_name in cmd_dict:
            raise RuntimeError("Command with alias '{}' already exists.".format(cmd_name))
         cmd_dict[cmd_name] = function
      if default:
         if "" in cmd_dict:
            raise RuntimeError("A default command has already defined.")
         cmd_dict[""] = function
      return function
   return function_decorator

# Decorator adds an attribute named "privilege_gate" to a function object.
# This attribute is simply checked before execution.
def minimum_privilege(minimum_privilege_level):
   assert isinstance(minimum_privilege_level, PrivilegeLevel)
   def function_decorator(function):
      _ensure_cmd_obj(function)
      function.cmd_meta.set_min_priv(minimum_privilege_level)
      return function
   return function_decorator

# Decorator adds an attribute named "help_category" to a function object.
# This attribute is used when composing help messages, for grouping.
# When no category has been assigned (i.e. the decorator is not used),
# the composed help message will group the command along with all the
# other ungrouped commands.
def category(text):
   assert isinstance(text, str)
   def function_decorator(function):
      _ensure_cmd_obj(function)
      function.cmd_meta.set_help_category(text)
      return function
   return function_decorator

###########################################################################################
###########################################################################################
###########################################################################################

def _ensure_cmd_obj(function):
   if not hasattr(function, "cmd_meta"):
      function.cmd_meta = CommandMeta(function)
   return

class HelpNode(abc.ABC):
   """
   This defines an object that can be referenced as a node in a directed graph
   of help node objects.

   HelpNode implementors:
      - ServerModuleGroup (as this is an entrypoint)
      - ServerModuleWrapper
      - CommandHelpPage
      - CommandMeta

   SUBSTITUTION:

      PROPOSED SCHEME
         Commands are always "{cmd}".
         STEP 1 (leaves) for CommandMeta:
            IF it's marked as a top-level command:
               "{cmd}" becomes "{p}[top_level_alias]"
            ELSE:
               "{cmd}" becomes "{p}{grp}[cmd_alias]" # cmd_alias is the primary
                                                     # alias used by the
                                                     # aggregator underneath.
         STEP 2 (aggregators) for ServerModuleWrapper:
            "{p}" remains untouched.
            "{grp}" becomes "{grp}[module_alias] " # module_alias is the primary
                                                   # alias used by the
                                                   # aggregator.
         STEP 3 (requester) for ServerBotInstance:
            "{p}" becomes the new prefix
            "{grp}" disappears.


      
      CURRENT SCHEME (for reference until I've completely replaced it)
         Help message string formatting arguments:
             Everywhere:
                "{cmd}" -> "{bc}{c}" -> "{p}{b}{c}"
                   "{cmd}", "{c}", and "{bc}"->"{p}{b}" are evaluated in get_help_summary().
                   "{b}" is evaluated where the help summary is composed from the command
                      objects themselves.
                   "{p}" is evaluated last, before sending off the final string.
             In modules:
                "{modhelp}" -> "{p}help {mod}"
                   "{modhelp}" and "{mod}" are evaluated where the help summary is composed
                      from the command objects themselves, in a module method.
                   "{p}" is evaluated last, before sending off the final string.

   """

   # Get help content specified by the locator string.
   # RETURNS: Either a string containing help content, or None if no help
   #          content exists.
   async def get_node(self, locator_string):
      assert isinstance(locator_str, str)
      path = locator_string.split()
      prev = None
      curr = self
      for location in path:
         curr = await curr.get_next_node(location, prev)
         if curr is None:
            break
         prev = location
      return curr

   # Get the node's detail help content as a string.
   # POSTCONDITION: Will always produce help content.
   #                This implies no NoneTypes or empty strings.
   @abc.abstractmethod
   async def get_help_detail(self, privilege_level=None):
      raise NotImplementedError

   # Get the node's summary help content as a string.
   # POSTCONDITION: Will always produce help content.
   #                This implies no NoneTypes or empty strings.
   # RETURNS: Tuple with two items:
   #              [0]: The help summary content. Guaranteed to 
   #              [1]: A "category" string that may help nodes aggregating
   #                   other help nodes to organize their help content.
   #                   Value is None if there is no catgory.
   @abc.abstractmethod
   async def get_help_summary(self, privilege_level=None):
      raise NotImplementedError

   # Get the next IHelpNode object, given a locator string specifying this next
   # object. If no such object exists, returns None.
   # PARAMETER: locator_string - A locator string to specify a "single
   #                             traversal" to the next node.
   # PARAMETER: entry_string - The "single traversal" locator string used
   #                           previously. If no locator string was used, pass
   #                           in None.
   # PRECONDITION: The locator_string only specifies a "single traversal" to
   #               the next node, i.e. no spaces, and non-empty.
   # PRECONDITION: The entry string shares the same precondition as
   #               locator_string, but entry_string may also be None.
   @abc.abstractmethod
   async def get_next_node(self, locator_string, entry_string):
      # A few asserts that may be used.
      assert type(locator_string) is str
      assert (not " " in locator_string) and (not locator_string is "")
      assert entry_string is None or type(entry_string) is str
      assert (not " " in entry_string) and (not entry_string is "")
      raise NotImplementedError

# STILL IN DEVELOPMENT
# class CommandHelpPage(HelpNode):
#    """
#    A general-use node collection of CommandMeta nodes.
#    """
#    def __init__(self):
#       self._cmd_list = []
#       self._cmd_dict = {}
#       self._help_summary = None
#       self._above_text = None # This is text that will be added before the
#                               # command listing. This must be pre-stripped
#                               # then a newline appended to the end.
#       return

#    # PARAMETER: cmd_obj - A command object to add to the collection.
#    #                      Also supports a list of command objects (appends each
#    #                      one individually).
#    def add_command(self, cmd_obj):
#       if not isinstance(cmd_obj, list):
#          cmd_obj = list(cmd_obj)
#       for x in cmd_obj:
#          assert callable(x) and hasattr(x.cmd_meta, CommandMeta)
#          for cmd_alias in x.cmd_meta.get_aliases():
#             assert isinstance(cmd_alias, str)
#             assert not cmd_alias in self._cmd_dict
#             self._cmd_dict[cmd_alias] = cmd_obj
#       self._cmd_list += cmd_obj
#       return

#    # PARAMETER: text - Either a string containing text to set as the help
#    #                   summary, or None.
#    def set_help_summary(self, text):
#       if text is None:
#          self._help_summary = None
#       else:
#          assert isinstance(text, str)
#          self._help_summary = text.strip()
#       return

#    # PARAMETER: text - Either a string containing text to append to the top
#    #                   in get_help_detail(), or None.
#    def set_above_text(self, text):
#       if text is None:
#          self._above_text = None
#       else:
#          assert isinstance(text, str)
#          self._above_text = text.strip() + "\n"
#       return

#    ################################
#    ### HelpNode Implementations ###
#    ################################

#    async def get_help_detail(self, privilege_level=None):
#       raise NotImplementedError

#    async def get_help_summary(self, privilege_level=None):
#       raise NotImplementedError

#    async def get_next_node(self, locator_string):
#       assert not " " in locator_string
#       assert not locator_string is ""
#       raise NotImplementedError


class CommandMeta(HelpNode):
   """
   Stores information about a command.

   MOTIVATION

   The original implementation of command functions involved "duct taping" new
   attributes to command functions, with no clear organization of this. Not
   only is data neatness an issue, but the code to handle these command
   function objects has to explicitly check for the existence of these
   attributes, so data access is also an issue.

   CommandMeta is designed to tidy all of this up.
   """

   DEFAULT_HELP_STR = "`{cmd}`"

   class TopLevelAliasAction(enum.Enum):
      NO_TOP_LEVEL_ALIASES = 0
      USE_EXISTING_ALIASES = 1
      USE_NEW_ALIASES = 2

   def __init__(self, cmd_fn):
      self._cmd_fn = cmd_fn

      # Attributes for aliases
      self._aliases = None
      self._top_level_alias_action = self.TopLevelAliasAction.NO_TOP_LEVEL_ALIASES
      self._top_level_aliases = None

      # Attributes for privilege levels
      self._minimum_privilege = PrivilegeLevel.get_lowest_privilege()

      # Attributes for leaf help content
      self._help_detail = None

      # Attributes for module help content
      self._help_category = None
      self._help_summary = None

      # Parsing the docstring to get _help_detail and _help_summary
      docstr = inspect.getdoc(cmd_fn)
      if docstr is None or len(docstr) == 0:
         # Give the default value.
         self._help_detail = self._help_summary = self.DEFAULT_HELP_STR
      else:
         docstr = docstr.strip()
         self._help_detail = docstr # TODO: Is it necessary?
         # Summaries include the first few lines of the string up until the first
         # empty line.
         lines = []
         for line in docstr.splitlines():
            if len(line) == 0:
               break
            lines.append(line)
         assert len(lines) > 0
         assert len(lines[0].strip()) > 0
         self._help_summary = "\n".join(lines)
      return

   def set_aliases(self, string_list):
      self._aliases = list(string_list)
      return

   def set_min_priv(self, privilege_level):
      self._minimum_privilege = privilege_level
      return

   def set_help_category(self, string):
      assert isinstance(string, str) and len(string) > 0
      self._help_category = string
      return

   # Make top-level aliases match the existing aliases.
   def set_top_aliases_existing(self):
      self._top_level_alias_action = self.TopLevelAliasAction.USE_EXISTING_ALIASES
      return

   # Sets top-level aliases explicitly.
   def set_top_aliases_explicitly(self, str_list):
      self._top_level_alias_action = self.TopLevelAliasAction.USE_NEW_ALIASES
      self._top_level_aliases = list(str_list)
      return

   def get_aliases(self):
      return list(self._aliases)

   def get_min_priv(self):
      return self._minimum_privilege

   def get_top_aliases(self):
      if self._top_level_alias_action is self.TopLevelAliasAction.USE_EXISTING_ALIASES:
         return list(self._aliases)
      elif self._top_level_alias_action is self.TopLevelAliasAction.USE_NEW_ALIASES:
         return list(self._top_level_aliases)
      else:
         return None

   ################################
   ### HelpNode Implementations ###
   ################################
   
   async def get_help_detail(self, privilege_level=None):
      buf = self._help_detail + "\n\n"
      buf0 = "**Required privilege level:** "
      buf0 += self._minimum_privilege.get_commonname()
      if (not privilege_level is None) and (privilege_level < self._minimum_privilege):
         buf += "**(Sorry, you do not have the correct privilege level.)**\n"
         buf += buf0 + "\n**Your privilege level:** "
         buf += privilege_level.get_commonname()
      else:
         buf += buf0
      return buf

   # PARAMETER: privilege_level - This argument doesn't actually do anything.
   async def get_help_summary(self, privilege_level=None):
      cat = self._help_category
      assert (isinstance(cat, str) and len(cat) > 0) or cat is None
      return (self._help_summary, cat)

   async def get_next_node(self, locator_string, entry_string):
      assert type(locator_string) is str
      assert (not " " in locator_string) and (not locator_string is "")
      assert entry_string is None or type(entry_string) is str
      assert (not " " in entry_string) and (not entry_string is "")
      return None # This is a leaf node.
