from discord.ext import commands

class Meta(commands.Cog):
	"""Commands that tell you about the bot itself."""

	@commands.command()
	async def source(self, ctx):
		await ctx.send('https://owo.codes/lambda/chrona')

def setup(bot):
	bot.add_cog(Meta())
