CREATE TABLE expiries(
	-- not strictly necessary, but it's here so we can delete all expiries for a given guild
	guild_id BIGINT NOT NULL,
	channel_id BIGINT PRIMARY KEY,
	expiry INTERVAL NOT NULL,

	UNIQUE (guild_id, channel_id));

CREATE INDEX expiries_guild_id_idx ON expiries(guild_id);

CREATE TABLE timers(
	guild_id BIGINT NOT NULL,
	channel_id BIGINT NOT NULL,
	message_id BIGINT NOT NULL,
	expires TIMESTAMP WITHOUT TIME ZONE NOT NULL,

	-- ordered by access pattern
	PRIMARY KEY (message_id, channel_id));

-- for getting the soonest timer
CREATE INDEX "timers_expires_idx" ON timers (expires);

-- consider setting a timer for an invalid future date instead of using this table
-- that would obviate a full outer join and insertion into this table
CREATE TABLE last_timer_changes(
	guild_id BIGINT NOT NULL,
	channel_id BIGINT PRIMARY KEY,
	message_id BIGINT NOT NULL);
