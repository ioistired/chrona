#!/usr/bin/env python3

import asyncpg
import querypp
from ben_cogs.bot import BenCogsBot

import utils

class Chrona(BenCogsBot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs, setup_db=True)
		self.jinja_env = querypp.QueryEnvironment('sql')

	startup_extensions = (
		'cogs.core.db',
		'cogs.core.commands',
		'jishaku',
		'ben_cogs.misc',
		'ben_cogs.debug',
		'ben_cogs.stats',
		'ben_cogs.sql',
		'cogs.meta',
	)

	async def init_db(self):
		credentials = self.config['database']
		self.pool = await asyncpg.create_pool(**credentials, init=utils.asyncpg_set_json_codec)

if __name__ == '__main__':
	with open('config.py') as f:
		config = eval(f.read(), {})

	Chrona(config=config).run()
