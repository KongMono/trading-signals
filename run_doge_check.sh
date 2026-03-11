#!/bin/bash

# Navigate to the script directory
cd /Users/kong_mono/trading_signals

# Add a timestamp to the log
echo "--- Check performed on $(date) ---" >> signals.log

# Run the python script and append output to the log
# Using the full path to python3 to ensure it runs correctly in cron
/usr/bin/python3 trading_signals.py >> signals.log 2>&1

# Add a separator for readability
echo "-------------------------------------------" >> signals.log
echo "" >> signals.log
