from math import exp, sqrt
import warnings
import torch
from src.config import NUM_FRETS, NUM_STRINGS, PITCH_CLASSES, TUNING, MIDI_MAP, HANDSPAN
from typing import List, Tuple, Dict
from src.data.dataset import TorchDataset
from src.data.open_chords import manyhot_is_open_chord
from torch.nn import Softmax, Threshold
import itertools
from collections import defaultdict
from src.data.shape_to_manyhot import shape_to_manyhot
import music21 as m21

TORCH_TUNING = torch.Tensor(TUNING)
SOFTMAX = Softmax(-1)
THRESHOLD_24 = Threshold(-24,0)
THRESHOLD_25 = Threshold(-25,0)
MAX_RANGE = torch.Tensor([[0  , 80 , 95, 110],
                          [80 , 0  , 52, 69 ],
                          [95 , 52 , 0 , 47 ],
                          [110, 69 , 47, 0  ]])
MIN_RANGE = torch.Tensor([[0 , 5  , 15, 25 ],
                          [5 , 0  , 6 , 12 ],
                          [15, 6  , 0 , 8.5],
                          [25, 12 ,8.5, 0  ]])

def _midi_notes_from_fingering(fingering: torch.Tensor,
        tuning: torch.Tensor=TORCH_TUNING, midi_map: torch.Tensor = MIDI_MAP) -> torch.Tensor | None:
    if fingering.ndim == 3:
        return _midi_notes_from_fingering_batchwise(fingering)
    notes_indices = fingering.nonzero(as_tuple=True)
    if len(notes_indices[1]) > NUM_STRINGS:
        raise ValueError("Too many notes detected, model suggested several notes on the same string.")
    pitches = torch.zeros((NUM_STRINGS))
    pitches[:len(notes_indices[1])] = midi_map[notes_indices]
    return pitches

def _midi_notes_from_fingering_batchwise(fingering):
    """
    Je n'ai pas trouvé comment faire sans boucle for pour le moment.
    """
    out = []
    for i in range(fingering.size()[0]):
        try:
            out.append(_midi_notes_from_fingering(fingering[i]))
        except ValueError:
            warnings.warn("Too many notes.")
            continue
    return torch.stack(out) if len(out) > 0 else None

def _are_notes_accepted(accepted_pitches: torch.Tensor, root_note: torch.Tensor,
        notes: torch.Tensor, num_pc: int = PITCH_CLASSES) -> torch.Tensor:
    if accepted_pitches.ndim == 2:
        return _are_notes_accepted_batchwise(accepted_pitches, root_note, notes)
    notes = notes[notes.nonzero()] % num_pc
    accepted_pitches = torch.nonzero(accepted_pitches, as_tuple=False)
    out = torch.ones((NUM_STRINGS), dtype=torch.bool)
    out[:notes.size()[0]] = torch.isin(notes, accepted_pitches)[:, 0]
    return out


def _are_notes_accepted_batchwise(accepted_pitches, root_note, notes):
    out = []
    for i in range(notes.size()[0]):
        out.append(_are_notes_accepted(accepted_pitches[i],
            root_note[i], notes[i]))
    return torch.stack(out)

def _is_chord_complete(required_pitches: torch.Tensor, root_note: torch.Tensor,
        notes: torch.Tensor, num_pc: int = PITCH_CLASSES) -> torch.Tensor:
    if required_pitches.ndim == 2:
        return _is_chord_complete_batchwise(required_pitches, root_note, notes)
    notes = notes[notes.nonzero()] % num_pc
    required_pitches = torch.nonzero(required_pitches, as_tuple=False)
    out = torch.isin(required_pitches, notes)[:, 0]
    return out.mean(dtype=torch.float32)

def _is_chord_complete_batchwise(required_pitches, root_note, notes):
    out = []
    for i in range(notes.size()[0]):
        out.append(_is_chord_complete(required_pitches[i],
            root_note[i], notes[i]))
    return torch.stack(out)

def _is_playable(fingering_vector: torch.Tensor, handspan: int, with_mute: bool=False) -> torch.Tensor:
    if fingering_vector.ndim == 3:
        return _is_playable_batchwise(fingering_vector, handspan, with_mute)
    else:
        fingering_str = TorchDataset.fingering_from_target_tensor(fingering_vector, with_mute=with_mute)
        min_fret = 25
        max_fret = 0
        for char in fingering_str.split('.'):
            if char in ['x', '']:
                continue
            else:
                fret = int(char)
                if fret > max_fret:
                    max_fret = fret
                if fret < min_fret and fret != 0:
                    min_fret = fret
        return torch.Tensor([max_fret - min_fret <= handspan])

