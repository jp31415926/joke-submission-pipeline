#!/usr/bin/bash

STOP_FILE=./ALL_STOP
SLEEP_DELAY=20

run_script() {
    while [ ! -f $STOP_FILE ]; do
        ./joke-pipeline.py --stage $1
        # Integer-only math: (Base * (80% + 0-40%)) / 100
        sleep $(( SLEEP_DELAY * (800 + RANDOM % 401) / 1000 ))
    done
}

# Clean up any old stop file
rm -f $STOP_FILE

run_script incoming &
run_script parsed &
run_script deduped &
run_script clean_checked &
run_script formatted &
run_script categorized &
