"""
Shared daily-aggregation SQL generator for weather data.

Public API:
    build_aggregation_sql(source_name, table_name=None, where_clause=None) -> str

Returns the full aggregation SELECT for a given source (e.g. "weather_10sec"
or "weather_regular"). Consumers like weather-api-py import this to run the
same calculations against a live DuckDB connection holding cached data.

The SOURCES / AGGS / VARIABLES config in render_sql.py is the single source
of truth for every column produced by the daily rollup.
"""

from .render_sql import build_aggregation_sql

__all__ = ["build_aggregation_sql"]