def _is_playable_batchwise(fingering_vector: torch.Tensor, handspan: int, with_mute: bool) -> torch.Tensor:
    to_stack = []
    for vec in fingering_vector:
        to_stack.append(_is_playable(vec, handspan, with_mute))
    return torch.stack(to_stack, dim=0)


def pitch_class_loss(chord_vector: torch.Tensor,
        fingering_vector: torch.Tensor,
        with_mute: bool = False,
        num_frets: int = NUM_FRETS,
        num_strings: int = NUM_STRINGS,
        num_pc: int = PITCH_CLASSES,
        tuning: torch.Tensor = TORCH_TUNING) -> torch.Tensor:
    """pitch_class_loss.
    From chord_vector representing the chord label and the proposed fingering,
    checks if all notes in that fingering are consistent with chord label.

    Args:
        chord_vector (torch.Tensor): chord_vector
        fingering_vector (torch.Tensor): fingering_vector
        num_frets (int): num_frets
        num_strings (int): num_strings
        num_pc (int): num_pc

    Returns:
        torch.Tensor:
    """
    if chord_vector.ndim == 1:
        chord_vector = chord_vector[None, :]
    if fingering_vector.ndim == 2:
        fingering_vector = fingering_vector[None, :, :]
    if with_mute:
        fingering_vector = fingering_vector[:, :, :-1]
    root_note_vector = chord_vector[:, :num_pc]
    accepted_pitches = chord_vector[:, num_pc:]
    notes = _midi_notes_from_fingering(fingering_vector)
    print(notes)
    if notes is None:
        return None
    res = _are_notes_accepted(accepted_pitches, root_note_vector, notes)
    print(res)
    return res.mean(dim=-1, dtype=torch.float32)

def completeness_metric(chord_vector: torch.Tensor,
        fingering_vector: torch.Tensor,
        with_mute: bool = False,
        num_pc: int = PITCH_CLASSES):
    """
    Assert wether the provided fingering contains ALL pitches
    expected by the chord_vector.
    """
    if chord_vector.ndim == 1:
        chord_vector = chord_vector[None, :]
    if fingering_vector.ndim == 2:
        fingering_vector = fingering_vector[None, :, :]
    if with_mute:
        fingering_vector = fingering_vector[:, :, :-1]
    root_note_vector = chord_vector[:, :num_pc]
    accepted_pitches = chord_vector[:, num_pc:]
    notes = _midi_notes_from_fingering(fingering_vector)
    if notes is None:
        return 0
    res = _is_chord_complete(accepted_pitches, root_note_vector, notes)
    return res.mean(dim=-1, dtype=torch.float32)

def open_chord_metric(fingering_vector: torch.Tensor, expected_fingering:torch.Tensor) -> torch.Tensor:
    """open_chord_metric.

    Args:
        fingering_vector (torch.Tensor): fingering_vector [(batch_size,) num_strings, num_frets]
        expected_fingering (torch.Tensor): expected_fingering [(batch_size,) num_strings, num_frets]
    Returns:
        torch.Tensor: [batch_size, 1], True if fingering
        is same (open/closed) as expected, False otherwise.
    """
    if fingering_vector.ndim == 3:
        out = torch.zeros((fingering_vector.size()[0], 1), dtype=torch.bool)
        for i, sample in enumerate(fingering_vector):
            out[i] = manyhot_is_open_chord(sample) == manyhot_is_open_chord(expected_fingering[i])
    else:
        out = manyhot_is_open_chord(fingering_vector) == manyhot_is_open_chord(expected_fingering)
    return out

def stringwise_exactness(fingering_vector: torch.Tensor, expected_fingering: torch.Tensor) -> torch.Tensor:
    """stringwise_exactness.

    Args:
        fingering_vector (torch.Tensor): fingering_vector [BATCHSIZE, NUM_STRINGS, NUM_FRETS]
        expected_fingering (torch.Tensor): expected_fingering [same]

    Returns:
        torch.Tensor: [BATCHSIZE, NUM_STRINGS, 1]
    """
    return torch.mean(torch.eq(fingering_vector, expected_fingering).all(dim=-1), dim=-1, dtype=torch.float32)


def playability_metric(fingering_vector: torch.Tensor, handspan_limit: int = HANDSPAN,
        with_mute: bool = False) -> torch.Tensor:
    res = _is_playable(fingering_vector, handspan_limit, with_mute)
    return res

