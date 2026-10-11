-- Silver flights: one clean, typed row per flight.
-- Rules:
--   1. Convert text to proper types (dates, numbers, true/false).
--   2. Cancelled flights never arrived, so they have no arrival delay. Keep them, flag them.
--   3. If the same flight appears twice (e.g. a corrected file), keep the latest load.

with source as (
    select * from {{ source('bronze', 'flights') }}
),

typed as (
    select
        cast(FlightDate as date)                          as flight_date,
        Reporting_Airline                                 as carrier_code,
        cast(Flight_Number_Reporting_Airline as integer)  as flight_number,
        nullif(Tail_Number, '')                           as tail_number,
        Origin                                            as origin_airport,
        Dest                                              as dest_airport,
        lpad(CRSDepTime, 4, '0')                          as scheduled_dep_time,
        cast(left(lpad(CRSDepTime, 4, '0'), 2) as integer) as scheduled_dep_hour,

        try_cast(DepDelay as double)                      as dep_delay_min,
        try_cast(ArrDelay as double)                      as arr_delay_min,
        try_cast(Distance as double)                      as distance_miles,

        try_cast(Cancelled as double) = 1                 as is_cancelled,
        try_cast(Diverted  as double) = 1                 as is_diverted,
        nullif(CancellationCode, '')                      as cancellation_code,

        try_cast(CarrierDelay      as double)             as carrier_delay_min,
        try_cast(WeatherDelay      as double)             as weather_delay_min,
        try_cast(NASDelay          as double)             as nas_delay_min,
        try_cast(SecurityDelay     as double)             as security_delay_min,
        try_cast(LateAircraftDelay as double)             as late_aircraft_delay_min,

        _source_file,
        _loaded_at
    from source
),

deduplicated as (
    select *
    from typed
    qualify row_number() over (
        partition by flight_date, carrier_code, flight_number,
                     origin_airport, dest_airport, scheduled_dep_time
        order by _loaded_at desc
    ) = 1
)

select
    -- Business key: what makes a flight unique in the real world
    md5(concat_ws('|', flight_date, carrier_code, flight_number,
                  origin_airport, dest_airport, scheduled_dep_time)) as flight_id,
    *,
    -- 15 minutes is the official US definition of a delayed flight
    coalesce(arr_delay_min >= 15, false)                              as is_delayed
from deduplicated
