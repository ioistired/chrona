import datetime
import re

import inflect
inflect = inflect.engine()
import parsedatetime as pdt
from dateutil.relativedelta import relativedelta
from discord.ext import commands

from . import plural

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

def human_timedelta(dt, *, accuracy=3, brief=False, past=False):
	suffix = ' ago' if past else ''

	attrs = [
		('year', 'y'),
		('month', 'mo'),
		('day', 'd'),
		('hour', 'h'),
		('minute', 'm'),
		('second', 's'),
	]

	output = []
	for attr, brief_attr in attrs:
		elem = getattr(delta, attr + 's')
		if not elem:
			continue

		if attr == 'day':
			weeks = delta.weeks
			if weeks:
				elem -= weeks * 7
				if not brief:
					output.append(format(plural(weeks), 'week'))
				else:
					output.append(f'{weeks}w')

		if elem <= 0:
			continue

		if brief:
			output.append(f'{elem}{brief_attr}')
		else:
			output.append(format(plural(elem), attr))

	if accuracy is not None:
		output = output[:accuracy]

	if len(output) == 0:
		return 'now'
	else:
		if not brief:
			return inflect.join(output, conj='and') + suffix
		else:
			return ' '.join(output) + suffix
