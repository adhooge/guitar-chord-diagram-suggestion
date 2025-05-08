import copy
import pickle

from music21 import *

from parserGP import ParserGP


def stream_without_notes(str):
    chordified_stream = str.chordify()
    if (
        len(chordified_stream.getElementsByClass(chord.Chord)) == 0
    ):  # measure without any note
        return True
    return False


def parse_or_unpickle(file_name):
    p_name = file_name.replace(".gp", "") + ".p"
    if p_name in pickle_list:
        print("unpicking {}".format(p_name))
        str = pickle.load(open(pickled_streams_dir + "/" + p_name, "rb"))
        return str
    else:
        print("parsing {}".format(file_name))
        return ParserGP().parseFile(
            gpif_dir + "/" + file_name.replace(".gp", "") + "/score.gpif"
        )


def note_equivalence(n1, n2):
    if n1 == n2 and n1.offset == n2.offset:
        return True
    return False


def note_in_stream(n, str):
    sflat = str.flat
    for e in sflat:
        if type(e) == note.Note and note_equivalence(e, n):
            return True
    return False


def chord_equivalence(c1, c2):
    if len(c1) != len(c2):
        return False
    if c1.offset != c2.offset:
        return False
    for n in c1:
        if n not in c2:
            return False
    return True


def chord_in_stream(c, str):
    sflat = str.flat
    for e in sflat:
        if type(e) == chord.Chord and chord_equivalence(e, c):
            return True
    return False


def stream_equivalence(str1, str2):
    sflat1 = str1.flat
    sflat2 = str2.flat
    if len(sflat1) != len(sflat2):
        return False
    for e1 in sflat1:
        if type(e1) == chord.Chord:
            if not chord_in_stream(e1, str2):
                return False
        if type(e1) == note.Note:
            if not note_in_stream(e1, str2):
                return False
    return True


def double_stream(str):
    print("single stream:")
    str.show("text")
    original_length = str.duration.quarterLength
    double_stream = stream.Stream()
    for e in str.flat:
        double_stream.insert(e.offset, e)
    for e in str.flat:
        new_offset = e.offset + original_length
        new_element = copy.deepcopy(e)
        print("double stream avant nouvel ajout:")
        double_stream.show("text")

        print("element : {} - new : {}".format(e, new_element))
        double_stream.insert(new_offset, new_element)
    print("double stream:")
    double_stream.show("text")
    return double_stream
