'''
Futures data updates script, all futures contracts
'''
#import os, sys, inspect

# realpath() will make your script run, even if you symlink it :)
# cmd_folder = os.path.realpath(os.path.abspath(os.path.split(inspect.getfile(inspect.currentframe()))[0]))
# if cmd_folder not in sys.path:
#     sys.path.insert(0, cmd_folder)
#
# # Use this if you want to include modules from a subfolder
# cmd_subfolder = os.path.realpath(
#     os.path.abspath(os.path.join(os.path.split(inspect.getfile(inspect.currentframe()))[0], "subfolder")))
# if cmd_subfolder not in sys.path:
#     sys.path.insert(0, cmd_subfolder)

from tmqrscripts.import_options_data import *

run_all_options()
