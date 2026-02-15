#!/usr/bin/bash

rm -vrf __pycache__ .pytest_cache data tests/__pycache__ parsers/__pycache__ jokes/*
rm -vf `find . -path "./.venv" -prune -o -name "*~" -print`
