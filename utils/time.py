import datetime
import re

import inflect
inflect = inflect.engine()
import parsedatetime as pdt
from dateutil.relativedelta import relativedelta

from . import plural

# Using code provided by Rapptz under the MIT License
# © 2015 Rapptz
# https://github.com/Rapptz/RoboDanny/blob/b8c427ad97372cb47f16397ff04a6b80e2494757/cogs/utils/time.py

class ShortTime:
	compiled = re.compile("""(?:(?P<years>[0-9])(?:years?|y))?			   # e.g. 2y
							 (?:(?P<months>[0-9]{1,2})(?:months?|mo))?	   # e.g. 2months
							 (?:(?P<weeks>[0-9]{1,4})(?:weeks?|w))?		   # e.g. 10w
							 (?:(?P<days>[0-9]{1,5})(?:days?|d))?		   # e.g. 14d
							 (?:(?P<hours>[0-9]{1,5})(?:hours?|h))?		   # e.g. 12h
							 (?:(?P<minutes>[0-9]{1,5})(?:minutes?|m))?	   # e.g. 10m
							 (?:(?P<seconds>[0-9]{1,5})(?:seconds?|s))?	   # e.g. 15s
						  """, re.VERBOSE)

	def __init__(self, argument):
		match = self.compiled.fullmatch(argument)
		if match is None or not match.group(0):
			raise commands.BadArgument('invalid time provided')

		data = {k: int(v) for k, v in match.groupdict(default=0).items()}
		now = datetime.datetime.utcnow()
		self.dt = now + relativedelta(**data)


def human_timedelta(dt, *, source=None, accuracy=3, brief=False, suffix=True):
	now = source or datetime.datetime.utcnow()
	# Microsecond free zone
	now = now.replace(microsecond=0)
	dt = dt.replace(microsecond=0)

	# This implementation uses relativedelta instead of the much more obvious
	# divmod approach with seconds because the seconds approach is not entirely
	# accurate once you go over 1 week in terms of accuracy since you have to
	# hardcode a month as 30 or 31 days.
	# A query like "11 months" can be interpreted as "!1 months and 6 days"
	if dt > now:
		delta = relativedelta(dt, now)
		suffix = ''
	else:
		delta = relativedelta(now, dt)
		suffix = ' ago' if suffix else ''

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
