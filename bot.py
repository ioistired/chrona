#!/usr/bin/env python3

# © 2019 lambda#0987
#
# Chrona is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Chrona is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Chrona. If not, see <https://www.gnu.org/licenses/>.

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
