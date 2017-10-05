from tmqrscripts.run_indexes.run_indexes import IndexGenerationScript
from datetime import datetime
# x = IndexGenerationScript(override_run=True)
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

args = parser.parse_args()

if args.instrument is None:
    indexGenerationScript = IndexGenerationScript(override_run=True, date_end=args.date_end)
    indexGenerationScript.run_all_instruments()
else:
    indexGenerationScript = IndexGenerationScript(override_run=True, date_end=args.date_end)
    indexGenerationScript.run_selected_intruments(args.instrument)








