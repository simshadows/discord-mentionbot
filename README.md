# Discord-mentionbot
An extensible, multi-server Discord bot.

**This bot is still in at a really early stage in development. I suggest you don't use it just yet...**

One of the key features is its suite of mention-searching modules. You can:
* configure it to PM mentions when offline, and/or
* get the bot to search the entire chat history for your mentions so you don't have to.

Currently, no other modules are available as the main program structure is being built and perfected. Check back later though!

**Notes:**

* `classdiagram.xml` is opened with [draw.io](https://www.draw.io/).
* This does not poll to check who's the server owner. Must restart bot for changes to apply.

**TODO:**

* Implement module enabling/disabling.
* Reimplement abstract classes with the `abc` library.
* Work a design that allows unified persistent data storage, shared message history caching, and shared user activity sensing.
* Find and exterminate the many security flaws...



