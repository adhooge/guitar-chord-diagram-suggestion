from argparse import ArgumentParser
from collections import defaultdict
import sys
import pathlib
import pandas as pd
import cds.model.losses as L
import cds.config as C
from statistics import mean, stdev

def main(parser: ArgumentParser) -> int:
    args = parser.parse_args()
    SOURCEPATH = pathlib.Path(args.sourcepath)
    if SOURCEPATH.is_dir():
        test_sets = list(SOURCEPATH.glob('*.csv'))
    else:
        test_sets = [SOURCEPATH]
    results = defaultdict(list)
    for test_set in test_sets:
        df = pd.read_csv(test_set, index_col=0)
        if args.strict:
            df = df.drop_duplicates(subset=['filename', 'next_chord', 'next_position'])
        elif args.stricter:
            df = df.drop_duplicates(subset=['next_chord', 'next_position'])
        if args.strictest:
            df = df.drop_duplicates(subset=['next_chord'])
        if args.anatomical_score:
            anatomical_score = 0
        if args.transition_cost:
            transition_cost = 0
        if args.unplayable:
            unplayable = 0
        if args.texture:
            texture = {
                    'ratio_muted_strings': 0,
                    'ratio_muted_strings_diff': 0,
                    'ratio_open_strings': 0,
                    'ratio_open_strings_diff': 0,
                    'num_strings_played': 0,
                    'num_strings_played_diff': 0,
                    'string_centroid': 0,
                    'string_centroid_diff': 0,
                    'ratio_unique_notes': 0,
                    'ratio_unique_notes_diff': 0,
                    }
        for i, row in df.iterrows():
            score, fingering = L.anatomical_score(row['next_position'])
            if args.anatomical_score:
                anatomical_score += score
            if args.unplayable:
                if score < C.PLAYABILITY_THRESHOLD:
                    if args.verbose:
                        print(f"Chord {row['next_chord']} in pos {row['next_position']} is unplayable.")
                    unplayable += 1
            if args.transition_cost:
                _, prev_fingering = L.anatomical_score(row['current_position'])
                transition_cost += L.transition_cost(prev_fingering, fingering,
                                                     theta1=C.THETA1, theta2=C.THETA2)
            if args.texture:
                current_diag = row['current_position']
                next_diag = row['next_position']
                c_r_muted = L.ratio_muted_strings(current_diag)
                c_r_open = L.ratio_open_strings(current_diag)
                c_num_strings = L.num_strings_played(current_diag)
                c_centroid = L.string_centroid(current_diag)
                c_r_unique = L.ratio_unique_notes(current_diag)
                n_r_muted = L.ratio_muted_strings(next_diag)
                n_r_open = L.ratio_open_strings(next_diag)
                n_num_strings = L.num_strings_played(next_diag)
                n_centroid = L.string_centroid(next_diag)
                n_r_unique = L.ratio_unique_notes(next_diag)
                texture['ratio_muted_strings'] += n_r_muted
                texture['ratio_open_strings'] += n_r_open
                texture['num_strings_played'] += n_num_strings
                texture['string_centroid'] += n_centroid
                texture['ratio_unique_notes'] += n_r_unique
                texture['ratio_muted_strings_diff'] += abs(n_r_muted - c_r_muted)
                texture['ratio_open_strings_diff'] += abs(n_r_open - c_r_open)
                texture['num_strings_played_diff'] += abs(n_num_strings - c_num_strings)
                texture['string_centroid_diff'] += abs(n_centroid - c_centroid)
                texture['ratio_unique_notes_diff'] += abs(n_r_unique - c_r_unique)
        if args.anatomical_score:
            results['anatomical_score'].append(anatomical_score/len(df))
        if args.transition_cost:
            results['transition_cost'].append(transition_cost/len(df))
        if args.unplayable:
            results['unplayable'].append(unplayable/len(df))
        if args.texture:
            for k, v in texture.items():
                results[k].append(v/len(df))

    for k, v in results.items():
        print(f"{k}: {mean(v):.2f} ± {stdev(v):.2f}")
    return 0


if __name__ == '__main__':
    parser = ArgumentParser(description="SOME DESCRIPTION OF THAT SCRIPT")
    parser.add_argument('-s', '--sourcepath', type=str,
            help="Source files for this script.")
    parser.add_argument('-o', '--outpath', type=str,
            help="Path to store results of this script.")
    parser.add_argument('--transition-cost', action='store_true',
            help="Compute transition cost metric on data.")
    parser.add_argument('--anatomical-score', action='store_true',
            help="Compute anatomical score on data.")
    parser.add_argument('--unplayable', action='store_true',
            help="Compute ratio on 'unplayable' diagrams.")
    parser.add_argument('--texture', action='store_true',
            help="Compute a set of texture related metrics.")
    parser.add_argument('--strict', action='store_true',
            help="Drop duplicates from test set on filename, nextchord and nextposition.")
    parser.add_argument('--stricter', action='store_true',
            help="Drop duplicates from test set on nextchord and nextposition.")
    parser.add_argument('--strictest', action='store_true',
            help="Drop duplicates from test set on nextposition.")
    parser.add_argument('-v', '--verbose', action='store_true',
            help="Enable verbose output.")
    sys.exit(main(parser))


