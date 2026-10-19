#!/usr/bin/env bash

set -e

source ./.venv/bin/activate
flask --app flaskr run --debug -p 8080
