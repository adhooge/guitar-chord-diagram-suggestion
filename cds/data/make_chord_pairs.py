import ast
import pathlib
import random
import sys
from argparse import ArgumentParser
from datetime import datetime
from difflib import SequenceMatcher
from typing import List, Tuple

import pandas as pd
from tqdm import tqdm

MATCHER = SequenceMatcher(None, "", "")

OUT_COLUMNS = [
    "filename",
    "measure",
    "current_chord",
    "next_chord",
    "current_position",
    "next_position",
]
CHORDOCC_COLUMNS = ["filename", "measure", "chordname", "position"]
IN_COLUMNS = ["File", "Measure", "Duration", "Chords", "Offsets", "Shapes"]
INPUT_CONVERTERS = {
    "Chords": ast.literal_eval,
    "Offsets": ast.literal_eval,
    "Shapes": ast.literal_eval,
}


def filenames_match(n1: str, n2: str, t: float = 0.8) -> bool:
    n1 = n1.upper()
    n2 = n2.upper()
    n1 = "".join(c for c in n1 if c.isalnum())
    n2 = "".join(c for c in n2 if c.isalnum())
    MATCHER.set_seqs(n1, n2)
    r1 = MATCHER.ratio()
    MATCHER.set_seqs(n2, n1)
    r2 = MATCHER.ratio()
    return (r1 > t) or (r2 > t)


def _is_there_a_position(l: List) -> bool:
    """
    Check if input contains any chord position info.
    """
    if len(l) == 0:
        return False
    else:
        for v in l:
            if v is not None:
                return True
    return False


def _process_single_row(row):
    if len(row["Shapes"]) == 1 or None in row["Shapes"]:
        return None
    else:
        out = []
        for i in range(len(row["Shapes"]) - 1):
            tmp = {}
            tmp["filename"] = row["File"]
            tmp["measure"] = row["Measure"]
            tmp["current_chord"] = row["Chords"][i]
            tmp["next_chord"] = row["Chords"][i + 1]
            tmp["current_position"] = row["Shapes"][i]
            tmp["next_position"] = row["Shapes"][i + 1]
            out.append(tmp)
    return out


def _add_dict_to_df(d: dict, df: pd.DataFrame) -> pd.DataFrame:
    df_dict = pd.DataFrame([d])
    output = pd.concat([df, df_dict], ignore_index=True)
    return output


def _process_two_rows(row, previous_row):
    """
    Both rows should have a chord position.
    We have to check that the measures are consecutive.
    """
    meas = row["Measure"]
    prev_meas = previous_row["Measure"]
    if meas - prev_meas > 1:
        # Should never happen but sanity check
        raise ValueError
    else:
        out = {}
        out["filename"] = row["File"]
        out["measure"] = prev_meas + 0.5
        out["current_chord"] = previous_row["Chords"][-1]
        out["next_chord"] = row["Chords"][0]
        out["current_position"] = previous_row["Shapes"][-1]
        out["next_position"] = row["Shapes"][0]
        if out["current_position"] is None or out["next_position"] is None:
            return None
    return out


def process_subdf(
    subdf: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame] | Tuple[None, None]:
    out = pd.DataFrame(columns=OUT_COLUMNS)
    chord_occ = pd.DataFrame(columns=CHORDOCC_COLUMNS)
    # First check is there is any position information at all
    if not (subdf["Shapes"].apply(_is_there_a_position).any()):
        return None, None
    # Then check only rows that have at least one position
    df = subdf[subdf["Shapes"].apply(_is_there_a_position)]
    for idx, row in df.iterrows():
        res = None
        res = _process_single_row(row)
        if res is not None:
            for r in res:
                out = _add_dict_to_df(r, out)
                dict_chord_occ1 = {
                    "filename": r["filename"],
                    "measure": r["measure"],
                    "chordname": r["current_chord"],
                    "position": r["current_position"],
                }
                dict_chord_occ2 = {
                    "filename": r["filename"],
                    "measure": r["measure"],
                    "chordname": r["next_chord"],
                    "position": r["next_position"],
                }
                chord_occ = pd.concat(
                    [
                        chord_occ,
                        pd.DataFrame([dict_chord_occ1]),
                        pd.DataFrame([dict_chord_occ2]),
                    ],
                    ignore_index=True,
                )
        if idx > 0:
            try:
                previous_row = df.loc[idx - 1]
            except KeyError:
                # Previous row is not there, moving on.
                continue
            res = _process_two_rows(row, previous_row)
            if res is not None:
                out = _add_dict_to_df(res, out)
                dict_chord_occ1 = {
                    "filename": res["filename"],
                    "measure": (
                        res["measure"] - 0.5
                        if int(res["measure"]) != res["measure"]
                        else res["measure"]
                    ),
                    "chordname": res["current_chord"],
                    "position": res["current_position"],
                }
                dict_chord_occ2 = {
                    "filename": res["filename"],
                    "measure": (
                        res["measure"] + 0.5
                        if int(res["measure"]) != res["measure"]
                        else res["measure"]
                    ),
                    "chordname": res["next_chord"],
                    "position": res["next_position"],
                }
                chord_occ = pd.concat(
                    [
                        chord_occ,
                        pd.DataFrame([dict_chord_occ1]),
                        pd.DataFrame([dict_chord_occ2]),
                    ],
                    ignore_index=True,
                )
    return out, chord_occ


