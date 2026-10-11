-- Use the schema name exactly as written (silver, gold) instead of dbt's default "main_silver"
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name if custom_schema_name else target.schema }}
{%- endmacro %}