def stringfret_precision(fingering_vector: torch.Tensor, expected_fingering: torch.Tensor,
        with_mute: bool = False, tol = 1e-8) -> torch.Tensor:
    if with_mute:
        fingering_vector = fingering_vector[:, :, :-1]
        expected_fingering = expected_fingering[:, :, :-1]
    TP = torch.count_nonzero((fingering_vector + expected_fingering)==2, dim=(-1, -2))
    FP = torch.count_nonzero((expected_fingering-fingering_vector)==-1, dim=(-1, -2)) 
    out = torch.div(TP, TP+FP)
    out = torch.nan_to_num(out, nan=0, posinf=0, neginf=0)
    return out

def stringfret_recall(fingering_vector: torch.Tensor, expected_fingering: torch.Tensor,
        with_mute: bool = False) -> torch.Tensor:
    if with_mute:
        fingering_vector = fingering_vector[:, :, :-1]
        expected_fingering = expected_fingering[:, :, :-1]
    TP = torch.count_nonzero((fingering_vector+expected_fingering)==2, dim=(-1, -2))
    FN = torch.count_nonzero((fingering_vector-expected_fingering)==-1, dim=(-1, -2)) 
    out = torch.div(TP, TP+FN)
    out = torch.nan_to_num(out, nan=0, posinf=0, neginf=0)
    return out

def stringfret_f1(fingering_vector, expected_fingering, with_mute: bool = False, tol=1e-8):
    if with_mute:
        fingering_vector = fingering_vector[:, :, :-1]
        expected_fingering = expected_fingering[:, :, :-1]
    TP = torch.count_nonzero((fingering_vector + expected_fingering)==2, dim=(-1, -2))
    FP = torch.count_nonzero((expected_fingering-fingering_vector)==-1, dim=(-1, -2)) 
    FN = torch.count_nonzero((fingering_vector-expected_fingering)==-1, dim=(-1, -2)) 
    out = torch.div(2*TP, 2*TP + FP + FN)
    out = torch.nan_to_num(out, nan=0, posinf=0, neginf=0)
    return out


def _get_index_finger(chord: str) -> int:
    index_pos = 25
    for char in chord.split('.'):
        if char not in ['x', '']:
            if int(char) < index_pos:
                index_pos = int(char)
    return index_pos

def _get_fret_span(chord: str) -> int:
    min_fret = 25
    max_fret = 0
    for char in chord.split('.'):
        if char in ['x', '']:
            continue
        else:
            fret = int(char)
            if fret > max_fret:
                max_fret = fret
            if fret < min_fret and fret != 0:
                min_fret = fret
    return max(max_fret - min_fret, 0)

def _get_num_fingers(chord: str) -> int:
    num = 0
    for char in chord.split('.'):
        if char not in ['x', '', '0']:
            num += 1
    return min(num, 4) # hard to put more than 4 fingers on the fretboard

def chord_distance(chord1: str, chord2: str, t: float = 1) -> float:
    index1 = _get_index_finger(chord1)
    index2 = _get_index_finger(chord2)
    fret_span2 = _get_fret_span(chord2)
    num_fingers2 = _get_num_fingers(chord2)
    out = exp(-abs(index2 - index1)/t)/(2*t)
    out = out/((1+index2)*(1+fret_span2)*(1+num_fingers2))
    return out


def hand_span_tensor(fingering_vector: torch.Tensor, with_mute: bool = True) -> torch.Tensor:
    """hand_span_tensor.

    Args:
        fingering_vector (torch.Tensor): fingering_vector [batch, num_strings, num_frets
        center_val (float): center_val for sigmoid function. Default is 1.392 on analysis of validation set.

    Returns:
        torch.Tensor:
    """
    batch, num_strings, num_frets = fingering_vector.size()
    if fingering_vector.dtype is torch.bool:
        fingering_vector = fingering_vector.type(torch.float32)
    #if with_mute:
    #    #drop mute coeff
    #    fingering_vector = fingering_vector[:, :, :-1]
    #    num_frets -= 1
    #fingering_vector = fingering_vector[:, :, 1:]   # drop open strings
    #num_frets -= 1
    tmp = SOFTMAX(fingering_vector*100)
    range_max = torch.arange(start=0, end=num_frets, step=1, dtype=torch.float32)
    range_min = torch.arange(start=num_frets, end=0, step=-1, dtype=torch.float32)
    tmp_max = (torch.sum(tmp*range_max[None, None, :].expand(batch, num_strings, num_frets), dim=-1))
    #tmp_max = (torch.remainder(tmp_max, 24))
    tmp_max = - THRESHOLD_24(-tmp_max)
    max_frets = torch.max(tmp_max, dim=-1).values
    tmp_min = (torch.sum(tmp*range_min[None, None, :].expand(batch, num_strings, num_frets), dim=-1))
    tmp_min = - THRESHOLD_25(-tmp_min)
    #tmp_min = (torch.remainder(tmp_min, num_frets))
    tmp_min = torch.max(tmp_min, dim=-1).values 
    min_frets = 25 - tmp_min
    #min_frets = torch.remainder(num_frets, tmp_min)
    return max_frets - min_frets
    #tmp = fingering_vector.argmax(dim=-1)
    #max_frets = tmp.max(dim=-1).values + 1
    #tmp_min = fingering_vector * torch.arange(start=num_frets, end=0, step=-1)
    #tmp_min = tmp_min.max(dim=-1).values 
    #min_frets = tmp_min.max(dim=-1).values
    #min_frets = torch.remainder(num_frets + 1, min_frets + 1) + 1  # +1 inside function are to avoid zero division
    #return max_frets - min_frets


