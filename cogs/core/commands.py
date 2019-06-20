import contextlib
import datetime
import os.path

import discord
from discord.ext import commands

from utils.sql import load_sql
from utils.time import human_timedelta, ShortTime

class DisappearingMessages(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.timer_db = bot.cogs['TimerDatabase']
		self.db = bot.cogs['DisappearingMessagesDatabase']

	@commands.Cog.listener()
	async def on_message(self, message):
		if not message.guild:
			return
		expiry = await self.db.get_expiry(message.channel)
		if expiry is None:
			return

		expires = datetime.datetime.utcnow() + expiry
		timer = await self.timer_db.create_timer(
			'message_expiration',
			expires,
			channel_id=message.channel.id,
			message_id=message.id)

	@commands.group(name='expiry', invoke_without_command=True)
	@commands.has_permissions(manage_messages=True)
	async def expiry(self, ctx):
		if ctx.invoked_subcommand is not None:
			return

		expiry = await self.db.get_expiry(message.channel)
		if expiry is None:
			await ctx.send(f'This message has disappearing messages set up.')
		else:
			await ctx.send(f'The current expiry for this channel is {human_timedelta(expiry)}.')

	@expiry.command(name='set')
	async def set_expiry(self, ctx, expiry: ShortTime):
		await self.db.set_expiry(ctx.channel, expiry)
		await ctx.send(
			f'{self.bot.config["success_emojis"][True]} New expiry for this channel: {human_timedelta(expiry)}.')

	@commands.Cog.listener()
	async def on_message_expiration_timer_complete(self, timer):
		channel_id, message_id = map(timer.kwargs.get, ('channel_id', 'message_id'))
		with contextlib.suppress(discord.HTTPException):
			await self.bot.http.delete_message(channel_id, message_id)

def setup(bot):
	bot.add_cog(DisappearingMessages(bot))
