# © 2019–2020 lambda#0987
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

import asyncio
import collections
import contextlib
import datetime
import math
import os.path
import time
import typing

import discord
from bot_bin.misc import absolute_natural_timedelta, natural_timedelta
from bot_bin.sql import connection
from discord.ext import commands

from utils.converter import Message
from utils.time import ShortTime

class DisappearingMessages(commands.Cog):
	def __init__(self, bot):
		self.started_at = datetime.datetime.utcnow()
		self.bot = bot
		self.db = bot.cogs['DisappearingMessagesDatabase']
		# TODO make these one LRU
		self.to_keep_locks = collections.defaultdict(asyncio.Lock)
		self.to_keep = collections.defaultdict(set)

		self.handle_missed_task = self.bot.loop.create_task(self.handle_missed())

	async def handle_missed(self):
		await self.bot.wait_until_ready()

		cutoff = discord.utils.time_snowflake(self.started_at, high=True)
		async for channel_id, message_id, expiry in self.db.latest_message_per_channel(cutoff):
			channel = self.bot.get_channel(channel_id)
			if not channel:
				continue

			to_purge = []
			async for m in channel.history(after=discord.Object(message_id), limit=None):
				if m.created_at < datetime.datetime.utcnow() - expiry:
					to_purge.append(m)
				else:
					await self.db.create_timer(m, expiry)

			await channel.delete_messages(to_purge)

	def cog_unload(self):
		self.handle_missed_task.cancel()

	@commands.Cog.listener()
	async def on_message(self, message):
		if not message.guild:
			return

		async with self.to_keep_locks[message.channel.id]:
			with contextlib.suppress(LookupError):
				self.to_keep[message.channel.id].remove(message.id)
				return

		expiry = await self.db.get_expiry(message.channel)
		if expiry is None:
			return

		await self.db.create_timer(message, expiry)

	@commands.group(invoke_without_command=True)
	async def timer(self, ctx, channel: discord.TextChannel = None):
		"""Get the current disappearing message timer for this channel or another"""
		if ctx.invoked_subcommand is not None:
			return

		channel = channel or ctx.channel
		expiry = await self.db.get_expiry(channel)
		if expiry is None:
			emoji = self.bot.config['timer_disable_emoji']
			await ctx.send(f'{emoji} This channel does not have disappearing messages set up.')
		else:
			noun = 'this channel' if channel == ctx.channel else channel.mention
			await ctx.send(
				f'The current disappearing message timer for {noun} channel is '
				f'**{absolute_natural_timedelta(expiry.total_seconds())}**.')

	@timer.command(name='set', usage='[channel] <time interval>')
	async def set_timer(self, ctx, channel: typing.Optional[discord.TextChannel] = None, *, expiry: ShortTime):
		"""Set the disappearing messages timer for the given channel or the current one.

		Messages sent in that channel will be deleted after the given amount of time.
		You must have the Manage Channels permission on that channel in order to set the disappearing messages
		timer.
		"""
		channel = channel or ctx.channel
		if not channel.permissions_for(ctx.author).manage_channels:
			raise commands.MissingPermissions(['manage_channels'])

		# for consistency with already having a timer, also delete the invoking message
		# even when no timer is set
		async with self.to_keep_locks[channel.id]:
			self.to_keep[channel.id].add(ctx.message.id)
			await self.db.create_timer(ctx.message, expiry)

		async with self.bot.pool.acquire() as conn, conn.transaction():
			connection.set(conn)
			await self.db.set_expiry(channel, expiry)

			emoji = self.bot.config['timer_change_emoji']
			async with self.to_keep_locks[channel.id]:
				m = await channel.send(
					f'{emoji} {ctx.author.mention} set the disappearing message timer to '
					f'**{absolute_natural_timedelta(expiry.total_seconds())}**.')
				self.to_keep[channel.id].add(m.id)
			await self.db.set_last_timer_change(channel, m.id)

	@timer.command(name='delete', aliases=['rm', 'del', 'remove', 'disable'])
	async def delete_timer(self, ctx, channel: discord.TextChannel = None):
		"""Delete the disappearing messages timer for the given channel or the current one.

		Messages sent in that channel will no longer be deleted.
		You must have the Manage Channels permission on that channel in order to delete the disappearing messages
		timer.
		"""
		channel = channel or ctx.channel
		if not channel.permissions_for(ctx.author).manage_channels:
			raise commands.MissingPermissions(['manage_channels'])

		async with self.bot.pool.acquire() as conn, conn.transaction():
			connection.set(conn)
			await self.db.delete_expiry(channel)
			await self.db.delete_last_timer_change(channel.id)

		async with self.to_keep_locks[channel.id]:
			emoji = self.bot.config['timer_disable_emoji']
			m = await channel.send(f'{emoji} {ctx.author.mention} disabled disappearing messages.')
			self.to_keep[channel.id].add(m.id)

	@commands.command(name='time-left', aliases=['when'])
	async def time_left(self, ctx, message: Message):
		expires_at = await self.db.get_message_expiration(message.id)
		if expires_at is None:
			await ctx.send(f'{self.bot.config["timer_disable_emoji"]} That message will not disappear.')
			return

		now = datetime.datetime.utcnow()
		time_left = expires_at - now
		time_elapsed = now - message.created_at
		expiry = expires_at - message.created_at

		emoji = self.timer_emoji(time_elapsed, expiry)

		await self.db.create_or_update_timer(ctx.message, time_left)
		async with self.to_keep_locks[ctx.channel.id]:
			# time left messages disappear when the message does
			m = await ctx.send(f'{emoji} That message will disappear in **{natural_timedelta(expires_at)}**.')
			self.to_keep[ctx.channel.id].add(m.id)
			await self.db.create_timer(m, time_left)

	@commands.Cog.listener()
	async def on_message_expiration(self, timer):
		with contextlib.suppress(discord.HTTPException):
			await self.bot.http.delete_message(timer.channel_id, timer.message_id)

	def timer_emoji(self, time_elapsed, expiry):
		elapsed_coeff = max(0, min(1, time_elapsed.total_seconds() / expiry.total_seconds()))
		emojis = self.bot.config['timer_emojis']
		# err on the side of more time left, allowing a new message to show the first emoji
		i = max(0, min(len(emojis) - 1, math.floor(elapsed_coeff * len(emojis))))
		return emojis[i]

def setup(bot):
	bot.add_cog(DisappearingMessages(bot))
