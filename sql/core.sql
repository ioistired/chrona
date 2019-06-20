-- :name get_expiry
-- params: guild_id, channel_id
SELECT expiry
FROM expiries
WHERE guild_id = $1 AND channel_id = $2

-- :name set_expiry
-- params: guild_id, channel_id, expiry
INSERT INTO expiries(guild_id, channel_id, expiry)
VALUES ($1, $2, $3)
ON CONFLICT (guild_id, channel_id)
DO UPDATE SET expiry = EXCLUDED.expiry

-- :name get_message_expiration
-- params: message_id
SELECT expires
FROM timers
WHERE payload -> 'kwargs' -> 'message_id' = $1
