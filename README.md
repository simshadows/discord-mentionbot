# Discord - mentionbot
An extensible, module-based chatroom bot for [Discord](https://discordapp.com/).

**This bot is still at a really early stage in development. I suggest you don't use it just yet...**

# Key features:

* **Persistent data and settings**
	* A message caching service is also provided to speed up the operation of message searches and statistics generation.
* **Modularity**: Modules give the bot functionality.
	* Each module has the ability to pre-process incoming commands, allowing for some very interesting uses.
* **Server-wise customizability**: Server owners are able to set up installed modules and change settings as desired.
* **Hierarchical permissions system**: Assign roles different permission levels. Apart from the bot owner and server owner, there are 9 assignable permission levels, including a "No Privileges" level. *(Still under development)*
* **Server-isolation**: Each server is treated separately with their own installed modules and settings.<sup>[1]</sup>

# Available Modules

View installed modules

* **Basic Information**: Presents some basic information about the server and the users in it, including user avatars and server icons. *(Installed by default.)*
* **Mentions Notify**: PMs users of their mentions when they're offline.
* **Random**: Randomization tools. *(Installed by default.)*
	* Generate random numbers of arbitrary ranges, flip coins, get random RGB colour codes, and use dice notation.
* **Wolfram Alpha**: Allows users to query Wolfram Alpha. *(Installed by default.)*

Some community-specific modules:

* **JCFDiscord**: For the [JCFDiscord](https://www.reddit.com/r/JCFDiscord/) community.
* **BSI StarkRavingMadBot**: A bot stand-in for the [JCFDiscord](https://www.reddit.com/r/JCFDiscord/) community's [StarkRavingMadBot](https://github.com/josh951623/StarkRavingMadBot).
	* This module is made to mirror some of StarkRavingMadBot's functionality, as well as take over if Stark isn't present on the server.

Currently under development/planned to be made:

* **Dynamic Channels**: Gives users the ability to create temporary channels that disappear after a few minutes of inactivity.
	* "Default channels" can be specified to be ignored by the module.
	* Warning: Server owners beware! While normal members won't see all the hidden channels, you and the bot will. The solution is to have an "admin acount" separate from your normal account.

# Running the bot

1. Run `mentionbot.py` once (inside the `mentionbot` directory). A file named `login_details` should appear.
2. Open `login_details` and replace `USERNAME` and `PASSWORD` with your bot's username and password. (Make sure the file only contains those two lines of text and no other lines.)
3. Run `mentionbot.py` again. Your bot should be running now.

Every time the bot starts running, it will take a bit of time to locally cache messages. For bigger servers (or bots running on many servers), running this the first time will take a considerable amount of time, and until caching is complete, messages are not processed as commands.

# Notes

* To run the *Wolfram Alpha* module, you must add your Wolfram Alpha app ID to `cache/shared/m-WolframAlpha/settings.json`. This file appears the first time you use the module.
* `classdiagram.xml` is opened with [draw.io](https://www.draw.io/).
* `design_notes.txt` is used by myself to reflect on my own design choices as this project is partly a learning exercise in object-oriented design.
* To add a new module:
	* Make the following edits on `servermodulefactory.py`:
		* add an import for the module's "main class", and
		* add the module's class to `ServerModuleFactory._MODULE_LIST`.
	* Optionally, add them as defaultly installed modules in `serverpersistentstorage.py`. This is done by hard-coding the *module name* into `ServerPersistentStorage.DEFAULT_SETTINGS`. IMPORTANT: the module name here is `ServerModule.MODULE_NAME`, not the module's class name.
* This does not poll to check who's the server owner. Must restart bot to change the bot's registered bot owner. *(This might change in the future, but it's a low priority.)*

# TODO:

* Implement module safe-shutdown. Modules such as `Dynamic Channels` will need a method to end threads.
* Fix the issue in `bsistarkravingmadbot` where the command prefix is hard-coded.
* (IMPORTANT) Implement additional utility functions to make message pre-processing faster, and with neater code.
* Figure out a way to use dicts for faster message preprocessing. (It currently uses lots of if-else statements.)
* Implement message caching (retrieving messages from the server is time-consuming).
* Implement json data verification.
	* (LOW PRIORITY) Implement json data repair.
* Implement module enabling/disabling.
* Reimplement abstract classes with the `abc` library.
* Find all uses of utils.remove_blank_strings() and ensure none of them have a redundant list() around them.
* (LOW PRIORITY) Implement better locking for `MentionBot.on_message()`.
* (LOW PRIORITY) Implement data cache backups. The bot should also back up files if they're found to be corrupted (to allow for manual recovery in the case of a bug during runtime).
* (LOW PRIORITY) Implement deeper module information infrastructure.
* (LOW PRIORITY) Implement scheduling for module enable/disable, or "alternative command" enable/disable. For example, a feature may turn off if another bot is offline or not responding. I'm not too sure if this is necessary though, especially given the added complexity such a feature would bring. Modules may even be specially built for this purpose anyway...
* (VERY LOW PRIORITY) The following module features:
	* In module `Random`, implement more advanced dicerolling.
* (ONGOING) Find and exterminate security flaws...

# Dependencies:

* `pip install git+https://github.com/Rapptz/discord.py@async`
* `pip install git+https://github.com/dateutil/dateutil/`
* `pip install wolframalpha`
* ~~`pip install git+https://github.com/Julian/jsonschema`~~ (Planned to be used.)

---

<sup>[1]</sup> Modules are usually designed to only view and manipulate the server it's installed for. However, some modules are also designed to work inter-server (such as stat-tracking). This of course also shows that modules are not explicitly restricted from viewing and manipulating servers it's not installed for. This can be a problem if there are bugs, security flaws, and generally poorly designed modules (all of which are unintended). While all effort is made to fix any of these, security is not a key focus at the moment, so only essential security features and simple checks are implemented.
