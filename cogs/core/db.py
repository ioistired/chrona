import datetime
import os.path

import discord
from discord.ext import commands

from utils.sql import connection, optional_connection, load_sql

class DisappearingMessagesDatabase(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

		with open(os.path.join('sql', 'core.sql')) as f:
			self.queries = load_sql(f)

	@optional_connection
	async def get_expiry(self, channel: discord.TextChannel):
		return await connection().fetchval(self.queries.get_expiry, channel.id)

	@optional_connection
	async def set_expiry(self, channel: discord.TextChannel, expiry: datetime.timedelta):
		await connection().execute(self.queries.set_expiry, channel.guild.id, channel.id, expiry)

	@optional_connection
	async def get_message_expiration(self, message_id) -> datetime.datetime:
		return await connection().fetchval(self.queries.get_message_expiration, message_id)

def setup(bot):
	bot.add_cog(DisappearingMessagesDatabase(bot))
