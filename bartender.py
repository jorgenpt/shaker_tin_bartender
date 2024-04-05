import discord

class Bartender(discord.Client):
    notification_channels: list[discord.TextChannel] = []

    async def on_ready(self):
        print(f'Logged on as {self.user}!')
    
    async def on_guild_available(self, guild: discord.Guild):
        print(f'Guild available {guild}')
        for channel in guild.channels:
            if channel.name == 'shaker-tin':
                print(f"Found channel: {channel}")
                self.notification_channels.append(channel)


intents = discord.Intents.default()
client = Bartender(intents=intents)
client.run(open('bot_secret.txt', 'r').read().strip())