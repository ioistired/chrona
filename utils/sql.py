import asyncpg
import inspect
import re

import aiocontextvars
from async_exit_stack import AsyncExitStack

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
# optimize this getattr so it's cleaner and faster
connection = lambda _get_connection=_connection.get: _get_connection()
connection.set = _connection.set

def optional_connection(func):
	"""Decorator that acquires a connection for the decorated function if the contextvar is not set."""
	async def get_conn(self):
		stack = AsyncExitStack()

		try:
			# allow someone to call a decorated function twice within the same Task
			# the second time, a new connection will be acquired
			connection().is_closed()
		except (asyncpg.InterfaceError, LookupError):
			connection.set(await stack.enter_async_context(self.bot.pool.acquire()))

		return stack

	if inspect.isasyncgenfunction(func):
		async def inner(self, *args, **kwargs):
			async with await get_conn(self):
				async for x in func(self, *args, **kwargs):
					yield x
	else:
		async def inner(self, *args, **kwargs):
			async with await get_conn(self):
				return await func(self, *args, **kwargs)

	return inner
