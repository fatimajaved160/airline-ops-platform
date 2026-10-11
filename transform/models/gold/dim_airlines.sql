-- dim_airlines: one row per VERSION of each airline (SCD Type 2).
--
-- If an airline is renamed, it gets a new row. The old row keeps its name and gets an end date,
-- so flights before the change still show the old name and flights after show the new one.
--
-- valid_from: dbt records when it first saw each version, i.e. the day we ran it. The first
-- version of every airline is treated as valid from the beginning of time, so flights older
-- than this project still find their airline.

with versions as (
    select
        *,
        row_number() over (partition by carrier_code order by dbt_valid_from) as version_number
    from {{ ref('carriers_snapshot') }}
)

select
    dbt_scd_id                                     as airline_key,  -- unique per version
    carrier_code,
    carrier_name,
    icao_code,
    carrier_type,
    version_number,
    case when version_number = 1 then timestamp '1900-01-01'
         else dbt_valid_from end                   as valid_from,
    coalesce(dbt_valid_to, timestamp '9999-12-31') as valid_to,
    dbt_valid_to is null                           as is_current
from versions
