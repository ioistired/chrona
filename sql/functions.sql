-- © 2019 lambda#0987
--
-- Chrona is free software: you can redistribute it and/or modify
-- it under the terms of the GNU Affero General Public License as
-- published by the Free Software Foundation, either version 3 of the
-- License, or (at your option) any later version.
--
-- Chrona is distributed in the hope that it will be useful,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
-- GNU Affero General Public License for more details.
--
-- You should have received a copy of the GNU Affero General Public License
-- along with Chrona. If not, see <https://www.gnu.org/licenses/>.

CREATE FUNCTION coalesce_max(x anyelement, y anyelement) RETURNS anyelement AS $$ BEGIN
	IF x IS NULL OR x < y THEN
		RETURN y; END IF;
	RETURN x; END $$ LANGUAGE 'plpgsql';
