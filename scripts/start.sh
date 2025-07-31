#!/bin/bash

cd ~/projects/cs-api
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 10443