def hand_span_loss(fingering_vector: torch.Tensor, with_mute: bool = False,
        center_val: float = 1.392) -> float:
    """hand_span_loss.

    Args:
        fingering_vector (torch.Tensor): fingering_vector [batch, num_strings, num_frets
        center_val (float): center_val for sigmoid function. Default is 1.392 on analysis of validation set.

    Returns:
        torch.Tensor:
    """
    hand_span_t = hand_span_tensor(fingering_vector, with_mute)
    out = 1/(1+torch.exp(-(hand_span_t - center_val)))
    return torch.mean(out)


def pc_precision(expected_notes: List[str], pred_notes: List[str]) -> float:
    expected = set(expected_notes)
    pred = set(pred_notes)
    size = len(pred)
    if size == 0:
        return 1
    unwanted_notes = pred.difference(expected)
    return (size - len(unwanted_notes))/size

def pc_recall(expected_notes: List[str], pred_notes: List[str]) -> float:
    expected = set(expected_notes)
    pred = set(pred_notes)
    size = len(expected)
    if size == 0:
        return 1
    missing_notes = expected.difference(pred)
    return (size - len(missing_notes))/size


def fret_distance(m: int, n: int, scale_length: float = 620) -> float:
    if m > n:
        m, n = n, m
    s = scale_length
    out = s*(2**(n/12) - 2**(m/12))/(2**((m+n)/12))
    return out

def string_distance(s1: int, s2: int, y: float,bridge_size: float = 58.7, nut_size: float = 44.4,
        scale_length: float = 620, num_strings: int = 6) -> float:
    string_hop = abs(s1 - s2)/(num_strings-1)
    dist = (nut_size-bridge_size)*y/scale_length + bridge_size
    return dist*string_hop

def finger_distance(s1: int, f1: int, s2: int, f2: int,
                    gamma: float = 36, max_fret: int = 24,
                    bridge_size: float = 58.7, nut_size: float = 44.4,
                    scale_length: float = 620, num_strings: int = 6) -> float:
    f_dist = fret_distance(f1, f2, scale_length)
    s_dist = string_distance(s1, s2, min(f1,f2), bridge_size, nut_size, scale_length, num_strings)
    return sqrt(f_dist**2 + s_dist**2)

def finger_score(x: float, finger1: int, finger2: int, pinky_penalty: float = 0.85) -> float:
    a = MIN_RANGE[finger1, finger2].item()
    b = MAX_RANGE[finger1, finger2].item()
    if finger1 == 3 or finger2 == 3:
        penalty = pinky_penalty
    else:
        penalty = 1
    if x < a:
        return (1 + (x - 0.99*a)**3) * penalty
    else:
        return (1 - ((x - 0.99*a)/(1.01*b - 0.99*a))**2) * penalty

def get_string_fret_set(fingering: str) -> List[Tuple[int, int]]:
    out = []
    string_count = 6
    for val in fingering.split('.'):
        if val in ['', 'x']:
            string_count -= 1
            continue
        else:
            out.append((string_count, int(val)))
            string_count -= 1
    return out

def get_possible_fingerings(sf_set) -> List[Dict[int, List[Tuple[int, int]]]]:
    out = []
    sorted_set = sorted(sorted(sf_set, key=(lambda x: x[0]), reverse=True), key=(lambda x: x[1]))
    sorted_set = [a for a in sorted_set if a[1] != 0]   # remove open strings
    if len(sorted_set) >= 4:
        combinations = itertools.combinations([1]*(len(sorted_set)-2) + [2,3,4], len(sorted_set))
    else:
        combinations = itertools.combinations(range(1, 5), len(sorted_set))
    for combi in combinations:
        dico = defaultdict(list)
        for i, f in enumerate(combi):
            dico[f].append(sorted_set[i])
        skip = False
        for v in dico.values():
            if len(v) == 1:
                continue
            else:
                fret = v[0][1]
                for pair in v:
                    if pair[1] != fret:
                        skip = True
                        break
        if not skip:
            out.append(dico)
    return out

