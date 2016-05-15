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
* **Wolfram Alpha**: Allows users to query Wolfram Alpha.
* **Misc**: For commands that have no where else to live. *(Installed by default.)*

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

1. Go into `mentionbot/mentionbot.py` and change `BOTOWNER_ID` to your own ID.
2. Run `run.py` once. The bot should exit and a file named `bot_user_token` should appear.
3. Open `login_details` and replace `TOKEN` with your bot's login token. (Make sure the file only contains one line containing this information, with no extra newlines.)
4. Run `run.py` again. Your bot should be running now. This script is what you run from now on when you want to start the bot.

Every time the bot starts running, it will take a bit of time to locally cache messages. For bigger servers (or bots running on many servers), running this the first time will take a considerable amount of time, and until caching is complete, messages are not processed as commands.

Some modules will need some additional setting up in order to work.

* **Wolfram Alpha**: Add your Wolfram Alpha app ID to `cache\shared\m-WolframAlpha\settings.json`. This file appears the first time you use the module.
* **Server Activity Statistics**: Add your plotly username and API key to `cache\shared\m-ServerActivityStatistics\settings.json`. This file appears the first time you use the module.
* **Dynamic Channels**: This module's setup is currently broken (though once it's started, it works). I suggest not attempting to use this module until it's fixed.

# Other notes

* The bot will *always* reference flairs/roles by their names.

# For developers

* `classdiagram.xml` is opened with [draw.io](https://www.draw.io/).
* `design_notes.txt` is used by myself to reflect on my own design choices as this project is partly a learning exercise in object-oriented design.
* Creating new modules: Apologies for the lack of documentation for this. For now, you can try figuring out using current modules as examples. Notes:
	* Modules subclass ServerModule, and to register it for use in the bot, you must decorate the class with `registered`.
	* Services supplied to the module are from `resources` passed to the `_initialize()` method. `resources` is an instance of `ServerModuleResources` (which you can just read the source code for exposed methods). Please do not attempt to access any more than what this object allows.
	* Modules may make new non-returning coroutine tasks using `resources.start_nonreturning_coro()`. See `dynamicchannels.py` as an example. This allows for proper error-handling, should something go wrong within that task. Additionally, it allows the bot to cleanly stop the coroutine if required (e.g. when uninstalling the module).
		* **DO NOT** make non-returning coroutines in any other way (e.g. with `loop.create_task()`) as these cannot be cleaned up easily (unless you can figure out some other nicer way, in which case please leave a comment about it).
		* Similarly, **DO NOT** create new threads with indefinite lifespans unless you're prepared to clean it up cleanly.
		* For returning coroutines and temporary threads (e.g. a coroutine that waits 1 minute to send a message before a callback, or a thread that processes data for a definite amount of time before terminating), do these at your own risk. Just know that you will need to handle the errors or bad things will happen.
	* There isn't really much I can do about you doing weird things such as just up-front terminating the asyncio event loop, using sys.exit(0), accessing my computer and letting people know what's in my internet browser history somehow, or even weirder things. Just... try not to do these things, k? ;P

TODO:

* (VERY IMPORTANT) Clean up synchronization.
* (VERY IMPORTANT) Figure out why message caching sometimes freezes. This doesn't appear to cause an exception traceback printout, and while it's frozen, it just doesn't do anything.
* (VERY IMPORTANT) Figure out how to deal with the weird discord.py bug where sometimes, the server owner attribute is `None` and the server owner doesn't even appear in the list of users, meaning one less user than there actually are exists. The bot currently handles this error by restarting itself over and over until the bug is somehow resolved, but this can sometimes go on indefinitely.
* (IMPORTANT): Figure out how to fix the issue with `serveractivitystatistics.py` where, on larger servers, it fails to send back the results of a query and the whole bot crashes (and thus restarts). The result of the query, however, still sit in the root of the repository and may be retrieved.
* Implement "core modules" and put privilege management, module management, help messages, the misc commands module, and more things into "core modules". These core modules:
	* do not show when you use `/mods` (but have good help messages),
	* are **ALWAYS** installed by default,
	* cannot be uninstalled,
	* would require more exposed methods in `ServerModuleResources`, and
	* are probably easily distinguished in the source files (e.g. by putting them in a folder other than `servermodules`).
* Cleaner way to handle persistent storage of settings. Just look at the code to load/save settings in modules such as `dynamicchannels.py`. So damn messy!
* Consider using databases? Might be better than using lots and lots of JSON files.
* Consider using a `.ini` file for things like login token, bot owner ID, wolfram alpha app ID, etc.
* (IMPORTANT) Fix weird issue in `MessageCache` where message where, while moving messages to disk, some timestamps would already be strings. They should all be `datetime` objects. It's fixed, but I still don't understand the source of the problem.
* Fix the issue in `bsistarkravingmadbot` where the command prefix is hard-coded.
* (IMPORTANT) Implement additional utility functions to make message pre-processing faster, and with neater code.
* Figure out a way to use dicts for faster message preprocessing. (It currently uses lots of if-else statements.)
* Implement json data verification.
	* (LOW PRIORITY) Implement json data repair.
* Reimplement abstract classes with the `abc` library.
* Find all uses of utils.remove_blank_strings() and ensure none of them have a redundant list() around them.
* (LOW PRIORITY) Implement data cache backups. The bot should also back up files if they're found to be corrupted (to allow for manual recovery in the case of a bug during runtime).
* (LOW PRIORITY) Implement deeper module information infrastructure.
* (LOW PRIORITY) Implement scheduling for module enable/disable, or "alternative command" enable/disable. For example, a feature may turn off if another bot is offline or not responding. I'm not too sure if this is necessary though, especially given the added complexity such a feature would bring. Modules may even be specially built for this purpose anyway...
* (VERY LOW PRIORITY) The following module features:
	* In module `Random`, implement more advanced dicerolling.
* (ONGOING) Find and exterminate security flaws...

---

<sup>[1]</sup> Modules are usually designed to only view and manipulate the server it's installed for. However, some modules are also designed to work inter-server (such as stat-tracking). This of course also shows that modules are not explicitly restricted from viewing and manipulating servers it's not installed for. This can be a problem if there are bugs, security flaws, and generally poorly designed modules (all of which are unintended). While all effort is made to fix any of these, security is not a key focus at the moment, so only essential security features and simple checks are implemented.
