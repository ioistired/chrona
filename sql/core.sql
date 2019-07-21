-- :name get_expiry
-- params: channel_id
SELECT expiry
FROM expiries
WHERE channel_id = $1

-- :name set_expiry
-- params: guild_id, channel_id, expiry
INSERT INTO expiries(guild_id, channel_id, expiry)
VALUES ($1, $2, $3)
ON CONFLICT (channel_id) DO UPDATE
SET expiry = EXCLUDED.expiry

-- :name delete_expiry
-- params: channel_id
DELETE FROM expiries
WHERE channel_id = $1

-- :name get_message_expiration
-- params: message_id
SELECT expires
FROM timers
WHERE (payload -> 'kwargs' -> 'message_id')::bigint = $1

-- :name latest_message_per_channel
SELECT channel_id, coalesce(max_per_channel.message_id, last_timer_changes.message_id), expiry
FROM (
	SELECT
		(payload -> 'kwargs' -> 'channel_id')::bigint AS channel_id,
		max((payload -> 'kwargs' -> 'message_id')::bigint) AS message_id
	FROM timers
	GROUP BY channel_id) AS max_per_channel
	FULL OUTER JOIN last_timer_changes USING (channel_id)
	INNER JOIN expiries USING (channel_id);

-- :name set_last_timer_change
-- params: guild_id, channel_id, message_id
INSERT INTO last_timer_changes
VALUES ($1, $2, $3)
ON CONFLICT (channel_id) DO UPDATE
SET message_id = EXCLUDED.message_id

-- :name delete_last_timer_change
-- params: channel_id
DELETE FROM last_timer_changes
WHERE channel_id = $1
