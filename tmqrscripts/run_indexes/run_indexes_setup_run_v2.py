from tmqrscripts.run_indexes.run_indexes_v1 import IndexGenerationScript
from datetime import datetime

import argparse

def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)

parser = argparse.ArgumentParser()
parser.add_argument("-i",
                    "--instrument",
                    help="an instrument you want to backfill",
                    required=False,
                    type=str)
parser.add_argument("-e",
                    "--date_end",
                    help="The End Date - format YYYY-MM-DD",
                    required=False,
                    type=valid_date)
parser.add_argument("-a",
                    "--alphas",
                    help="Force alphas to run",
                    required=False,
                    type=bool)
parser.add_argument("-x",
                    "--try_run_all_exos_live_and_test",
                    help="Try to run all exos live and test",
                    required=False,
                    type=bool)
parser.add_argument("-r",
                    "--reset_exo_from_beginning",
                    help="Reset exos from beginning",
                    required=False,
                    type=bool)
parser.add_argument("-o",
                    "--override_time_check_run_exo",
                    help="Over",
                    required=False,
                    type=bool)

args = parser.parse_args()

indexGenerationScript = IndexGenerationScript(
    override_time_check_run_exo = args.override_time_check_run_exo,
    reset_exo_from_beginning=args.reset_exo_from_beginning,
    date_end=args.date_end, override_run_alpha=args.alphas, try_run_all_exos_live_and_test=args.try_run_all_exos_live_and_test, instrument=args.instrument)

indexGenerationScript.run_main_index_alpha_script()








