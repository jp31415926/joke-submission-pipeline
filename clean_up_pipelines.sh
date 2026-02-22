#!/usr/bin/bash

find ./pipeline-main -type f -print -delete
find ./pipeline-priority -type f -print -delete
rm -vf logs/*.log