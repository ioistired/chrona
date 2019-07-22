import asyncio
import collections
import contextlib
import datetime
import os.path
import time
import typing

import discord
from discord.ext import commands

from utils.converter import MessageId
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
		await asyncio.sleep(10)
		print('handling missed')

		cutoff = discord.utils.time_snowflake(self.started_at, high=True)
		async for channel_id, message_id, expiry in self.db.latest_message_per_channel(cutoff):
			channel = self.bot.get_channel(channel_id)
			if not channel:
				continue

			to_purge = []
			async for m in channel.history(after=discord.Object(message_id), limit=None):
				print(m.content)
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
			await ctx.send(f'This channel does not have disappearing messages set up.')
		else:
			noun = 'this channel' if channel == ctx.channel else channel.mention
			await ctx.send(
				f'The current disappearing message timer for {noun} channel is {human_timedelta(expiry)}.')

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
			async with self.to_keep_locks[channel.id]:
				m = await channel.send(
					f'{ctx.author.mention} set the disappearing message timer to {human_timedelta(expiry)}.')
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
			m = await channel.send(f'{ctx.author.mention} disabled disappearing messages.')
			self.to_keep[channel.id].add(m.id)

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
