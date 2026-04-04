#!/usr/bin/bash

STOP_FILE=./ALL_STOP
SLEEP_DELAY=5
VERBOSE=--verbose

run_script() {
    while [ ! -f $STOP_FILE ]; do
        ./joke-pipeline.py --stage $1 $VERBOSE
        # Integer-only math: (Base * (80% + 0-40%)) / 100
        sleep $(( SLEEP_DELAY * (800 + RANDOM % 401) / 1000 ))
    done
}

# Clean up any old stop file
rm -f $STOP_FILE

run_script parse &
run_script dedup &
run_script clean_check &
run_script format &
run_script categorize &
run_script title &
