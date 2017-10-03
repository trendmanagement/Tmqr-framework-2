from tmqrscripts.run_indexes.run_indexes import IndexGenerationScript

# x = IndexGenerationScript(reset_from_beginning=True)
# x.run_main_index_alpha_script()

import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--instrument", help="an instrument you want to backfill", type=str)
args = parser.parse_args()

if args.instrument is None:
    indexGenerationScript = IndexGenerationScript(reset_from_beginning=True)
    indexGenerationScript.run_all_instruments()
else:
    indexGenerationScript = IndexGenerationScript(reset_from_beginning=True)
    indexGenerationScript.run_selected_intruments(args.instrument)

