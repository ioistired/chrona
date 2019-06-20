import asyncio
import collections
import contextlib
import datetime
import os.path
import typing

import discord
from discord.ext import commands

from utils.converter import MessageId
from utils.sql import load_sql
from utils.time import human_timedelta, ShortTime

class DisappearingMessages(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.timers = bot.cogs['TimerDispatcher']
		self.db = bot.cogs['DisappearingMessagesDatabase']
		self.to_keep_lock = asyncio.Lock()
		self.to_keep = set()

	@commands.Cog.listener()
	async def on_message(self, message):
		if not message.guild:
			return

		async with self.to_keep_lock:
			if message.id in self.to_keep:
				self.to_keep.remove(message.id)
				return

		expiry = await self.db.get_expiry(message.channel)
		if expiry is None:
			return

		expires = datetime.datetime.utcnow() + expiry
		timer = await self.timers.create_timer(
			'message_expiration',
			expires,
			channel_id=message.channel.id,
			message_id=message.id)

	@commands.group(invoke_without_command=True)
	@commands.has_permissions(manage_messages=True)
	async def timer(self, ctx, channel: discord.TextChannel = None):
		"""Get the current disappearing message timer for this channel or another"""
		if ctx.invoked_subcommand is not None:
			return

		channel = channel or ctx.channel
		expiry = await self.db.get_expiry(channel)
		if expiry is None:
			await ctx.send(f'This channel does not have disappearing messages set up.')
		else:
			pronoun = 'this' if channel == ctx.channel else 'that'
			await ctx.send(
				f'The current disappearing message timer for {pronoun} channel is {human_timedelta(expiry)}.')

	@timer.command(name='set', usage='<time interval>')
	async def set_timer(self, ctx, channel: typing.Optional[discord.TextChannel] = None, *, expiry: ShortTime):
		# XXX i think this may not always preserve the invoking message
		# as self.on_message may have gotten to it first
		# however, in my experience, this does work
		async with self.to_keep_lock:
			self.to_keep.add(ctx.message.id)

		channel = channel or ctx.channel
		await self.db.set_expiry(channel, expiry)
		pronoun = 'this' if channel == ctx.channel else 'that'
		async with self.to_keep_lock:
			m = await ctx.send(
				f'{self.bot.config["success_emojis"][True]} New disappearing message timer for {pronoun} channel: '
				f'{human_timedelta(expiry)}.')
			self.to_keep.add(m.id)

	@commands.command(name='time-left')
	async def time_left(self, ctx, message: MessageId):
		channel, message_id = message
		expires_at = await self.db.get_message_expiration(message_id)
		if expires_at is None:
			await ctx.send('That message will not disappear.')
			return

		delta = expires_at - datetime.datetime.utcnow()
		await ctx.send(f'That message will expire in {human_timedelta(delta)}.')

	@commands.Cog.listener()
	async def on_message_expiration_timer_complete(self, timer):
		channel_id, message_id = map(timer.kwargs.get, ('channel_id', 'message_id'))
		with contextlib.suppress(discord.HTTPException):
			await self.bot.http.delete_message(channel_id, message_id)

def setup(bot):
	bot.add_cog(DisappearingMessages(bot))
