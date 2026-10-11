-- History rule: every airline must have exactly one current version.
select carrier_code, count(*) as current_versions
from {{ ref('dim_airlines') }}
where is_current
group by carrier_code
having count(*) <> 1
