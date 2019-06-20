import asyncio
import datetime
import os.path

import asyncpg
import discord
from discord.ext import commands
from discord.ext import tasks

from .db import Timer
from utils.sql import connection, optional_connection, load_sql
from utils.time import human_timedelta

# Using code provided by Rapptz under the MIT License
# © 2015 Rapptz
# https://raw.githubusercontent.com/Rapptz/RoboDanny/rewrite/cogs/reminder.py

class TimerDatabase(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.db = bot.cogs['TimerDatabase']
		self._current_timer = None
		self._have_timer = asyncio.Event()
		self._task = self.bot.loop.create_task(self._dispatch_timers())

	# be careful not to use @optional_connection here, as that would potentially hold open connections for too long
	async def _wait_for_active_timer(self):
		timer = self._active_timer = await self.db.get_active_timer()
		if timer is not None:
			self._have_timer.set()
			return timer

		# no timers found in the DB
		self._have_timer.clear()
		await self._have_timer.wait()
		timer = self._active_timer = await self.db.get_active_timer()
		return timer

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
		await self.db.delete_timer(timer)
		self.dispatch_timer(timer)

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

		Note
		------
		Arguments and keyword arguments must be JSON serialisable.

		Returns
		--------
		:class:`Timer`
		"""
		event, when, *args = args

		now = datetime.datetime.utcnow()
		timer = Timer(event=event, args=args, kwargs=kwargs, expires=when, created_at=now)
		delta = (when - now).total_seconds()
		if delta <= 60:
			self.bot.loop.create_task(self._short_timer_optimization(timer))
			return timer

		timer.id = await self.db.create_timer(event, when, {'args': args, 'kwargs': kwargs})

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
