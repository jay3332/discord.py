discord.py
==========

.. image:: https://discord.com/api/guilds/336642139381301249/embed.png
   :target: https://discord.gg/r3sSKJJ
   :alt: Discord server invite
.. image:: https://img.shields.io/pypi/v/discord.py.svg
   :target: https://pypi.python.org/pypi/discord.py
   :alt: PyPI version info
.. image:: https://img.shields.io/pypi/pyversions/discord.py.svg
   :target: https://pypi.python.org/pypi/discord.py
   :alt: PyPI supported Python versions

A modern, easy to use, feature-rich, and async ready API wrapper for Discord written in Python.

This fork has halted maintenance.
---------------------------------

Development of discord.py has now been "revived", see further details `here <https://gist.github.com/Rapptz/c4324f17a80c94776832430007ad40e6>`.
As such, there really isn't much motivation for this fork anymore.

Practically everything that was implemented for this fork was also implemented for Danny's. Additionally, ext-commands compatibility (previously done using `discord-ext-compat <https://github.com/jay3332/discord-ext-compat>`) is planned.
Danny implemented application commands in a way that they are declared using functions. This fork implements it in a way that uses classes: they were much cleaner, readable, and reduced unnecessary repetition with names. Additionally, they just seemed more declarative than it's function-based counterpart.
Although I'm not the biggest fan of a function-based implementation, see `here <https://github.com/jay3332/discord.py/#why-not-class-based>` as to why Danny went with it.

Welcome to my fork of discord.py
--------------------------------

Note: The following was written **before** Danny announced the "resurrection" of discord.py

It was originally made to implement Danny's
`slash command DSL <https://gist.github.com/Rapptz/2a7a299aa075427357e9b8a970747c2c>`_ (The class based version),
and it does it pretty well.

There have been many changes since this DSL was created however, for example slash commands turning
into a category of "application commands". These "application commands" also contain "context menus",
specifically referred to as "message commands" and "user commands". This fork does, in fact, support them.

As a result of this, naming schemes that go along "slash command" have been renamed to their counterparts
that go along with "application_command". This unfortunately does make things a bit verbose, however
shortening the names would leave name conflicts and confusion.

What's been added?
~~~~~~~~~~~~~~~~~~
- Application commands

  - Slash commands
  - Context menus (Message commands & user commands)
  - ``channel_types`` option field
  - Autocomplete options
  - Attachment option type

- UI

  - Modals @ ``discord.ui.Modal``
  - ``ItemContainer`` ABC

- Role icons
- Welcome screens
- Guild scheduled events
- Member chat timeout (``communication_disabled_until``)

Key Features
-------------

- Modern Pythonic API using ``async`` and ``await``.
- Proper rate limit handling.
- Optimised in both speed and memory.

Installing
----------

**Python 3.8 or higher is required**

To install the library without full voice support, you can just run the following command:

.. code:: sh

    # Linux/macOS
    python3 -m pip install -U discord.py

    # Windows
    py -3 -m pip install -U discord.py

Otherwise to get voice support you should run the following command:

.. code:: sh

    # Linux/macOS
    python3 -m pip install -U "discord.py[voice]"

    # Windows
    py -3 -m pip install -U discord.py[voice]


To install the development version, do the following:

.. code:: sh

    $ git clone https://github.com/jay3332/discord.py
    $ cd discord.py
    $ python3 -m pip install -U .[voice]


Optional Packages
~~~~~~~~~~~~~~~~~~

* `PyNaCl <https://pypi.org/project/PyNaCl/>`__ (for voice support)

Please note that on Linux installing voice you must install the following packages via your favourite package manager (e.g. ``apt``, ``dnf``, etc) before running the above commands:

* libffi-dev (or ``libffi-devel`` on some systems)
* python-dev (e.g. ``python3.6-dev`` for Python 3.6)

Quick Example
--------------

.. code:: py

    import discord

    class MyClient(discord.Client):
        async def on_ready(self):
            print('Logged on as', self.user)

        async def on_message(self, message):
            # don't respond to ourselves
            if message.author == self.user:
                return

            if message.content == 'ping':
                await message.channel.send('pong')

    client = MyClient()
    client.run('token')

Application Command Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: py

    import discord
    from discord.application_commands import ApplicationCommand, ApplicationCommandTree, option

    tree = ApplicationCommandTree(guild_id=123456)

    class HelloWorld(ApplicationCommand, name='hello-world', tree=tree):
        """Hello"""
        async def callback(self, interaction):
            await interaction.response.send_message('Hello, world!')

    client = discord.Client(update_application_commands_at_startup=True)
    client.add_application_command_tree(tree)
    client.run('token')

Bot Example
~~~~~~~~~~~~~

.. code:: py

    import discord
    from discord.ext import commands

    bot = commands.Bot(command_prefix='>')

    @bot.command()
    async def ping(ctx):
        await ctx.send('pong')

    bot.run('token')

You can find more examples in the examples directory.

Links
------

- `Documentation <https://discordpy.readthedocs.io/en/latest/index.html>`_
- `Official Discord Server <https://discord.gg/r3sSKJJ>`_
- `Discord API <https://discord.gg/discord-api>`_

Why not class-based?
--------------------
This fork **does** implement a class-based application commands implementation. However, Danny chose to not implement it this way on discord.py itself:

   "I think this is too hung up on syntactic features (i.e. this is mostly focused on "syntax looks" rather than functionality). There's actually a reason that classes aren't abused like this in most Python libraries and that's because their composability is too restricted. For example, classes can't compose very well if they override one functionality without an explicit call to super and making many mixins which infects the MRO chain. Every caller in the MRO chain then depends on calling super or else the chain ends, sometimes unexpectedly prematurely.

   I've messed with class based commands, but it doesn't actually work very well. To give a concrete example, consider checks. Checks are nice and reusable, but if every command was a class where would you shove the check in? In traditional systems you'd have a check method you override with your logic but in this system you now have to maintain every function call. Alternatively you can stack decorators that do this.

   I've also messed with returning a class sentinel value (e.g. TextResponse in your example) in many of my old bots before d.py existed. That system doesn't work either because of the concept of follow ups. Sometimes you want to send more than one message at a specific point and sometimes that message depends on user input from an asynchronous system. Things get complicated if you had to return a value to signal whether to return a response or not. It's just not good dev UX."
