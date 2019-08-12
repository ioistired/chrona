CREATE FUNCTION coalesce_max(x bigint, y bigint) RETURNS bigint AS $$ BEGIN
	IF x IS NULL OR x < y THEN
		RETURN y; END IF;
	RETURN x; END $$ LANGUAGE 'plpgsql';
