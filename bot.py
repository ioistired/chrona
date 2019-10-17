#!/usr/bin/env python3

from pathlib import Path

import asyncpg
import jinja2
from bot_bin.bot import Bot

import utils

class Chrona(Bot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs, setup_db=True)
		here = Path(__file__).parent
		self.jinja_env = jinja2.Environment(
			loader=jinja2.FileSystemLoader(str(here / 'sql')),
			line_statement_prefix='-- :')

	def queries(self, template_name):
		return self.jinja_env.get_template(template_name).module

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
