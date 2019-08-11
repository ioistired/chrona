import asyncio
import collections
import contextlib
import datetime
import math
import os.path
import time
import typing

import discord
from discord.ext import commands

from utils.converter import Message
from utils.sql import connection, load_sql
from utils.time import human_timedelta, ShortTime

class DisappearingMessages(commands.Cog):
	def __init__(self, bot):
		self.started_at = datetime.datetime.utcnow()
		self.bot = bot
		self.timers = bot.cogs['TimerDispatcher']
		self.db = bot.cogs['DisappearingMessagesDatabase']
		# TODO make these one LRU
		self.to_keep_locks = collections.defaultdict(asyncio.Lock)
		self.to_keep = collections.defaultdict(set)

		self.handle_missed_task = self.bot.loop.create_task(self.handle_missed())

	async def handle_missed(self):
		await self.bot.wait_until_ready()

		cutoff = discord.utils.time_snowflake(self.started_at, high=True)
		async for channel_id, message_id, expiry in self.db.latest_message_per_channel(cutoff):
			channel = self.bot.get_channel(channel_id)
			if not channel:
				continue

			to_purge = []
			async for m in channel.history(after=discord.Object(message_id), limit=None):
				if m.created_at < datetime.datetime.utcnow() - expiry:
					to_purge.append(m)
				else:
					await self.create_timer(m, expiry)

			await channel.delete_messages(to_purge)

	def cog_unload(self):
		self.handle_missed_task.cancel()

	@commands.Cog.listener()
	async def on_message(self, message):
		if not message.guild:
			return

		async with self.to_keep_locks[message.channel.id]:
			with contextlib.suppress(LookupError):
				self.to_keep[message.channel.id].remove(message.id)
				return

		expiry = await self.db.get_expiry(message.channel)
		if expiry is None:
			return

		await self.create_timer(message, expiry)

	async def create_timer(self, message, expiry):
		expires = message.created_at + expiry
		await self.timers.create_timer(
			'message_expiration',
			expires,
			channel_id=message.channel.id,
			message_id=message.id,
			created=message.created_at)

	@commands.group(invoke_without_command=True)
	async def timer(self, ctx, channel: discord.TextChannel = None):
		"""Get the current disappearing message timer for this channel or another"""
		if ctx.invoked_subcommand is not None:
			return

		channel = channel or ctx.channel
		expiry = await self.db.get_expiry(channel)
		if expiry is None:
			emoji = self.bot.config['timer_disable_emoji']
			await ctx.send(f'{emoji} This channel does not have disappearing messages set up.')
		else:
			noun = 'this channel' if channel == ctx.channel else channel.mention
			await ctx.send(
				f'The current disappearing message timer for {noun} channel is **{human_timedelta(expiry)}**.')

	@timer.command(name='set', usage='<time interval>')
	async def set_timer(self, ctx, channel: typing.Optional[discord.TextChannel] = None, *, expiry: ShortTime):
		channel = channel or ctx.channel
		if not channel.permissions_for(ctx.author).manage_channels:
			raise commands.MissingPermissions(['manage_channels'])

		async with self.bot.pool.acquire() as conn, conn.transaction():
			connection.set(conn)
			await self.db.set_expiry(channel, expiry)
			# for consistency with already having a timer, also delete the invoking message
			# even when no timer is set
			self.bot.loop.create_task(self.create_timer(ctx.message, expiry))

			emoji = self.bot.config['timer_change_emoji']
			async with self.to_keep_locks[channel.id]:
				m = await channel.send(
					f'{emoji} {ctx.author.mention} set the disappearing message timer to **{human_timedelta(expiry)}**.')
				self.to_keep[channel.id].add(m.id)
			await self.db.set_last_timer_change(channel, m.id)

	@timer.command(name='delete', aliases=['rm', 'del', 'delet', 'remove', 'disable'])
	async def delete_timer(self, ctx, channel: discord.TextChannel = None):
		channel = channel or ctx.channel
		if not channel.permissions_for(ctx.author).manage_channels:
			raise commands.MissingPermissions(['manage_channels'])

		async with self.bot.pool.acquire() as conn, conn.transaction():
			connection.set(conn)
			await self.db.delete_expiry(channel)
			await self.db.delete_last_timer_change(channel.id)

		async with self.to_keep_locks[channel.id]:
			emoji = self.bot.config['timer_disable_emoji']
			m = await channel.send(f'{emoji} {ctx.author.mention} disabled disappearing messages.')
			self.to_keep[channel.id].add(m.id)

	@commands.command(name='time-left', aliases=['when'])
	async def time_left(self, ctx, message: Message):
		# this technically may not work--it's still a race condition
		async with self.to_keep_locks[ctx.channel.id]:
			self.to_keep[ctx.channel.id].add(ctx.message.id)

		expires_at = await self.db.get_message_expiration(message.id)
		if expires_at is None:
			await ctx.send('That message will not disappear.')
			return

		now = datetime.datetime.utcnow()
		time_left = expires_at - now
		time_elapsed = now - message.created_at
		expiry = expires_at - message.created_at

		emoji = self.timer_emoji(time_elapsed, expiry)

		async with self.to_keep_locks[ctx.channel.id]:
			# time left messages disappear when the message does
			await self.create_timer(ctx.message, time_left)
			m = await ctx.send(f'{emoji} That message will disappear in **{human_timedelta(time_left)}**.')
			self.to_keep[ctx.channel.id].add(m.id)
			await self.create_timer(m, time_left)

	@commands.Cog.listener()
	async def on_message_expiration_timer_complete(self, timer):
		channel_id, message_id = map(timer.kwargs.get, ('channel_id', 'message_id'))
		with contextlib.suppress(discord.HTTPException):
			await self.bot.http.delete_message(channel_id, message_id)

	def timer_emoji(self, time_elapsed, expiry):
		elapsed_coeff = max(0, min(1, time_elapsed.total_seconds() / expiry.total_seconds()))
		emojis = self.bot.config['timer_emojis']
		# err on the side of more time left, allowing a new message to show the first emoji
		i = max(0, min(len(emojis) - 1, math.floor(elapsed_coeff * len(emojis))))
		return emojis[i]

def setup(bot):
	bot.add_cog(DisappearingMessages(bot))
