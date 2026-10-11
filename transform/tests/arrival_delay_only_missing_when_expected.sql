-- A flight that was not cancelled or diverted must have an arrival delay.
-- Any rows returned here are a data quality failure.
select flight_id, flight_date, carrier_code, flight_number
from {{ ref('stg_flights') }}
where arr_delay_min is null
  and not is_cancelled
  and not is_diverted
