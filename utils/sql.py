import asyncpg
import contextlib
import inspect
import re

import aiocontextvars

from . import attrdict

# this function is Public Domain
# https://creativecommons.org/publicdomain/zero/1.0/
def load_sql(fp):
	"""given a file-like object, read the queries delimited by `-- :name foo` comment lines
	return a dict mapping these names to their respective SQL queries
	the file-like is not closed afterwards.
	"""
	# tag -> list[lines]
	queries = attrdict()
	current_tag = ''

	for line in fp:
		match = re.match(r'\s*--\s*:name\s*(\S+).*?$', line)
		if match:
			current_tag = match[1]
			continue
		if current_tag:
			queries.setdefault(current_tag, []).append(line)

	for tag, query in queries.items():
		queries[tag] = ''.join(query)

	return queries

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
