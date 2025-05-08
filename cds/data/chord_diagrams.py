import json
import pathlib
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict

import music21 as m21

FINGERS = {
    "Index": 1,
    "Middle": 2,
    "Ring": 3,
    "Pinky": 4,
    "Thumb": 0,
    "None": None,
    "Unspecified": -1,
}


def get_diagram_collection(file: str, tuning=[40, 45, 50, 55, 59, 64]) -> Dict:
    tree = ET.parse(file)
    root = tree.getroot()
    collection_xml = root.find(
        "./Tracks/Track/Staves/Staff/Properties/Property[@name='DiagramCollection']"
    )
    collection = {}
    for item in collection_xml.findall("Items/Item"):
        try:
            collection[item.get("id")] = get_chord_from_diagram(
                item.find("Diagram"), tuning=tuning
            )
        except ValueError:
            continue
    return collection


def get_id2name(file: str) -> Dict:
    tree = ET.parse(file)
    root = tree.getroot()
    collection_xml = root.find(
        "./Tracks/Track/Staves/Staff/Properties/Property[@name='DiagramCollection']"
    )
    collection = {}
    for item in collection_xml.findall("Items/Item"):
        try:
            collection[item.get("id")] = item.get("name")
        except ValueError:
            continue
    return collection


def get_chord_from_diagram(
    diagram, tuning=[40, 45, 50, 55, 59, 64]
) -> m21.chord.Chord:
    base_fret = diagram.get("baseFret")
    base_fret = int(base_fret) if base_fret is not None else 0
    notes = []
    if len(diagram.findall("Fret")) == 0:
        raise ValueError("Chord is not properly defined.")
    for fret_xml in diagram.findall("Fret"):
        fret = int(fret_xml.get("fret"))
        if fret != 0:
            fret += base_fret
        string = int(fret_xml.get("string"))
        pitch = tuning[string] + fret
        finger = "Unspecified"
        for position in diagram.findall("Fingering/Position"):
            if int(position.get("string")) == string:
                finger = position.get("finger")
        finger = FINGERS[finger]
        string = 6 - string  # convert to usual guitarist numbering
        note = m21.note.Note(pitch)
        note.articulations = [
            m21.articulations.FretIndication(fret),
            m21.articulations.StringIndication(string),
            m21.articulations.Fingering(finger),
        ]
        notes.append(note)
    return m21.chord.Chord(notes)


def chord_position_str(chord: m21.chord.Chord) -> str:
    out = ["x"] * 6
    for note in chord.notes:
        string = 6 - note.string.number
        fret = note.fret.number
        out[string] = str(fret)
    return ".".join(out)


if __name__ == "__main__":
    CORPUS = "/home/alexandre/PhD/data/gpFiles"
    OUTPATH = "/home/alexandre/PhD/imitation_texture/data/"
    path_to_corpus = pathlib.Path(CORPUS)
    outpath = pathlib.Path(OUTPATH)
    chords_in_songs = defaultdict(list)
    chord_positions = defaultdict(set)
    chordbook = {}
    chord_occurences = defaultdict(int)
    chord_id = 0
    for song in path_to_corpus.rglob("**/*.gpif"):
        filename = song.parent.stem
        print(filename)
        diagram_collection = get_diagram_collection(str(song))
        for diag in diagram_collection.items():
            chord_name = diag[0]
            position = chord_position_str(diag[1])
            entry = {"name": chord_name, "position": position}
            if entry not in chordbook.values():
                chordbook[chord_id] = entry
                diag_id = chord_id
                chord_id += 1
            else:
                diag_id = list(chordbook.keys())[
                    list(chordbook.values()).index(entry)
                ]
            chord_occurences[diag_id] += 1
            chords_in_songs[filename].append(diag_id)
            chord_positions[chord_name].add(diag_id)
    print("Writing json files")
    chord_positions = dict(chord_positions)
    for k, v in chord_positions.items():
        chord_positions[k] = list(v)
    with open(outpath / "chordbook.json", "w") as f:
        json.dump(chordbook, f, indent="\t")
    with open(outpath / "chords_in_songs.json", "w") as f:
        json.dump(chords_in_songs, f, indent="\t")
    with open(outpath / "chord_occurences.json", "w") as f:
        json.dump(chord_occurences, f, indent="\t")
    with open(outpath / "chord_positions.json", "w") as f:
        json.dump(chord_positions, f, indent="\t")
