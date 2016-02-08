# Discord-mentionbot
An extensible, multi-server Discord bot.

**This bot is still at a really early stage in development. I suggest you don't use it just yet...**

Key features:

* **Persistent data and settings** *(Still under development)*
* **Modularity**: Modules give the bot functionality.
* **Customizability**: Server owners are able to set up installed modules and change settings as desired. *(Still under development)*
* **Hierarchical Permissions System**: Assign roles different permission levels. Apart from the bot owner and server owner, there are 9 assignable permission levels, including a "No Privileges" level.
* **Server-isolation**: Each server is treated separately with their own installed modules, settings, and functionality.^[Modules are usually designed to only view and manipulate the server it's installed for. However, some modules are also designed to work inter-server (such as stat-tracking). This of course also shows that modules are not explicitly restricted from viewing and manipulating servers it's not installed for. This can be a problem if there are bugs, security flaws, and generally poorly designed modules (all of which are unintended). While all effort is made to fix any of these, security is not a key focus at the moment, so only essential security features and simple checks are implemented.]

Currently, no other modules are available while the main program structure is being built. Check back later though!

**Notes:**

* `classdiagram.xml` is opened with [draw.io](https://www.draw.io/).
* This does not poll to check who's the server owner. Must restart bot for changes to apply.

**TODO:**

* Implement module enabling/disabling.
* Reimplement abstract classes with the `abc` library.
* Work a design that allows unified persistent data storage, shared message history caching, and shared user activity sensing.
* Find and exterminate the many security flaws...

**Dependencies:**

* `pip install git+https://github.com/Rapptz/discord.py@async`
