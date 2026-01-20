-- 04_daily_cron_yesterday_weather_10sec.sql
--
-- Purpose:
--   Cron job: run once per day shortly after midnight (e.g. 00:05).
--   Aggregates YESTERDAY from weather_10sec and appends one row into weather_daily.
--   Safe to rerun: ON CONFLICT (date) DO NOTHING prevents duplicates.
--
-- Run manually:
--   psql -h localhost -U weather_stats -d weather -f 04_daily_cron_yesterday_weather_10sec.sql
--
-- Install as cron (runs daily at 00:05):
--   crontab -e
--   5 0 * * * psql -h localhost -U weather_stats -d weather -f /FULL/PATH/TO/04_daily_cron_yesterday_weather_10sec.sql
--
-- Confirm cron installed:
--   crontab -l

WITH base AS (
    SELECT
        timestamp::date AS date,
        timestamp,
        precipitation,
        precipdrop,
        strikes,
        dist,
        wind_speed,
        windspdmax,
        wind_direction,
        temperature,
        vp,
        atmospheric_pressure,
        humidity,
        dewpoint_temp,
        solar_flux_density_wm2,
        cs320_irradiance
    FROM weather_10sec
    WHERE timestamp >= CURRENT_DATE - INTERVAL '1 day'
      AND timestamp <  CURRENT_DATE
),
enriched AS (
    SELECT
        date,
        timestamp,
        precipitation,
        precipdrop,
        strikes,
        dist,
        wind_speed,
        windspdmax,
        wind_direction,
        temperature,
        vp,
        atmospheric_pressure,
        humidity,
        dewpoint_temp,
        solar_flux_density_wm2,
        cs320_irradiance,
        SUM(precipitation) OVER (
            PARTITION BY date
            ORDER BY timestamp
            RANGE BETWEEN INTERVAL '10 minutes' PRECEDING AND CURRENT ROW
        ) AS precip_sum_10min
    FROM base
)
INSERT INTO weather_daily (
    date,

    atmospheric_pressure_mean,
    atmospheric_pressure_max,
    atmospheric_pressure_min,

    cs320_irradiance_mean,
    cs320_irradiance_max,
    cs320_irradiance_min,
    cs320_irradiance_sum,
    cs320_irradiance_count_gt_5,
    cs320_irradiance_gt_5_mean,
    cs320_irradiance_bright_count,

    dewpoint_temp_min,
    dewpoint_temp_max,
    dewpoint_temp_mean,

    dist_min,

    humidity_mean,
    humidity_min,
    humidity_max,

    precipdrop_sum,
    precipitation_sum,
    precipitation_count,
    precipitation_count_gt_0,
    precipitation_intensity_mean,
    precipitation_max_10min_intensity,

    solar_flux_density_wm2_mean,
    solar_flux_density_wm2_max,
    solar_flux_density_wm2_min,
    solar_flux_density_wm2_sum,
    solar_flux_density_wm2_count_gt_5,
    solar_flux_density_wm2_gt_5_mean,
    solar_flux_density_wm2_bright_count,

    uvb_radiation_mean,
    uvb_radiation_max,
    uvb_radiation_min,
    uvb_radiation_sum,
    uvb_radiation_count_gt_5,
    uvb_radiation_gt_5_mean,
    uvb_radiation_bright_count,

    uva_radiation_mean,
    uva_radiation_max,
    uva_radiation_min,
    uva_radiation_sum,
    uva_radiation_count_gt_5,
    uva_radiation_gt_5_mean,
    uva_radiation_bright_count,

    strikes_sum,

    temperature_min,
    temperature_max,
    temperature_mean,
    temperature_diurnal_range,
    temperature_count_below_0,
    temperature_count_below_5,
    temperature_count_above_30,
    temperature_count_above_35,
    temperature_count_above_40,

    wind_speed_min,
    wind_speed_max,
    wind_speed_mean,
    wind_speed_count_less_0p5,
    wind_speed_count_gt_2,
    wind_speed_count_gt_8,
    wind_direction_mean,

    vp_mean,
    vp_min,
    vp_max,
    vp_diurnal_range,

    valid_count,
    data_availability
)
SELECT
    date,

    AVG(atmospheric_pressure) AS atmospheric_pressure_mean,
    MAX(atmospheric_pressure) AS atmospheric_pressure_max,
    MIN(atmospheric_pressure) AS atmospheric_pressure_min,

    AVG(cs320_irradiance) AS cs320_irradiance_mean,
    MAX(cs320_irradiance) AS cs320_irradiance_max,
    MIN(cs320_irradiance) AS cs320_irradiance_min,
    SUM(cs320_irradiance) AS cs320_irradiance_sum,
    COUNT(*) FILTER (WHERE cs320_irradiance > 5) AS cs320_irradiance_count_gt_5,
    AVG(cs320_irradiance) FILTER (WHERE cs320_irra
