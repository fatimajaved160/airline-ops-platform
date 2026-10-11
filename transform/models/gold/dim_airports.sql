-- dim_airports: one row per airport that has an IATA code.
--
-- Row rule: keep only airports with a 3-letter IATA code. Flights join on that code,
-- so an airport without one can never match a flight. Filtering on the code (not on
-- airport type) keeps small regional airports that do have flights, and drops closed
-- airports, heliports and balloon ports automatically.
-- Checked: no IATA code appears twice, so iata_code is the primary key.

select
    iata_code,                                         -- 3-letter code, join key to flights
    ident                                as icao_code, -- 4-letter code, used by other systems (e.g. OpenSky)
    cast(id as integer)                  as source_airport_id, -- OurAirports id, never changes
    name                                 as airport_name,
    type                                 as airport_type,
    municipality                         as city,
    iso_region                           as region,
    iso_country                          as country,
    try_cast(latitude_deg  as double)    as latitude,
    try_cast(longitude_deg as double)    as longitude,
    try_cast(elevation_ft  as integer)   as elevation_ft,
    _loaded_at                                         -- audit column: when this row was loaded
from {{ source('bronze', 'airports') }}
where nullif(iata_code, '') is not null