def _anatomical_score(fingering: Dict[int, List[Tuple[int, int]]]) -> float:
    score = 0
    fingers = list(fingering.keys())
    m = len(fingers)
    if m == 1:
        if len(fingering[fingers[0]]) == 1:
            # all one note "chords" are playable
            return 1
    div = max(m**2-m, 1)
    for i in range(len(fingers)):
        for j in range(i+1, len(fingers)):
            d1, d2 = fingers[i], fingers[j]
            for k in range(len(fingering[d1])):
                for l in range(len(fingering[d2])):
                    s1, s2 = fingering[d1][k][0], fingering[d2][l][0]
                    f1, f2 = fingering[d1][k][1], fingering[d2][l][1]
                    x = finger_distance(s1, f1, s2, f2)
                    fscore = finger_score(x, fingers[i]-1, fingers[j]-1)
                    score += fscore
    return score/div


def anatomical_score(diagram: str) -> Tuple[float, Dict[int, Tuple[int, int]]]:
    string_fret_set = get_string_fret_set(diagram)
    only_open_strings = True
    for sf in string_fret_set:
        if sf[1] != 0:
            only_open_strings = False 
            break
    if only_open_strings:
        return 1, None
    fingerings = get_possible_fingerings(string_fret_set)
    score = 0
    best_fingering = None
    for fingering in fingerings:
        fscore = _anatomical_score(fingering)
        if fscore > score:
            score = fscore
            best_fingering = fingering
    return score, best_fingering


def wrist_movement(fingering1: Dict[int, List[Tuple[int, int]]],
        fingering2: Dict[int, List[Tuple[int, int]]]) -> int:
    index1 = fingering1[1][0][1]
    index2 = fingering2[1][0][1]
    return abs(index1 - index2)

def manhattan_distance(v1: Tuple[int, int], v2: Tuple[int, int]) -> int:
    string_dist = abs(v1[0] - v2[0])
    fret_dist = abs(v1[1] - v2[1])
    return string_dist + fret_dist

def finger_movement(fingering1: Dict[int, List[Tuple[int, int]]],
                    fingering2: Dict[int, List[Tuple[int, int]]]) -> int:
    mvt = 0
    for finger in fingering1.keys():
        if finger in fingering2.keys():
            for sf_pair1 in fingering1[finger]:
                for sf_pair2 in fingering2[finger]:
                    dist = manhattan_distance(sf_pair1, sf_pair2)
                    mvt += dist
    return mvt

def transition_cost(fingering1: Dict[int, List[Tuple[int, int]]], 
                    fingering2: Dict[int, List[Tuple[int, int]]],
                    theta1: float = 1, theta2: float = 1) -> float:
    if fingering1 is None or fingering2 is None:
        return 0
    a1 = wrist_movement(fingering1, fingering2)
    a2 = finger_movement(fingering1, fingering2)
    return 1/(1+(theta1*a1) + (theta2*a2))

def ratio_muted_strings(diagram: str, num_strings: int = NUM_STRINGS) -> float:
    muted_strings = diagram.count('x')
    return muted_strings / num_strings

def ratio_open_strings(diagram: str, num_strings: int = NUM_STRINGS) -> float:
    open_strings = diagram.count('0')
    strings_played = num_strings_played(diagram, num_strings)
    if strings_played == 0:
        return 0
    return open_strings / strings_played

def num_strings_played(diagram: str, num_strings: int = NUM_STRINGS) -> float:
    muted_strings = diagram.count('x')
    return num_strings - muted_strings

def string_centroid(diagram: str, num_strings: int = NUM_STRINGS) -> float:
    centroid = 0
    string = num_strings
    for v in diagram.split('.'):
        if v in ['x', '']:
            string -= 1
            continue
        else:
            centroid += string
            string -= 1
    strings_played = num_strings_played(diagram, num_strings)
    if strings_played == 0:
        return 0
    centroid = centroid / strings_played
    return centroid
        
def ratio_unique_notes(diagram: str, num_strings: int = NUM_STRINGS) -> float: 
    if diagram[-1] == '.':
        diagram = diagram[:-1]
    array = shape_to_manyhot(diagram, with_mute=False)
    notes = _midi_notes_from_fingering(array)
    notes_reduced = set([m21.note.Note(a).name for a in notes if a != 0])
    num_notes_played = num_strings_played(diagram, num_strings)
    if num_notes_played == 0:
        return 0
    return len(notes_reduced)/num_notes_played
