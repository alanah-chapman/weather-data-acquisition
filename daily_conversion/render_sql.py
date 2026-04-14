"""
Data-driven generator for the weather_daily aggregation SQL.

This module replaces the old hand-written template file with declarative
Python config: three constants (SOURCES, AGGS, VARIABLES) describe what
columns each source table has and what aggregations we want on each
canonical variable. A generator function walks those constants and produces
the SQL, either as a raw SELECT (for Python/DuckDB consumers) or wrapped in
an INSERT for the Postgres cron scripts.

To add a new output column:
    - add an entry to the appropriate variable in VARIABLES, and
    - make sure each SOURCES entry either maps the variable to a real column
      expression or to None (meaning "source doesn't have this variable;
      emit a NULL instead of a real aggregation").

To add a new source table:
    - add an entry to SOURCES with its column mapping and sampling rate, and
    - add an entry to FILES_TO_RENDER (at the bottom of this file) for the
      cron file(s) you want to produce from it.

Run after any edit:
    python daily_conversion/render_sql.py
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent


# ============================================================================
# SOURCES
# ----------------------------------------------------------------------------
# Per-source metadata. Each key is the canonical "variable" name used
# throughout this file; the value is the SQL expression that gives that
# variable's value in the source table. If the source doesn't have that
# variable, use None — the generator will emit a typed NULL in its place.
#
# `samples_per_day` is used only for the data_availability column.
# ============================================================================

SOURCES = {
    "weather_10sec": {
        "samples_per_day": 8640,
        "columns": {
            "atmospheric_pressure":   "atmospheric_pressure",
            "cs320_irradiance":       "cs320_irradiance",
            "dewpoint_temp":          "dewpoint_temp",
            "dist":                   "dist",
            "humidity":               "humidity",
            "precipdrop":             "precipdrop",
            "precipitation":          "precipitation",
            "solar_flux_density_wm2": "solar_flux_density_wm2",
            "strikes":                "strikes",
            "temperature":            "temperature",
            "uva_radiation":          None,
            "uvb_radiation":          None,
            "vp":                     "vp",
            "wind_speed":             "wind_speed",
            "windspdmax":             "windspdmax",
        },
    },
    "weather_regular": {
        "samples_per_day": 1440,
        "columns": {
            "atmospheric_pressure":   "atmospheric_pressure",
            "cs320_irradiance":       None,
            "dewpoint_temp":          "dewpoint_temp",
            "dist":                   None,
            "humidity":               "humidity",
            "precipdrop":             None,
            "precipitation":          "precipitation",
            "solar_flux_density_wm2": None,
            "strikes":                None,
            "temperature":            "temperature",
            "uva_radiation":          "NULLIF(uvb_radiation2, -1)",
            "uvb_radiation":          "NULLIF(uvb_radiation, -1)",
            "vp":                     None,
            "wind_speed":             "wind_speed",
            "windspdmax":             None,
        },
    },
}


# ============================================================================
# AGGS
# ----------------------------------------------------------------------------
# Aggregation function library. Each entry is a SQL template with a `{col}`
# placeholder for the variable's source expression, plus any extra placeholders
# that the per-variable params dict supplies (e.g. `{val}` for thresholds).
#
# `returns` is the SQL type the aggregation returns — used to choose the right
# NULL cast when a source doesn't have the variable.
# ============================================================================

AGGS = {
    "avg":{"sql": "AVG({col})","returns": "double precision"},
    "max":            {"sql": "MAX({col})",                                 "returns": "double precision"},
    "min":            {"sql": "MIN({col})",                                 "returns": "double precision"},
    "sum":            {"sql": "SUM({col})",                                 "returns": "double precision"},
    "diurnal_range":  {"sql": "MAX({col}) - MIN({col})",                    "returns": "double precision"},
    "count_gt":       {"sql": "COUNT(*) FILTER (WHERE {col} > {val})",      "returns": "integer"},
    "count_ge":       {"sql": "COUNT(*) FILTER (WHERE {col} >= {val})",     "returns": "integer"},
    "count_lt":       {"sql": "COUNT(*) FILTER (WHERE {col} < {val})",      "returns": "integer"},
    "count_le":       {"sql": "COUNT(*) FILTER (WHERE {col} <= {val})",     "returns": "integer"},
    "count_not_null": {"sql": "COUNT({col}) FILTER (WHERE {col} IS NOT NULL)", "returns": "integer"},
    "avg_gt":         {"sql": "AVG({col}) FILTER (WHERE {col} > {val})",    "returns": "double precision"},
}


# ============================================================================
# VARIABLES
# ----------------------------------------------------------------------------
# Canonical variables and the aggregations applied to each, in the exact order
# they should appear as columns in weather_daily.
#
# Each entry is {"name": <variable>, "aggs": [agg_spec, ...]}.
# Each agg_spec is a tuple:
#   (suffix, agg_name)                 - plain aggregation from AGGS
#   (suffix, agg_name, params_dict)    - with template params (e.g. thresholds)
#   (suffix, "custom", custom_dict)    - bespoke SQL, see render_custom() below
#
# Output column name is f"{variable_name}_{suffix}".
#
# A variable entry may also carry:
#   "null_type": "integer" | "double precision"
#       Overrides the NULL cast used when the source doesn't have this
#       variable. Defaults to the agg's own `returns` type. Useful for
#       integer-valued sums like strikes_sum so the NULL is typed correctly.
#
# An agg's params dict may include the reserved meta key:
#   "_skip_sources": ["weather_regular", ...]
#       Forces this specific output column to NULL for the listed sources,
#       even when the source does have the underlying variable. Use when
#       the calculation is meaningful for one source's sample rate but not
#       another's (e.g. intensity_mean on 1-minute data vs 10-second data).
# ============================================================================

VARIABLES = [
    {"name": "atmospheric_pressure", "aggs": [
        ("mean", "avg"),
        ("max",  "max"),
        ("min",  "min"),
    ]},
    {"name": "cs320_irradiance", "aggs": [
        ("mean",         "avg"),
        ("max",          "max"),
        ("min",          "min"),
        ("sum",          "sum"),
        ("count_gt_5",   "count_gt", {"val": 5}),
        ("gt_5_mean",    "avg_gt",   {"val": 5}),
        ("bright_count", "count_gt", {"val": 10}),
    ]},
    {"name": "dewpoint_temp", "aggs": [
        ("min",  "min"),
        ("max",  "max"),
        ("mean", "avg"),
    ]},
    {"name": "dist", "aggs": [
        ("min", "min"),
    ]},
    {"name": "humidity", "aggs": [
        ("mean", "avg"),
        ("min",  "min"),
        ("max",  "max"),
    ]},
    {"name": "precipdrop", "aggs": [
        ("sum", "sum"),
    ]},
    {"name": "precipitation", "aggs": [
        ("sum",            "sum"),
        ("count",          "count_not_null"),
        ("count_gt_0",     "count_gt", {"val": 0}),
        # intensity_mean is only meaningful on dense sampling — NULL it out
        # for weather_regular (1-minute cadence), keep it for weather_10sec.
        ("intensity_mean", "avg",      {"_skip_sources": ["weather_regular"]}),
    ]},
    {"name": "solar_flux_density_wm2", "aggs": [
        ("mean",         "avg"),
        ("max",          "max"),
        ("min",          "min"),
        ("sum",          "sum"),
        ("count_gt_5",   "count_gt", {"val": 5}),
        ("gt_5_mean",    "avg_gt",   {"val": 5}),
        ("bright_count", "count_gt", {"val": 10}),
    ]},
    {"name": "uvb_radiation", "aggs": [
        ("mean",         "avg"),
        ("max",          "max"),
        ("min",          "min"),
        ("sum",          "sum"),
        ("count_gt_5",   "count_gt", {"val": 5}),
        ("gt_5_mean",    "avg_gt",   {"val": 5}),
        ("bright_count", "count_gt", {"val": 10}),
    ]},
    {"name": "uva_radiation", "aggs": [
        ("mean",         "avg"),
        ("max",          "max"),
        ("min",          "min"),
        ("sum",          "sum"),
        ("count_gt_5",   "count_gt", {"val": 5}),
        ("gt_5_mean",    "avg_gt",   {"val": 5}),
        ("bright_count", "count_gt", {"val": 10}),
    ]},
    {"name": "strikes", "null_type": "integer", "aggs": [
        ("sum", "sum"),
    ]},
    {"name": "temperature", "aggs": [
        ("min",            "min"),
        ("max",            "max"),
        ("mean",           "avg"),
        ("diurnal_range",  "diurnal_range"),
        ("count_below_0",  "count_lt", {"val": 0}),
        ("count_below_5",  "count_lt", {"val": 5}),
        ("count_above_30", "count_gt", {"val": 30}),
        ("count_above_35", "count_gt", {"val": 35}),
        ("count_above_40", "count_gt", {"val": 40}),
    ]},
    {"name": "wind_speed", "aggs": [
        ("min",  "min"),
        # wind_speed_max is bespoke: 10sec data also has a per-sample windspdmax
        # column (the max observed during that 10-second window), so we take
        # the larger of MAX(wind_speed) and MAX(windspdmax). weather_regular
        # has no windspdmax column, so the generator falls back to plain
        # MAX(wind_speed) automatically.
        ("max",  "custom", {
            "sql":      "GREATEST(MAX({col}), MAX({windspdmax}))",
            "returns":  "double precision",
            "requires": ["windspdmax"],
            "fallback": "MAX({col})",
        }),
        ("mean",           "avg"),
        ("count_gt_14",     "count_gt", {"val": 14}),
        ("count_gt_21",     "count_gt", {"val": 21}),
    ]},
    {"name": "vp", "aggs": [
        ("mean",          "avg"),
        ("min",           "min"),
        ("max",           "max"),
        ("diurnal_range", "diurnal_range"),
    ]},
]


# ============================================================================
# Generator
# ============================================================================


def render_standard(agg_name: str, col_sql: str | None, params: dict) -> str:
    """Render a standard AGGS entry for one variable on one source."""
    agg = AGGS[agg_name]
    if col_sql is None:
        return f"NULL::{agg['returns']}"
    return agg["sql"].format(col=col_sql, **params)


def render_custom(custom: dict, col_sql: str | None, source_cols: dict) -> str:
    """
    Render a bespoke per-variable aggregation.

    `custom` is a dict of:
      sql       - template with {col} plus any extra column placeholders
      returns   - SQL type for NULL fallback
      requires  - list of other variable names whose source column
                  expressions must be substituted into the template
      fallback  - optional template used if any `requires` variable is
                  missing in the current source (still has {col} access)
    """
    returns = custom["returns"]
    if col_sql is None:
        return f"NULL::{returns}"

    # Look up each required extra variable's source expression. If any are
    # missing, we can't use the primary template — degrade to the fallback.
    extras: dict[str, str] = {}
    missing_extra = False
    for extra_name in custom.get("requires", []):
        extra_sql = source_cols.get(extra_name)
        if extra_sql is None:
            missing_extra = True
            break
        extras[extra_name] = extra_sql

    if missing_extra:
        fallback = custom.get("fallback")
        if fallback is None:
            return f"NULL::{returns}"
        return fallback.format(col=col_sql)

    return custom["sql"].format(col=col_sql, **extras)


def generate_output_columns(source_name: str) -> list[tuple[str, str]]:
    """
    Walk VARIABLES and produce the ordered list of (column_name, sql_expr)
    pairs for one source table. Includes the leading `date` column and the
    trailing `valid_count` / `data_availability` columns.
    """
    source = SOURCES[source_name]
    source_cols = source["columns"]
    samples_per_day = source["samples_per_day"]

    pairs: list[tuple[str, str]] = []

    # The date grouping key is always first and identical across sources.
    pairs.append(("date", "timestamp::date"))

    for variable in VARIABLES:
        var_name = variable["name"]
        col_sql = source_cols.get(var_name)
        # Optional per-variable override for the NULL cast, used when the
        # source doesn't have this variable and we want something other than
        # the agg's default return type (e.g. integer for strikes_sum).
        null_type_override = variable.get("null_type")

        for agg_spec in variable["aggs"]:
            suffix = agg_spec[0]
            agg_name = agg_spec[1]
            raw_params = agg_spec[2] if len(agg_spec) > 2 else {}
            output_name = f"{var_name}_{suffix}"

            # Split meta keys (starting with _) from the real template params.
            skip_sources = raw_params.get("_skip_sources")
            params = {k: v for k, v in raw_params.items() if not k.startswith("_")}

            # Per-agg source skip: force NULL for listed sources even if the
            # underlying variable exists there.
            if skip_sources and source_name in skip_sources:
                null_type = null_type_override or AGGS[agg_name]["returns"]
                pairs.append((output_name, f"NULL::{null_type}"))
                continue

            if agg_name == "custom":
                expr = render_custom(params, col_sql, source_cols)
            else:
                expr = render_standard(agg_name, col_sql, params)

            # Apply the variable-level null_type override if we ended up with
            # a NULL cast (i.e. the source didn't have this variable).
            if col_sql is None and null_type_override:
                expr = f"NULL::{null_type_override}"

            pairs.append((output_name, expr))

    # Always-present trailers.
    pairs.append(("valid_count", "COUNT(*)"))
    pairs.append(
        ("data_availability", f"COUNT(*)::double precision / {samples_per_day}")
    )

    return pairs


def build_aggregation_sql(
    source_name: str,
    table_name: str | None = None,
    where_clause: str | None = None,
) -> str:
    """
    Build the full aggregation SELECT for a source — no INSERT wrapper.

    This is the public API that Python/DuckDB consumers (e.g. weather-api-py)
    use to run the aggregation over an in-memory DataFrame registered on a
    DuckDB connection.

    Args:
        source_name: key into SOURCES (e.g. "weather_10sec").
        table_name: FROM target. Defaults to source_name. Pass the registered
            DuckDB view/table name when running against a DataFrame.
        where_clause: raw SQL fragment for the row filter. None means no
            WHERE clause (aggregate everything in the table).

    SECURITY NOTE: `where_clause` is interpolated verbatim into the SQL.
    Do not build it from untrusted user input without sanitising first.
    """
    pairs = generate_output_columns(source_name)
    select_lines = [f"    {expr} AS {name}" for name, expr in pairs]
    select_body = ",\n".join(select_lines)

    parts = [
        "SELECT",
        select_body,
        f"FROM {table_name or source_name}",
    ]
    if where_clause:
        parts.append(f"WHERE {where_clause}")
    parts.append("GROUP BY timestamp::date")

    return "\n".join(parts)


def build_insert_sql(source_name: str, where_clause: str | None) -> str:
    """
    Wrap build_aggregation_sql with the INSERT ... ON CONFLICT DO NOTHING
    boilerplate used by the Postgres cron scripts.
    """
    pairs = generate_output_columns(source_name)
    col_block = ",\n    ".join(name for name, _ in pairs)
    select_sql = build_aggregation_sql(source_name, where_clause=where_clause)
    return (
        f"INSERT INTO weather_daily (\n    {col_block}\n)\n"
        f"{select_sql}\n"
        f"ON CONFLICT (date) DO NOTHING;"
    )


# ============================================================================
# Cron file outputs
# ============================================================================

AUTOGEN_BANNER = (
    "-- !!! AUTOGENERATED by daily_conversion/render_sql.py !!!\n"
    "-- Do not edit this file directly. Edit the config at the top of\n"
    "-- render_sql.py (SOURCES / AGGS / VARIABLES) and re-run:\n"
    "--     python daily_conversion/render_sql.py\n"
)

FILE_02_HEADER = (
    "-- 02_backfill_from_weather_regular.sql\n"
    "-- Backfill: aggregates every day in weather_regular and appends to\n"
    "-- weather_daily. Many columns come out NULL because weather_regular\n"
    "-- doesn't record them (cs320_irradiance, solar flux, strikes, etc.).\n"
    "--\n"
    f"{AUTOGEN_BANNER}"
)

FILE_03_HEADER = (
    "-- 03_backfill_from_weather_10sec.sql\n"
    "-- Backfill: aggregates ALL complete days from weather_10sec\n"
    "-- (timestamp < CURRENT_DATE) and appends to weather_daily. Not a cron job.\n"
    "--\n"
    f"{AUTOGEN_BANNER}"
)

FILE_04_HEADER = (
    "-- 04_daily_cron_yesterday_weather_10sec.sql\n"
    "--\n"
    "-- Purpose:\n"
    "--   Cron job: run once per day shortly after midnight (e.g. 00:05).\n"
    "--   Aggregates YESTERDAY from weather_10sec and appends one row into weather_daily.\n"
    "--   Safe to rerun: ON CONFLICT (date) DO NOTHING prevents duplicates.\n"
    "--\n"
    "-- Install as cron (runs daily at 00:05):\n"
    "--   crontab -e\n"
    "--   5 0 * * * psql -h localhost -U weather_stats -d weather -f /FULL/PATH/TO/04_daily_cron_yesterday_weather_10sec.sql\n"
    "--\n"
    f"{AUTOGEN_BANNER}"
)

def build_sql_ds():
    pairs = []
    col_block = ''
    for variable in VARIABLES:
        var_name = variable["name"]
        for agg_spec in variable["aggs"]:
            suffix = agg_spec[0]
            agg_name = agg_spec[1]
            output_name = f"{var_name}_{suffix}"
            # print(agg_name)
            if agg_name == "custom":
                dtype = agg_spec[2]["returns"]
            else:
                dtype = AGGS[agg_name]['returns']
            pair = '  '.join([output_name, dtype])
            col_block = "\n    ".join([col_block, pair]) + ','
        col_block = col_block + '\n'
            # pairs.append(pair)
            # print(pairs)
    
    pairs.extend(['valid_count integer','data_availability double precision'])

    # col_block = ",\n    ".join(pairs)


    sql_str = (
        f"CREATE TABLE weather_daily (\n"
        "    date date PRIMARY KEY,\n"
        f"    {col_block}\n);"
    )
    print(sql_str)
    return sql_str

FILES_TO_RENDER = {
    "02_backfill_from_weather_regular.sql": {
        "source": "weather_regular",
        "where_clause": None,
        "header": FILE_02_HEADER,
    },
    "03_backfill_from_weather_10sec.sql": {
        "source": "weather_10sec",
        "where_clause": "timestamp < CURRENT_DATE",
        "header": FILE_03_HEADER,
    },
    "04_daily_cron_yesterday_weather_10sec.sql": {
        "source": "weather_10sec",
        "where_clause": (
            "timestamp >= CURRENT_DATE - INTERVAL '1 day'\n"
            "  AND timestamp <  CURRENT_DATE"
        ),
        "header": FILE_04_HEADER,
    },
}



def main() -> None:
    content = build_sql_ds()
    init_filename = "01_create_weather_daily_table.sql"
    print(f'Building {init_filename}')
    (HERE / init_filename).write_text(content)

    for filename, cfg in FILES_TO_RENDER.items():
        body = build_insert_sql(cfg["source"], cfg["where_clause"])
        content = f"{cfg['header']}\n{body}\n"
        (HERE / filename).write_text(content)
        print(f"wrote {filename}")


if __name__ == "__main__":
    main()
