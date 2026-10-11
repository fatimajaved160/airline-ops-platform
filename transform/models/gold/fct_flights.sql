-- fct_flights: one row per flight, linked to airports and the airline version valid on the flight date.
--
-- Airports: flights carry 3-letter codes, which can change over time. Each flight's code is resolved
-- to the airport's stable 4-letter ICAO code, first through seeds/airport_code_aliases.csv
-- (known code changes), then through the current code in dim_airports.
--
-- Airlines: "point in time" join. A flight is matched to the airline version valid on flight_date.

with flights as (
    select * from {{ ref('stg_flights') }}
),

airports as (
    select iata_code, icao_code from {{ ref('dim_airports') }}
),

aliases as (
    select flight_code, icao_code from {{ ref('airport_code_aliases') }}
)

select
    f.flight_id,
    f.flight_date,
    a.airline_key,
    f.carrier_code,
    f.flight_number,
    f.tail_number,
    f.origin_airport,
    f.dest_airport,
    coalesce(origin_alias.icao_code, origin_ap.icao_code) as origin_icao,
    coalesce(dest_alias.icao_code,   dest_ap.icao_code)   as dest_icao,
    f.scheduled_dep_time,
    f.scheduled_dep_hour,
    f.distance_miles,
    f.dep_delay_min,
    f.arr_delay_min,
    f.is_delayed,
    f.is_cancelled,
    f.is_diverted,
    f.cancellation_code,
    f.carrier_delay_min,
    f.weather_delay_min,
    f.nas_delay_min,
    f.security_delay_min,
    f.late_aircraft_delay_min
from flights f
left join aliases  origin_alias on f.origin_airport = origin_alias.flight_code
left join airports origin_ap    on f.origin_airport = origin_ap.iata_code
left join aliases  dest_alias   on f.dest_airport   = dest_alias.flight_code
left join airports dest_ap      on f.dest_airport   = dest_ap.iata_code
left join {{ ref('dim_airlines') }} a
    on  f.carrier_code = a.carrier_code
    and f.flight_date >= a.valid_from
    and f.flight_date <  a.valid_to
