-- fct_flights: one row per flight, linked to the airline version that was valid on the flight date.
--
-- The airline join is "point in time": a flight is matched to whichever version of its airline
-- was valid on flight_date, not simply the current one. That is what makes the history useful.

select
    f.flight_id,
    f.flight_date,
    a.airline_key,
    f.carrier_code,
    f.flight_number,
    f.tail_number,
    f.origin_airport,
    f.dest_airport,
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
from {{ ref('stg_flights') }} f
left join {{ ref('dim_airlines') }} a
    on  f.carrier_code = a.carrier_code
    and f.flight_date >= a.valid_from
    and f.flight_date <  a.valid_to