def main(parser: ArgumentParser) -> int:
    args = parser.parse_args()
    random.seed(args.random_seed)
    if not args.chordpairs:
        if args.sourcefile:
            df = pd.read_csv(args.sourcefile, index_col=0)
        else:
            df = pd.DataFrame(columns=IN_COLUMNS)
            to_concat = []
            for f in tqdm(pathlib.Path(args.sourcefiles).glob("*.csv")):
                subdf = pd.read_csv(f, index_col=0)
                to_concat.append(subdf)
            df = pd.concat([df] + to_concat, ignore_index=True)
        df["Chords"] = df["Chords"].apply(ast.literal_eval)
        df["Shapes"] = df["Shapes"].apply(ast.literal_eval)
        out_df = pd.DataFrame(columns=OUT_COLUMNS)
        out_chord_occ = pd.DataFrame(columns=CHORDOCC_COLUMNS)
        filenames = df["File"].unique()
        random.shuffle(filenames)
        for file in filenames:
            print(file)
            tmp_df, tmp_chord_occ = process_subdf(df[df["File"] == file])
            if tmp_df is not None:
                out_df = pd.concat([out_df, tmp_df], ignore_index=True)
                out_chord_occ = pd.concat(
                    [out_chord_occ, tmp_chord_occ], ignore_index=True
                )
        out_chord_occ = out_chord_occ.drop_duplicates()
        out_df.to_csv(args.outfile)
        out_chord_occ.to_csv(args.chordocc)
    else:
        out_df = pd.read_csv(args.chordpairs, index_col=0)
        out_chord_occ = pd.read_csv(args.chordocc, index_col=0)
    out_df_unique = out_df.drop_duplicates(
        subset=[
            "filename",
            "current_position",
            "current_chord",
            "next_position",
            "next_chord",
        ]
    )
    outpath = pathlib.Path(args.outfile)
    outpath_occ = pathlib.Path(args.chordocc)
    out_df_unique.to_csv(outpath.with_stem("chord_pairs_unique"))
    # Train/Validation/Test Split
    total_size = len(out_df_unique)
    test_size = total_size * args.test_split
    validation_size = total_size * args.validation_split
    filenames = out_df_unique["filename"].unique()
    filenames = list(filenames)
    random.shuffle(filenames)
    test_df = pd.DataFrame(columns=OUT_COLUMNS)
    val_df = pd.DataFrame(columns=OUT_COLUMNS)
    train_df = pd.DataFrame(columns=OUT_COLUMNS)
    test_occ = pd.DataFrame(columns=CHORDOCC_COLUMNS)
    val_occ = pd.DataFrame(columns=CHORDOCC_COLUMNS)
    train_occ = pd.DataFrame(columns=CHORDOCC_COLUMNS)
    f = 0
    print("Building test set...")
    while len(test_df) < test_size:
        filename = filenames[f]
        if filename in test_df["filename"].values:
            f += 1
            continue
        f_to_add = [filename]
        for f2 in filenames:
            if f2 == filename:
                continue
            if filenames_match(filename, f2):
                f_to_add.append(f2)
        for fn in f_to_add:
            test_df = pd.concat(
                [test_df, out_df_unique[out_df_unique["filename"] == fn]],
                ignore_index=True,
            )
            test_occ = pd.concat(
                [test_occ, out_chord_occ[out_chord_occ["filename"] == fn]],
                ignore_index=True,
            )
        f += 1
    print("Building val set...")
    while len(val_df) < validation_size:
        filename = filenames[f]
        if (
            filename in val_df["filename"].values
            or filename in test_df["filename"].values
        ):
            f += 1
            continue
        f_to_add = [filename]
        for f2 in filenames:
            if f2 == filename or f2 in test_df["filename"].values:
                continue
            if filenames_match(filename, f2):
                f_to_add.append(f2)
        for fn in f_to_add:
            val_df = pd.concat(
                [val_df, out_df_unique[out_df_unique["filename"] == fn]],
                ignore_index=True,
            )
            test_occ = pd.concat(
                [test_occ, out_chord_occ[out_chord_occ["filename"] == fn]],
                ignore_index=True,
            )
        f += 1
    print("Finishing with train set...")
    while f < len(filenames):
        filename = filenames[f]
        if (
            filename in train_df["filename"].values
            or filename in val_df["filename"].values
            or filename in test_df["filename"].values
        ):
            f += 1
            continue
        f_to_add = [filename]
        for f2 in filenames:
            if (
                f2 == filename
                or f2 in test_df["filename"].values
                or f2 in val_df["filename"].values
            ):
                continue
            if filenames_match(filename, f2):
                f_to_add.append(f2)
        for fn in f_to_add:
            train_df = pd.concat(
                [train_df, out_df_unique[out_df_unique["filename"] == fn]],
                ignore_index=True,
            )
            test_occ = pd.concat(
                [test_occ, out_chord_occ[out_chord_occ["filename"] == fn]],
                ignore_index=True,
            )
        f += 1
    # write everything to disk now
    print(f"Total size is {total_size}")
    print(f"Test set has {len(test_df)} samples.")
    print(f"Validation set has {len(val_df)} samples.")
    print(f"Training set has {len(train_df)} samples.")
    print("Checking sets validity")
    for f in test_df["filename"].unique():
        if f in val_df["filename"].values or f in train_df["filename"].values:
            print(f"{f} is also seen in other sets...")
    for f in val_df["filename"].unique():
        if f in train_df["filename"].values:
            print(f"{f} is also seen in train set...")
    test_df.to_csv(outpath.with_stem(args.out_prefix + "test_chordpairs"))
    val_df.to_csv(outpath.with_stem(args.out_prefix + "val_chordpairs"))
    train_df.to_csv(outpath.with_stem(args.out_prefix + "train_chordpairs"))
    test_occ.to_csv(outpath_occ.with_stem(args.out_prefix + "test_chordocc"))
    val_occ.to_csv(outpath_occ.with_stem(args.out_prefix + "val_chordocc"))
    train_occ.to_csv(outpath_occ.with_stem(args.out_prefix + "train_chordocc"))
    return 0


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Take dadaGP_chords.csv file as input and produces a new csv file with pairs of chords following each other, with known positions."
    )
    parser.add_argument(
        "--sourcefile",
        "-s",
        type=str,
        help="Path to the source file with chord info.",
    )
    parser.add_argument(
        "--sourcefiles",
        "-S",
        type=str,
        default="/home/alexandre/PhD/data/DadaGP-chordcsv/",
        help="Path to separate csv files. Useful for huge datasets like DadaGP.",
    )
    parser.add_argument(
        "--chordpairs",
        type=str,
        help="Path to precomputed Chordpairs to avoid computing them again.",
    )
    parser.add_argument(
        "--outfile",
        "-o",
        type=str,
        default="chord_pairs.csv",
        help="Name/path to store the produced file.",
    )
    parser.add_argument(
        "--chordocc",
        "-c",
        type=str,
        default="chord_occurences.csv",
        help="Name/path to store the .csv file of chord occurences.",
    )
    parser.add_argument(
        "--out-prefix",
        type=str,
        default=datetime.today().strftime("%Y-%m-%d-%H_%M_%S"),
        help="prefix to add to output files, to avoid overwritting stuff.",
    )
    parser.add_argument(
        "--validation-split",
        "-V",
        type=float,
        default=0.2,
        help="ratio of the data that should be put aside for validation.",
    )
    parser.add_argument(
        "--test-split",
        "-t",
        type=float,
        default=0.2,
        help="ratio of the data that should be put aside for testing.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=2222,
        help="Random seed for train_test_split",
    )
    sys.exit(main(parser))
