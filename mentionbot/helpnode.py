import abc

from .enums import PrivilegeLevel

class HelpNode(abc.ABC):
   """
   (INTERFACE) This defines an object that can be referenced as a node in a directed graph
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
            All remains untouched.
         STEP 3 (requester) for ServerBotInstance:
            "{p}" becomes the new prefix
            "{grp}" is evaluated to the path taken to reach the node.
      
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
   # PARAMETER: locator_string - A string used to locate the help content.
   #                             By convention, 
   # RETURNS: Either a string containing help content, or None if no help
   #          content exists.
   # Get the node's detail help content as a string.
   # POSTCONDITION: Will always produce help content.
   #                This implies no NoneTypes or empty strings.
   @abc.abstractmethod
   async def get_help_detail(self, locator_string, entry_string, privilege_level):
      assert isinstance(locator_string, str) and isinstance(entry_string, str)
      assert isinstance(privilege_level, PrivilegeLevel)
      raise NotImplementedError

   # Get the node's summary help content as a string.
   # POSTCONDITION: Will always produce help content.
   #                This implies no NoneTypes or empty strings.
   # RETURNS: Tuple with two items:
   #              [0]: The help summary content.
   #              [1]: A "category" string that may help nodes aggregating
   #                   other help nodes to organize their help content.
   #                   Value is None if there is no catgory.
   @abc.abstractmethod
   async def get_help_summary(self, privilege_level):
      assert isinstance(privilege_level, PrivilegeLevel)
      raise NotImplementedError

   # Get the minimum privilege level normally required to access the node.
   # POSTCONDITION: Guaranteed to produce a PrivilegeLevel object.
   #                For nodes with no privilege restriction, the lowest
   #                privilege level will be returned.
   @abc.abstractmethod
   async def node_min_priv(self):
      raise NotImplementedError

   # Get a string that names the category in which the node identifies itself
   # to belong to. If no category, then this will return an empty string.
   @abc.abstractmethod
   async def node_category(self):
      raise NotImplementedError
