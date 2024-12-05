#!/bin/bash

#-E: ignore PYTHONPATH
python3.12 -E -u mobo_wrapper.py -c optimize.config -d parameters.config
