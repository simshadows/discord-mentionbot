# Discord-mentionbot
An extensible, multi-server Discord bot.

**This bot is still at a really early stage in development. I suggest you don't use it just yet...**

Key features:

* **Persistent data and settings**
* **Modularity**: Modules give the bot functionality.
	* Each module has the ability to pre-process incoming commands, allowing for some very interesting uses.
* **Server-wise Customizability**: Server owners are able to set up installed modules and change settings as desired.
* **Hierarchical Permissions System**: Assign roles different permission levels. Apart from the bot owner and server owner, there are 9 assignable permission levels, including a "No Privileges" level. *(Still under development)*
* **Server-isolation**: Each server is treated separately with their own installed modules, settings, and functionality.<sup>[1]</sup>

# Available Modules

* **Basic Information**: Presents some basic information about the server and the users in it, including user avatars and server icons.
* **Mentions**: Tools for keeping track of mentions.
	* Mentions can be PMed when users are offline (with the ability to opt-out).
	* A search tool allows you to scan through channels for mentions.
* **Random**: Randomization tools.
	* Generate random numbers of arbitrary ranges, flip coins, get random RGB colour codes, and use dice notation.
* **Wolfram Alpha**: Allows users to query Wolfram Alpha.

Some community-specific modules:

* **BSI StarkRavingMadBot**: A bot stand-in for the [JCFDiscord](https://www.reddit.com/r/JCFDiscord/) community's [StarkRavingMadBot](https://github.com/josh951623/StarkRavingMadBot).
	* This module is made to mirror some of StarkRavingMadBot's functionality, as well as take over if it's Stark isn't present on the server.

# Notes

* To run the *Wolfram Alpha* module, you must add your Wolfram Alpha app ID to `WolframAlpha._WA_APP_ID`.
* `classdiagram.xml` is opened with [draw.io](https://www.draw.io/).
* `design_notes.txt` is used by myself to reflect on my own design choices as this project is partly a learning exercise in object-oriented design.
* To add a new module:
	* Make the following edits on `servermodulefactory.py`:
		* add an import for the module's "main class", and
		* add the module's class to `ServerModuleFactory._MODULE_LIST`.
	* Optionally, add them as defaultly installed modules in `serverpersistentstorage.py`. This is done by hard-coding the *module name* into `ServerPersistentStorage.DEFAULT_SETTINGS`. IMPORTANT: the module name here is `ServerModule.MODULE_NAME`, not the module's class name.
* This does not poll to check who's the server owner. Must restart bot to change the bot's registered bot owner. *(This might change in the future, but it's a low priority.)*

# TODO:

* Fix the issue in `bsistarkravingmadbot` where the command prefix is hard-coded.
* Implement additional utility functions to make message pre-processing faster, and with neater code.
* Figure out a way to use dicts for faster message preprocessing. (It currently uses lots of if-else statements.)
* Implement message caching (retrieving messages fromm the server is time-consuming).
* Implement json data verification.
	* (LOW PRIORITY) Implement json data repair.
* Implement module enabling/disabling.
* Implement unified shared infrastructure for things like:
	* user activity sensing,
* Reimplement abstract classes with the `abc` library.
* Find all uses of utils.remove_blank_strings() and ensure none of them have a redundant list() around them.
* (LOW PRIORITY) Implement data cache backups. The bot should also back up files if they're found to be corrupted (to allow for manual recovery in the case of a bug during runtime).
* (LOW PRIORITY) Implement deeper module information infrastructure.
* (LOW PRIORITY) Implement scheduling for module enable/disable, or "alternative command" enable/disable. For example, a feature may turn off if another bot is offline or not responding. I'm not too sure if this is necessary though, especially given the added complexity such a feature would bring. Modules may even be specially built for this purpose anyway...
* (VERY LOW PRIORITY) The following module features:
	* In module `Random`, implement more advanced dicerolling.
* (ONGOING) Find and exterminate security flaws...

# Dependencies:

* `pip install git+https://github.com/Rapptz/discord.py@async`
* `pip install wolframalpha`
* ~~`pip install git+https://github.com/Julian/jsonschema`~~ (Planned to be used.)

---

<sup>[1]</sup> Modules are usually designed to only view and manipulate the server it's installed for. However, some modules are also designed to work inter-server (such as stat-tracking). This of course also shows that modules are not explicitly restricted from viewing and manipulating servers it's not installed for. This can be a problem if there are bugs, security flaws, and generally poorly designed modules (all of which are unintended). While all effort is made to fix any of these, security is not a key focus at the moment, so only essential security features and simple checks are implemented.
