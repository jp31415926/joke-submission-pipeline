#!/usr/bin/bash

rm -vrf .pytest_cache
rm -vrf `find . -path "./.venv" -prune -o -name "__pycache__" -print`
rm -vf `find . -path "./.venv" -prune -o -name "*~" -print`
