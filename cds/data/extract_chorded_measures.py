import itertools
import os
import pathlib

import pandas as pd
from music21 import *
from tqdm import tqdm

from chord_diagrams import (
    chord_position_str,
    get_diagram_collection,
    get_id2name,
)
from parserGP import ParserGP
from tab_functions import *

PATH_TO_DATA = "/home/alexandre/PhD/data/"

gpifDir = PATH_TO_DATA + "DadaGP8-gpif/"
gpif_files_path = PATH_TO_DATA + "DadaGP8-gpif/"
csv_path = PATH_TO_DATA + "DadaGP-chordcsvTEST/"

# Create directory if it doesn't exist
pathlib.Path(csv_path).mkdir(parents=True, exist_ok=True)


def get_chords_and_positions(measure, collection=None, id2name=None):
    chord_pos_tuples = []
    chord_shapes = []
    for voice in measure.getElementsByClass(stream.Voice):
        elements = list(
            itertools.chain(
                voice.getElementsByClass(note.Note),
                voice.getElementsByClass(note.Rest),
                voice.getElementsByClass(chord.Chord),
            )
        )
        elements.sort(key=lambda x: x.offset)
        for n in elements:
            if len(n.lyrics) > 0:
                for l in n.lyrics:
                    if l.text.startswith("chordid:"):
                        chord_id = l.text.replace("chordid:", "")
                        chord_label = id2name[chord_id]
                        if collection is not None:
                            if chord_id in collection.keys():
                                chord_shape = chord_position_str(
                                    collection[chord_id]
                                )
                            else:
                                chord_shape = None
                        chord_positions = n.offset
                        chord_pos_tuples.append((chord_positions, chord_label))
                        chord_shapes.append(chord_shape)
    if not chord_pos_tuples:
        return [], [], []
    positions = list(zip(*chord_pos_tuples))[0]
    chords = list(zip(*chord_pos_tuples))[1]
    assert len(chords) == len(
        positions
    ), "Erreur : chords and positions should be the same length"
    assert len(chords) == len(
        chord_shapes
    ), "Erreur : chords and positions should be the same length"
    return list(chords), list(positions), chord_shapes


df = pd.DataFrame(
    columns=["File", "Measure", "Duration", "Chords", "Offsets", "Shapes"]
)
i = 0
for file_name in tqdm(sorted(os.listdir(path=gpifDir)), total=84000):
    # df = pd.DataFrame(columns = ['File','Measure','Duration','Chords','Offsets', 'Shapes'])
    subdf_path = pathlib.Path(csv_path + file_name.replace(".gpif", ".csv"))
    if subdf_path.exists():
        subdf = pd.read_csv(subdf_path, index_col=0)
        df = pd.concat([df, subdf])
        continue
    if file_name.endswith(".gpif"):
        gpif_path = gpif_files_path + file_name
        try:
            collection = get_diagram_collection(gpif_path)
            id2name = get_id2name(gpif_path)
            if len(collection) == 0:
                continue
        except IndexError:
            # probably not a six string guitar or bad encoding
            continue
        try:
            s = ParserGP().parseFile(gpif_path)
        except FileNotFoundError:
            continue
        except TypeError:
            continue
        part_number = len(s.getElementsByClass(stream.Part))
        assert part_number == 1, "There should be one part only"
        part = s.getElementsByClass(stream.Part)[0]
        measure_number = len(part.getElementsByClass(stream.Measure))
        print(file_name + " : {} measures".format(measure_number))
        measure_index = 0
        for measure in part.getElementsByClass(stream.Measure):
            chords, positions, shapes = get_chords_and_positions(
                measure, collection, id2name
            )
            df.loc[len(df)] = [
                file_name,
                measure_index,
                measure.duration.quarterLength,
                chords,
                positions,
                shapes,
            ]
            measure_index += 1
    subdf = df[df["File"] == file_name]
    subdf.to_csv(subdf_path)

df.to_csv("dadaGP_chords.csv")
