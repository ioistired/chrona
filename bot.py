#!/usr/bin/env python3

import asyncpg
import querypp
from bot_bin.bot import Bot

import utils

class Chrona(Bot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs, setup_db=True)
		self.jinja_env = querypp.QueryEnvironment('sql')

	startup_extensions = (
		'cogs.core.db',
		'cogs.core.commands',
		'jishaku',
		'bot_bin.misc',
		'bot_bin.debug',
		'bot_bin.stats',
		'bot_bin.sql',
		'cogs.meta',
	)

if __name__ == '__main__':
	with open('config.py') as f:
		config = eval(f.read(), {})

	Chrona(config=config).run()
