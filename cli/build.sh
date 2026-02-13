#!/usr/bin/env bash
# exit on error
set -o errexit

pip install --upgrade pip setuptools wheel
pip install --no-build-isolation -r requirements.txt