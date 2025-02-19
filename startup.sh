#!/bin/bash
source /home/site/wwwroot/antenv/bin/activate
pip install -r /home/site/wwwroot/requirements.txt
gunicorn -w 2 -k uvicorn.workers.UvicornWorker main:app