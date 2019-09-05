import asyncio
import datetime
import logging
import os.path

import asyncpg
import discord
from bot_bin.misc import natural_timedelta
from discord.ext import commands

from utils import sleep
from utils.sql import connection, optional_connection

logger = logging.getLogger(__name__)

# Using code provided by Rapptz under the MIT License
# © 2015 Rapptz
# https://raw.githubusercontent.com/Rapptz/RoboDanny/rewrite/cogs/reminder.py

class Timer:
	__slots__ = frozenset('expires guild_id channel_id message_id'.split())

	def __init__(self, *, guild_id, channel_id, message_id, expires):
		self.guild_id = guild_id
		self.channel_id = channel_id
		self.message_id = message_id
		self.expires = expires

	async def sleep_until_complete(self):
		await sleep((self.expires - datetime.datetime.utcnow()).total_seconds())

	@property
	def created_at(self):
		return discord.utils.snowflake_time(self.message_id)

	@property
	def human_delta(self):
		return natural_timedelta(self.created_at)

	def __repr__(self):
		return '<{} {}>'.format(
			type(self).__qualname__,
			' '.join(f'{k}={getattr(self, k)}' for k in 'guild_id channel_id message_id expires'.split()))

	@property
	def id(self):
		return self.channel_id, self.message_id

	def __eq__(self, other):
		return self.id == other.id

	def __hash__(self):
		return hash(self.id)

class DisappearingMessagesDatabase(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.queries = self.bot.jinja_env.get_template('queries.sql')
		self.current_timer = None
		self.have_timer = asyncio.Event()
		self.task = self.bot.loop.create_task(self._dispatch_timers())

	### dispatching

	def cog_unload(self):
		self.task.cancel()

	async def _dispatch_timers(self):
		try:
			while not self.bot.is_closed():
				# for some reason this is necessary, even with @optional_connection
				async with self.bot.pool.acquire() as conn:
					connection.set(conn)
					timer = self.current_timer = await self._wait_for_active_timer()

				await timer.sleep_until_complete()
				await self._handle_timer(timer)
		except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError, asyncpg.InterfaceError) as exc:
			logger.warning('Timer dispatching restarting due to %r', exc)
			self.task.cancel()
			self.task = self.bot.loop.create_task(self._dispatch_timers())

	async def _wait_for_active_timer(self):
		timer = await self.get_active_timer()
		if timer is not None:
			self.have_timer.set()
			return timer

		# no timers found in the DB
		self.have_timer.clear()
		self.current_timer = None
		await self.have_timer.wait()
		return await self.get_active_timer()

	async def _handle_timer(self, timer):
		await self.delete_timer(timer)
		self.bot.dispatch('message_expiration', timer)

	async def create_timer(self, message, expiry):
		return await self._create_timer(self.queries.create_timer(), message, expiry)

	async def create_or_update_timer(self, message, expiry):
		"""create a timer. if one already exists for this message, and the new expiration is sooner than the old
		expiration, update the existing timer.
		"""
		return await self._create_timer(self.queries.create_timer('upsert'), message, expiry)

	@optional_connection
	async def _create_timer(self, query, message, expiry):
		expires = message.created_at + expiry
		timer = Timer(guild_id=message.guild.id, channel_id=message.channel.id, message_id=message.id, expires=expires)

		await connection().execute(query, message.guild.id, message.channel.id, message.id, expires)
		self.have_timer.set()

		if self.current_timer and timer.expires < self.current_timer.expires:
			self.current_timer = timer
			self.task.cancel()
			self.bot.loop.create_task(self._dispatch_timers())

		return timer

	### Database calls

	@optional_connection
	async def delete_timer(self, timer):
		await connection().execute(self.queries.delete_timer(), timer.channel_id, timer.message_id)

	@optional_connection
	async def get_active_timer(self):
		record = await connection().fetchrow(self.queries.get_active_timer())
		return record and Timer(**record)

	@optional_connection
	async def get_expiry(self, channel: discord.TextChannel):
		return await connection().fetchval(self.queries.get_expiry(), channel.id)

	@optional_connection
	async def set_expiry(self, channel: discord.TextChannel, expiry: datetime.timedelta):
		await connection().execute(self.queries.set_expiry(), channel.guild.id, channel.id, expiry)

	@optional_connection
	async def set_last_timer_change(self, channel: discord.TextChannel, message_id):
		await connection().execute(self.queries.set_last_timer_change(), channel.guild.id, channel.id, message_id)

	@optional_connection
	async def delete_expiry(self, channel: discord.TextChannel):
		await connection().execute(self.queries.delete_expiry(), channel.id)

	@optional_connection
	async def delete_last_timer_change(self, channel_id):
		await connection().execute(self.queries.delete_last_timer_change(), channel_id)

	@optional_connection
	async def get_message_expiration(self, message_id) -> datetime.datetime:
		return await connection().fetchval(self.queries.get_message_expiration(), message_id)

	@optional_connection
	async def latest_message_per_channel(self, cutoff: int):
		async with connection().transaction():
			async for row in connection().cursor(self.queries.latest_message_per_channel(), cutoff):
				yield row

def setup(bot):
	bot.add_cog(DisappearingMessagesDatabase(bot))
