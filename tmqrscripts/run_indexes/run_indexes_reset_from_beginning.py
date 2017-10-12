from tmqrscripts.run_indexes.run_indexes import IndexGenerationScript
from datetime import datetime
# x = IndexGenerationScript(reset_from_beginning=True)
# x.run_main_index_alpha_script()

import argparse

def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)

parser = argparse.ArgumentParser()
parser.add_argument("-i","--instrument", help="an instrument you want to backfill", type=str)
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

args = parser.parse_args()

if args.instrument is None:
    indexGenerationScript = IndexGenerationScript(reset_exo_from_beginning=True, date_end=args.date_end, override_run_alpha=args.alphas)
    indexGenerationScript.run_all_instruments()
else:
    indexGenerationScript = IndexGenerationScript(reset_exo_from_beginning=True, date_end=args.date_end, override_run_alpha=args.alphas)
    indexGenerationScript.run_selected_intruments(args.instrument)



