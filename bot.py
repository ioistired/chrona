#!/usr/bin/env python3

import asyncpg
from ben_cogs import BenCogsBot
import json5

import utils

class Chrona(BenCogsBot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs, setup_db=True)

	startup_extensions = (
		'cogs.timers',
#		'cogs.core',
		'jishaku',
		'ben_cogs.misc',
		'ben_cogs.debug',
#		'ben_cogs.stats',
		'ben_cogs.sql',
	)

	async def init_db(self):
		credentials = self.config['database']
		self.pool = await asyncpg.create_pool(**credentials, init=utils.asyncpg_set_json_codec)

if __name__ == '__main__':
	with open('config.json5') as f:
		config = json5.load(f)

	Chrona(config=config).run()
