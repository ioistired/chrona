import asyncio
import sys

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
