{
	# @mentions will always work
	'prefixes': [],

	'database': {
		# possible values documented here:
		# https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.connection.connect
	},

	'tokens': {
		'discord': '',
		'stats': {
			'discord.bots.gg': None,
			'discordbots.org': None,
			'lbots.org': None,
		},
	},

	'success_emojis': {False: '❌', True: '✅'},

	# these are shown next to the amount of time left before a message expires
	# they should be in ascending order of amount of time left,
	# ie the first emoji is shown when a message is about to expire,
	# and the last emoji is shown for a new-ish message
	'timer_emojis': [
		'⌛',
		'⏳',
	],

	# the contents of this file will be shown by the copyright command
	'copyright_license_file': '',
}
