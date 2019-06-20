import re

import discord
from discord.ext.commands import Converter, errors

# Using code provided by khazhyk under the MIT License
# © 2017 khazhyk
# https://github.com/khazhyk/dango.py/blob/53fde0538eb8ee063fb10fdf85c29eb7c3bbaae9/dango/plugins/common/converters.py

MESSAGE_ID_RE = re.compile(r'^(?:(?P<channel_id>[0-9]{15,21})[-/:])?(?P<message_id>[0-9]{15,21})$')
MESSAGE_LINK_RE = re.compile(
	r'^https?://(?:(ptb|canary)\.)?discordapp\.com/channels/'
	r'(?:([0-9]{15,21})|(@me))'
	r'/(?P<channel_id>[0-9]{15,21})/(?P<message_id>[0-9]{15,21})$')

class MessageId(Converter):
	"""Match message_id, channel-message_id, or jump url to a discord.Channel, message_id pair

	Author must be able to view the target channel.
	"""

	async def convert(self, ctx, argument):
		match = MESSAGE_ID_RE.match(argument) or MESSAGE_LINK_RE.match(argument)
		if not match:
			raise errors.BadArgument("{} doesn't look like a message to me...".format(argument))

		msg_id = int(match.group("message_id"))
		channel_id = int(match.group("channel_id") or ctx.channel.id)
		channel = ctx.guild.get_channel(channel_id)
		if not channel:
			channel = ctx.bot.get_channel(channel_id)

		if not channel:
			raise errors.BadArgument("Channel {} not found".format(channel_id))

		author = channel.guild.get_member(ctx.author.id)

		if not channel.guild.me.permissions_in(channel).read_messages:
			raise errors.CheckFailure("I don't have permission to view channel {0.mention}".format(channel))
		if not author or not channel.permissions_for(author).read_messages:
			raise errors.CheckFailure("You don't have permission to view channel {0.mention}".format(channel))

		return (channel, msg_id)


class Message(Converter):
	"""Match message_id, channel-message_id, or jump url to a discord.Message"""
	async def convert(self, ctx, argument):
		channel, msg_id = await MessageIdConverter().convert(ctx, argument)

		msg = discord.utils.get(ctx.bot.cached_messages, id=msg_id)
		if msg is None:
			try:
				msg = await channel.fetch_message(msg_id)
			except discord.NotFound:
				raise errors.BadArgument("Message {0} not found in channel {1.mention}".format(msg_id, channel))
			except discord.Forbidden:
				raise errors.CheckFailure("I don't have permission to view channel {0.mention}".format(channel))
		elif msg.channel.id != channel.id:
			raise errors.BadArgument("Message not found")
		return msg
