import asyncio
import json
import re
import sys

async def asyncpg_set_json_codec(conn):
	await conn.set_type_codec(
		'jsonb',
		schema='pg_catalog',
		encoder=json.dumps,
		decoder=json.loads,
		format='text')

attrdict = type('attrdict', (dict,), {
	'__getattr__': dict.__getitem__,
	'__setattr__': dict.__setitem__,
	'__delattr__': dict.__delitem__})

# Using code provided by Rapptz under the MIT License
# © 2015 Rapptz
# https://github.com/Rapptz/RoboDanny/blob/6fd16002e0cbd3ed68bf5a8db10d61658b0b9d51/cogs/utils/formats.py

class plural:
    def __init__(self, value):
        self.value = value

    def __format__(self, format_spec):
        v = self.value
        singular, sep, plural = format_spec.partition('|')
        plural = plural or f'{singular}s'
        if abs(v) != 1:
            return f'{v} {plural}'
        return f'{v} {singular}'

ASYNCIO_MAX_SLEEP = 40 * 60 * 60 * 24

if sys.version_info >= (3, 7):
	sleep = asyncio.sleep
else:
	async def sleep(delay, result=None, *, loop=None):
		"""Sleep for any amount of time, even above the maximum allowed by asyncio.
		See https://bugs.python.org/issue20493.

		Args are identical to asyncio.sleep.
		"""
		while delay > ASYNCIO_MAX_SLEEP:
			await asyncio.sleep(ASYNCIO_MAX_SLEEP)
			delta -= ASYNCIO_MAX_SLEEP
		await asyncio.sleep(delta)
