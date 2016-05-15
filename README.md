# Discord - mentionbot
An extensible, module-based chatroom bot for [Discord](https://discordapp.com/).

**This bot is still at a really early stage in development. It isn't particularly user-friendly, help messages are broken, and the code's rather messy at the moment. I suggest you wait until the bot's a little better-baked.**

# Key features:

* **Modularity**
* **Persistent data and settings**
	* A **message caching service** is provided to modules to speed up the operation of message searches and statistics generation.
* **Server-wise customizability**: Server owners are able to set up installed modules and change settings as desired. Settings are unique to each server (with rare exceptions).<sup>[1]</sup>
* **Internal permissions system**: Assign roles/flairs/tags and users different permission levels to use commands. Apart from the bot owner and server owner, there are 9 assignable permission levels, including a "No Privileges" level.
	* For example, a server could have a `Staff` role, which has a bot command privilege level of `Admin`.

# Available Modules

View all installed and available modules in discord using the command `/mods`.

* **Basic Information**: Presents some basic information about the server and the users in it, including user avatars and server icons. *(Installed by default.)*
* **Mentions Notify**: PMs users of their mentions when they're offline.
* **PM Greetings**: Greets users with a personalized private message upon joining the server. The contents of this private message can be customized.
* **Server Activity Statistics**: Generates server statistics and graphs.
* **Dynamic Channels**: Gives users the ability to create temporary channels that disappear after a few minutes of inactivity.
	* "Default channels" can be specified to be ignored by the module.
	* Warning: Server owners beware! While normal members won't see all the hidden channels, you and the bot will. The solution is to have an "admin acount" separate from your normal account.
* **Random**: Randomization tools. *(Installed by default.)*
	* Generate random numbers of arbitrary ranges, flip coins, get random RGB colour codes, and use dice notation.
* **Self-Serve Colours**: Allows users to pick their own RGB colour.
	* `/colour 00FF00` assigns the user a flair named `00ff00` with the appropriate colour.
* **Truth Game**: Facilities to play a game of "Truth".
* **Wolfram Alpha**: Allows users to query Wolfram Alpha. *(Installed by default.)*
* **Misc**: For commands that have no where else to live.

Some community-specific modules:

* **JCFDiscord**: For the [JCFDiscord](https://www.reddit.com/r/JCFDiscord/) community.
* **BSI StarkRavingMadBot**: A bot stand-in for the [JCFDiscord](https://www.reddit.com/r/JCFDiscord/) community's [StarkRavingMadBot](https://github.com/josh951623/StarkRavingMadBot).
	* This module is made to mirror some of StarkRavingMadBot's functionality, as well as take over if Stark isn't present on the server.

Currently under development/planned to be made:

* (none)

# Running the bot

The bot has the following dependencies:

* `pip install git+https://github.com/Rapptz/discord.py@async`
* `pip install git+https://github.com/dateutil/dateutil/`
* `pip install wolframalpha`
* `pip install plotly`
* ~~`pip install git+https://github.com/Julian/jsonschema`~~ (Planned to be used.)

To run the bot:

1. Go into `mentionbot.py` and change `BOTOWNER_ID` to your own ID.
2. Run `mentionbot.py` once (inside the `mentionbot` directory). The bot should exit and a file named `login_details` should appear.
3. Open `login_details` and replace `USERNAME` and `PASSWORD` with your bot's username and password. (Make sure the file only contains those two lines of text and no other lines.)
4. Run `mentionbot.py` again. Your bot should be running now.

The behaviour of the bot when joining a server *while the bot is running* is currently undefined. Please make sure your bot account is already in the servers it must manage before launching, and restart the bot on server joins. Depending on the modules, getting kicked from a server may also cause issues.

Every time the bot starts running, it will take a bit of time to locally cache messages. For bigger servers (or bots running on many servers), running this the first time will take a considerable amount of time, and until caching is complete, messages are not processed as commands.

This bot is configured to kill itself when it encounters an unhandled exception.

Some modules will need some additional setting up in order to work.

* **Wolfram Alpha**: Add your Wolfram Alpha app ID to `cache\shared\m-WolframAlpha\settings.json`. This file appears the first time you use the module.
* **Server Activity Statistics**: Add your plotly username and API key to `cache\shared\m-ServerActivityStatistics\settings.json`. This file appears the first time you use the module.
* **Dynamic Channels**: This module's setup is currently broken (though once it's started, it works). I suggest not attempting to use this module until it's fixed.

# Other notes

* The bot will *always* reference flairs/roles by their names.

# For developers

* `classdiagram.xml` is opened with [draw.io](https://www.draw.io/).
* `design_notes.txt` is used by myself to reflect on my own design choices as this project is partly a learning exercise in object-oriented design.
* To add a new module:
	* Make the following edits on `servermodulefactory.py`:
		* add an import for the module's "main class", and
		* add the module's class to `ServerModuleFactory._MODULE_LIST`.
	* Optionally, add them as defaultly installed modules in `serverpersistentstorage.py`. This is done by hard-coding the *module name* into `ServerPersistentStorage.DEFAULT_SETTINGS`. IMPORTANT: the module name here is `ServerModule.MODULE_NAME`, not the module's class name.

TODO:

* (IMPORTANT) Fix start-up and shut-down issues with Dynamic Channels. It works perfectly once it's set up, but the initial setting up is such a pain.
* (IMPORTANT) Fix weird issue in `MessageCache` where message where, while moving messages to disk, some timestamps would already be strings. They should all be `datetime` objects.
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

---

<sup>[1]</sup> Modules are usually designed to only view and manipulate the server it's installed for. However, some modules are also designed to work inter-server (such as stat-tracking). This of course also shows that modules are not explicitly restricted from viewing and manipulating servers it's not installed for. This can be a problem if there are bugs, security flaws, and generally poorly designed modules (all of which are unintended). While all effort is made to fix any of these, security is not a key focus at the moment, so only essential security features and simple checks are implemented.
