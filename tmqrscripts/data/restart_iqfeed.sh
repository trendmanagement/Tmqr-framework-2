#!/usr/bin/env bash

# Create file which send signal to the run_iqfeed_updates.py to stop working
touch /tmp/stop_iqfeed.ctrl

# After stop the script run_iqfeed_updates.py will be restarted by the supervisor