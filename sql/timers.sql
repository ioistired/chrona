-- :name get_active_timer
SELECT *
FROM timers
ORDER BY expires
LIMIT 1

-- :name create_timer
-- params: event, expires, payload
INSERT INTO timers(event, expires, payload)
VALUES ($1, $2, $3::jsonb)
RETURNING timer_id

-- :name delete_timer
-- params: timer_id
DELETE FROM timers WHERE timer_id = $1
