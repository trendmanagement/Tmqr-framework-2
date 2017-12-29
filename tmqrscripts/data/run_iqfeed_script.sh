#!/usr/bin/env bash

# Try gracefully kill iqconnect.exe first
killall iqconnect.exe

# Otherwise try to force kill
killall -9 iqconnect.exe

# Run the script
/home/tmqr_framework2/anaconda3/bin/python /home/tmqr_framework2/tmqr_framework2/tmqrscripts/data/run_iqfeed_updates.py --headless --live_n_futures=6