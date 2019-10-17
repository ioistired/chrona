-- :macro get_expiry()
-- params: channel_id
SELECT expiry
FROM expiries
WHERE channel_id = $1
-- :endmacro

-- :macro set_expiry()
-- params: guild_id, channel_id, expiry
INSERT INTO expiries(guild_id, channel_id, expiry)
VALUES ($1, $2, $3)
ON CONFLICT (channel_id) DO UPDATE
SET expiry = EXCLUDED.expiry
-- :endmacro

-- :macro delete_expiry()
-- params: channel_id
DELETE FROM expiries
WHERE channel_id = $1
-- :endmacro

-- :macro get_message_expiration()
-- params: message_id
SELECT expires
FROM timers
WHERE message_id = $1
-- :endmacro

-- :macro latest_message_per_channel()
-- params: cutoff_time (as snowflake, upper bound)
SELECT channel_id, coalesce_max(max_per_channel.message_id, last_timer_changes.message_id), expiry
FROM (
		SELECT channel_id, max(message_id) AS message_id
		FROM timers
		WHERE message_id < $1
		GROUP BY channel_id
	) AS max_per_channel
	FULL OUTER JOIN last_timer_changes USING (channel_id)
	INNER JOIN expiries USING (channel_id)
-- :endmacro

-- :macro set_last_timer_change()
-- params: guild_id, channel_id, message_id
INSERT INTO last_timer_changes (guild_id, channel_id, message_id)
VALUES ($1, $2, $3)
ON CONFLICT (channel_id) DO UPDATE
	SET message_id = EXCLUDED.message_id
-- :endmacro

-- :macro delete_last_timer_change()
-- params: channel_id
DELETE FROM last_timer_changes
WHERE channel_id = $1
-- :endmacro

-- :macro get_active_timer()
SELECT *
FROM timers
ORDER BY expires
LIMIT 1
-- :endmacro

-- :macro create_timer()
INSERT INTO timers (guild_id, channel_id, message_id, expires)
VALUES ($1, $2, $3, $4)
-- :if 'upsert' in varargs
ON CONFLICT (channel_id, message_id) DO UPDATE
	SET expires = EXCLUDED.expires
	WHERE EXCLUDED.expires < timers.expires
-- :endif
-- :endmacro

-- :macro delete_timer()
-- params: channel_id, message_id
DELETE FROM timers
WHERE channel_id = $1 AND message_id = $2
-- :endmacro
