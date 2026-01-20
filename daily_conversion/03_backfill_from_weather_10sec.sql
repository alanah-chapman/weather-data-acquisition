-- 03_backfill_from_weather_10sec_existing.sql
-- Backfill: aggregates ALL complete days from weather_10sec (timestamp < CURRENT_DATE)
-- and appends to weather_daily. Not a cron job.

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
    WHERE timestamp < CURRENT_DATE
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
    AVG(cs320_irradiance) FILTER (WHERE cs320_irradiance > 5) AS cs320_irradiance_gt_5_mean,
    COUNT(*) FILTER (WHERE cs320_irradiance > 10) AS cs320_irradiance_bright_count,

    MIN(dewpoint_temp) AS dewpoint_temp_min,
    MAX(dewpoint_temp) AS dewpoint_temp_max,
    AVG(dewpoint_temp) AS dewpoint_temp_mean,

    MIN(dist) AS dist_min,

    AVG(humidity) AS humidity_mean,
    MIN(humidity) AS humidity_min,
    MAX(humidity) AS humidity_max,

    SUM(precipdrop) AS precipdrop_sum,
    SUM(precipitation) AS precipitation_sum,
    COUNT(precipitation) FILTER (WHERE precipitation IS NOT NULL) AS precipitation_count,
    COUNT(*) FILTER (WHERE precipitation > 0) AS precipitation_count_gt_0,
    AVG(precipitation) AS precipitation_intensity_mean,
    MAX(precip_sum_10min) AS precipitation_max_10min_intensity,

    AVG(solar_flux_density_wm2) AS solar_flux_density_wm2_mean,
    MAX(solar_flux_density_wm2) AS solar_flux_density_wm2_max,
    MIN(solar_flux_density_wm2) AS solar_flux_density_wm2_min,
    SUM(solar_flux_density_wm2) AS solar_flux_density_wm2_sum,
    COUNT(*) FILTER (WHERE solar_flux_density_wm2 > 5) AS solar_flux_density_wm2_count_gt_5,
    AVG(solar_flux_density_wm2) FILTER (WHERE solar_flux_density_wm2 > 5) AS solar_flux_density_wm2_gt_5_mean,
    COUNT(*) FILTER (WHERE solar_flux_density_wm2 > 10) AS solar_flux_density_wm2_bright_count,

    NULL::double precision AS uvb_radiation_mean,
    NULL::double precision AS uvb_radiation_max,
    NULL::double precision AS uvb_radiation_min,
    NULL::double precision AS uvb_radiation_sum,
    NULL::integer          AS uvb_radiation_count_gt_5,
    NULL::double precision AS uvb_radiation_gt_5_mean,
    NULL::integer          AS uvb_radiation_bright_count,

    NULL::double precision AS uva_radiation_mean,
    NULL::double precision AS uva_radiation_max,
    NULL::double precision AS uva_radiation_min,
    NULL::double precision AS uva_radiation_sum,
    NULL::integer          AS uva_radiation_count_gt_5,
    NULL::double precision AS uva_radiation_gt_5_mean,
    NULL::integer          AS uva_radiation_bright_count,

    SUM(strikes) AS strikes_sum,

    MIN(temperature) AS temperature_min,
    MAX(temperature) AS temperature_max,
    AVG(temperature) AS temperature_mean,
    MAX(temperature) - MIN(temperature) AS temperature_diurnal_range,
    COUNT(*) FILTER (WHERE temperature < 0) AS temperature_count_below_0,
    COUNT(*) FILTER (WHERE temperature < 5) AS temperature_count_below_5,
    COUNT(*) FILTER (WHERE temperature > 30) AS temperature_count_above_30,
    COUNT(*) FILTER (WHERE temperature > 35) AS temperature_count_above_35,
    COUNT(*) FILTER (WHERE temperature > 40) AS temperature_count_above_40,

    MIN(wind_speed) AS wind_speed_min,
    GREATEST(MAX(wind_speed), MAX(windspdmax)) AS wind_speed_max,
    AVG(wind_speed) AS wind_speed_mean,
    COUNT(*) FILTER (WHERE wind_speed <= 0.5) AS wind_speed_count_less_0p5,
    COUNT(*) FILTER (WHERE wind_speed > 2) AS wind_speed_count_gt_2,
    COUNT(*) FILTER (WHERE wind_speed > 8) AS wind_speed_count_gt_8,

    MOD(
        (
            DEGREES(ATAN2(
                AVG(SIN(RADIANS(wind_direction))),
                AVG(COS(RADIANS(wind_direction)))
            )) + 360
        )::numeric,
        360::numeric
    )::double precision AS wind_direction_mean,

    AVG(vp) AS vp_mean,
    MIN(vp) AS vp_min,
    MAX(vp) AS vp_max,
    MAX(vp) - MIN(vp) AS vp_diurnal_range,

    COUNT(*) AS valid_count,
    COUNT(*)::double precision / 8640 AS data_availability
FROM enriched
GROUP BY date
ON CONFLICT (date) DO NOTHING;
