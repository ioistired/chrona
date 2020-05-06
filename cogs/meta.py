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

import discord
from discord.ext import commands

class Meta(commands.Cog):
	"""Commands that tell you about the bot itself."""

	# this is hardcoded because if you need to change it (ie you forked it) then just modify it in your fork
	REPO = '<https://owo.codes/lambda/chrona>'

	@commands.command()
	async def about(self, ctx):
		"""Tells you about the bot."""
		await ctx.send(
			"Hello! I'm a bot created by lambda#0987 that implements the Disappearing Messages feature from Signal. "
			'Any channel with a timer set up will have all its messages disappear after a set amount of time. '
			f'To set it up, use the __{ctx.prefix}timer set__ command. '
			f'For info on my other commands, use __{ctx.prefix} help__. '
			f'For my source code and copyright information, visit {self.REPO}.')

	@commands.command()
	async def invite(self, ctx):
		"""Gives you a link to invite me to your server."""
		p = discord.Permissions()
		p.update(manage_messages=True)
		await ctx.send('<%s>' % discord.utils.oauth_url(ctx.bot.user.id, p))

	@commands.command()
	async def source(self, ctx):
		await ctx.send(self.REPO)

def setup(bot):
	bot.add_cog(Meta())
