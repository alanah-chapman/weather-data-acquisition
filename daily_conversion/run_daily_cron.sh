#!/usr/bin/env bash
export PGPASSWORD='E@rthSc1'
psql -h localhost -U weather_stats -d weather -f /srv/shared/weather-data-acquisition/daily_conversion/04_daily_cron_yesterday_weather_10sec.sql

