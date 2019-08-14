CREATE FUNCTION coalesce_max(x anyelement, y anyelement) RETURNS anyelement AS $$ BEGIN
	IF x IS NULL OR x < y THEN
		RETURN y; END IF;
	RETURN x; END $$ LANGUAGE 'plpgsql';
