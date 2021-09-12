import discord
from discord.application_commands import ApplicationCommand, option


class Ping(ApplicationCommand, name='ping'):
    """Pong?"""

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message('Pong!')


class Math(ApplicationCommand, name='math'):
    """Basic math operations."""

    class Add(ApplicationCommand, name='add'):
        """Sum of x + y."""
        x: int = option(description='Value of "x"', required=True)
        y: int = option(description='Value of "y"', required=True)

        async def callback(self, interaction: discord.Interaction):
            answer = self.x + self.y
            await interaction.response.send_message(
                f'The value of {self.x} + {self.y} is **{answer}**.',
                ephemeral=True
            )

    class Subtract(ApplicationCommand, name='subtract'):
        """Difference of x - y."""
        x: int = option(description='Value of "x"', required=True)
        y: int = option(description='Value of "y"', required=True)

        async def callback(self, interaction: discord.Interaction):
            answer = self.x - self.y
            await interaction.response.send_message(
                f'The value of {self.x} - {self.y} is **{answer}**.',
                ephemeral=True
            )


class Client(discord.Client):
    def __init__(self):
        super().__init__()
        self.add_application_commands(Ping, Math)

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')


client = Client()
client.run('token')
