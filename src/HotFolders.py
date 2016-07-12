#!/usr/bin/env python3
"""
    A script to monitor folders and subdirectories for file movement, creation
    or modification so that files are automatically converted from predefined
    filetypes to target filetypes set by the user.

    Zamzar API keys can be obtained by registering at: https://developers.zamzar.com/pricing
"""

# Imports
import time
import json
from Watch import Watch
import os
import sys

# Load the config file
print("Starting HotFolders.py")
try:
    config_file = open('hotfolders_config.json', 'r')
except FileNotFoundError as err:
    print("ERROR: Could not find JSON config file - ensure current working directory contains hotfolders_config.json")
    sys.exit(0)

# Use json.load to get the data from the config file
try:
    config_info = json.load(config_file)
    api_key = config_info['api_key'][0]
    config_info = config_info["conversions"]
except json.decoder.JSONDecodeError as err:
    print("ERROR: Could not parse 'hotfolders_config.json' - invalid JSON found:")
    print(err)
    sys.exit(0)


"""
    We need to set a watch for each of the directories watched.
    This is achieved using the Watch class written for this project.
    We make a watch object for each path watched. This is necessary as each path will have different options in
    formats and some paths may utilise the auto-extract or subdirectory search functions whilst others might not
"""

# This will hold the watch objects for the paths
watch_list = []

for key in config_info:
    # Check the path exists, if not, skip it with an error message in the log
    if not os.path.exists(key):
        print("ERROR: " + key + " does not exist - cannot monitor\n")
        sys.exit(0)
    else:
        print("Monitoring: " + key)
        # Each key is a directory path.
        watch_list.append(Watch(key, config_info[key]['to'], config_info[key]['from'], config_info[key]['options'],
                            config_info[key]['ignore'], api_key))

# Keep the program running, checking for keyboard input. If input is detected then clean up the Watch objects and end
# the program.
try:
    while True:
        time.sleep(0.5)
except KeyboardInterrupt:
    for w in watch_list:
        del w
    # Upon program termination remake the config file with the new ignore
