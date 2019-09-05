import asyncpg
import contextlib
import inspect
import re

import aiocontextvars

_connection = aiocontextvars.ContextVar('connection')
# make the interface a bit cleaner
connection = lambda: _connection.get()
connection.set = _connection.set

def optional_connection(func):
	"""Decorator that acquires a connection for the decorated function if the contextvar is not set."""
	class set_connection:
		def __init__(self, pool):
			self.pool = pool
		async def __aenter__(self):
			try:
				# allow someone to call a decorated function twice within the same Task
				# the second time, a new connection will be acquired
				connection().is_closed()
			except (asyncpg.InterfaceError, LookupError):
				self.connection = conn = await self.pool.acquire()
				connection.set(conn)
				return conn
			else:
				return connection()
		async def __aexit__(self, *excinfo):
			with contextlib.suppress(AttributeError):
				await self.connection.close()

	if inspect.isasyncgenfunction(func):
		async def inner(self, *args, **kwargs):
			async with set_connection(self.bot.pool) as conn:
				# this does not handle two-way async gens, but i don't have any of those either
				async for x in func(self, *args, **kwargs):
					yield x
	else:
		async def inner(self, *args, **kwargs):
			async with set_connection(self.bot.pool) as conn:
				return await func(self, *args, **kwargs)

	return inner
