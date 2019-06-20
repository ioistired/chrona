import asyncio
import datetime
import os.path

import asyncpg
import discord
from discord.ext import commands
from discord.ext import tasks

from utils.sql import load_sql
from utils.time import human_timedelta

# Using code provided by Rapptz under the MIT License
# © 2015 Rapptz
# https://raw.githubusercontent.com/Rapptz/RoboDanny/rewrite/cogs/reminder.py

# https://bugs.python.org/issue20493
ASYNCIO_MAX_SLEEP = 40 * 60 * 60 * 24

class Timer:
	__slots__ = frozenset(('args', 'kwargs', 'event', 'id', 'created_at', 'expires'))

	def __init__(self, *, id=None, args, kwargs, event, created_at, expires):
		self.id = id
		self.args = args
		self.kwargs = kwargs
		self.event = event
		self.created_at = created_at
		self.expires = expires

	async def sleep_until_complete(self):
		now = datetime.datetime.utcnow()
		if self.expires < now:
			return

		delta = (self.expires - now).total_seconds()
		while delta > ASYNCIO_MAX_SLEEP:
			await asyncio.sleep(ASYNCIO.MAX_SLEEP)
			delta -= ASYNCIO_MAX_SLEEP
		await asyncio.sleep(delta)

	@classmethod
	def from_record(cls, record):
		id = record['timer_id']

		payload = record['payload']
		args = payload.get('args', [])
		kwargs = payload.get('kwargs', {})
		event = record['event']
		created_at = record['created']
		expires = record['expires']

		return cls(id=id, args=args, kwargs=kwargs, event=event, created_at=created_at, expires=expires)

	@property
	def human_delta(self):
		return human_timedelta(self.created_at)

	def __repr__(self):
		return f'<Timer created_at={self.created_at} expires={self.expires} event={self.event}>'

	def __eq__(self, other):
		if self.id is None:
			return self is other
		return self.id == other.id

	def __hash__(self):
		return hash(self.id)

class TimerDatabase(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

		with open(os.path.join('sql', 'timers.sql')) as f:
			self.queries = load_sql(f)

		self._current_timer = None
		self._have_timer = asyncio.Event()
		self._task = self.bot.loop.create_task(self._dispatch_timers())

	async def get_active_timer(self, *, connection=None):
		conn = connection or self.bot.pool
		record = await conn.fetchrow(self.queries.get_active_timer)
		self._current_timer = ret = Timer.from_record(record) if record else None
		return ret

	async def _wait_for_active_timer(self, *, connection=None):
		timer = await self.get_active_timer(connection=connection)
		if timer is not None:
			self._have_timer.set()
			return timer

		# no timers found in the DB
		self._have_timer.clear()
		await self._have_timer.wait()
		return await self.get_active_timer(connection=connection)

	async def _dispatch_timers(self):
		try:
			while not self.bot.is_closed():
				timer = await self._wait_for_active_timer()
				await timer.sleep_until_complete()
				await self._handle_timer(timer)
		except (OSError, discord.ConnectionClosed, asyncpg.PostgresConnectionError):
			self._task.cancel()
			self._task = self.bot.loop.create_task(self._dispatch_timers())

	async def _handle_timer(self, timer):
		await self.delete_timer(timer)
		self.dispatch_timer(timer)

	async def delete_timer(self, timer):
		if timer.id is not None:
			await self.bot.pool.execute(self.queries.delete_timer, timer.id)

	async def create_timer(self, *args, **kwargs):
		r"""Creates a timer.

		Parameters
		-----------
		event: str
			The name of the event to trigger.
			Will transform to 'on_{event}_timer_complete'.
		when: datetime.datetime
			When the timer should fire.
		\*args
			Arguments to pass to the event
		\*\*kwargs
			Keyword arguments to pass to the event
		connection: asyncpg.Connection
			Special keyword-only argument to use a specific connection
			for the DB request.

		Note
		------
		Arguments and keyword arguments must be JSON serialisable.

		Returns
		--------
		:class:`Timer`
		"""
		event, when, *args = args
		connection = kwargs.get('connection', self.bot.pool)

		now = datetime.datetime.utcnow()
		timer = Timer(event=event, args=args, kwargs=kwargs, expires=when, created_at=now)
		delta = (when - now).total_seconds()
		if delta <= 5:
			self.bot.loop.create_task(self._short_timer_optimization(timer))
			return timer

		timer.id = await connection.execute(self.queries.create_timer, event, when, {'args': args, 'kwargs': kwargs})

		self._have_timer.set()

		if self._current_timer and timer.expires < self._current_timer.expires:
			self._current_timer = timer
			self._task.cancel()
			self.bot.loop.create_task(self._dispatch_timers())

		return timer

	async def _short_timer_optimization(self, timer):
		await timer.sleep_until_complete()
		self.dispatch_timer(timer)

	def dispatch_timer(self, timer):
		self.bot.dispatch(f'{timer.event}_timer_complete', timer)

def setup(bot):
	bot.add_cog(TimerDatabase(bot))
