import datetime
import re

from ben_cogs.misc import natural_time
from discord.ext import commands

# Using code provided by Rapptz under the MIT License
# © 2015 Rapptz
# https://github.com/Rapptz/RoboDanny/blob/b8c427ad97372cb47f16397ff04a6b80e2494757/cogs/utils/time.py

class ShortTime(commands.Converter):
	compiled = re.compile("""
		(?:(?P<weeks>[0-9]{1,4})\s*(?:weeks?|w))?  # e.g. 10w
		(?:(?P<days>[0-9]{1,5})\s*(?:days?|d))?  # e.g. 14d
		(?:(?P<hours>[0-9]{1,5})\s*(?:hours?|h))?  # e.g. 12h
		(?:(?P<minutes>[0-9]{1,5})\s*(?:minutes?|m))?  # e.g. 10m
		(?:(?P<seconds>[0-9]{1,5})\s*(?:seconds?|s))?  # e.g. 15s
	""", re.VERBOSE)

	@classmethod
	async def convert(cls, ctx, argument):
		match = cls.compiled.fullmatch(argument)
		if match is None or not match.group(0):
			raise commands.BadArgument('invalid time provided')

		data = {k: int(v) for k, v in match.groupdict(default=0).items()}
		return datetime.timedelta(**data)

def human_timedelta(delta):
	return natural_time(delta.total_seconds())
