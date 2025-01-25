#!/bin/bash
set -e
python3 -m pip install --upgrade pip
python3 -m gunicorn main:app -c gunicorn.conf.py