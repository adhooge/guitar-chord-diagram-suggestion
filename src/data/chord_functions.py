from typing import Tuple
import music21 as m21
import src.exceptions as E


def get_root_from_chordname(chord: str) -> str:
    idx = 0
    if chord[idx] == '(':
        idx += 1
    tonic = chord[idx]
    if tonic == 'H':
        # polish/german notation
        tonic = 'B'
    idx += 1
    try:
        if chord[idx] in ['b', '#']:
            alt = chord[idx]
        else:
            alt = ''
    except IndexError:
        alt = ''
    return tonic + alt

def get_bass_from_chordname(chord: str) -> str:
    bass = ''
    if '/' in chord:
        bass = chord.split('/')[-1]
    if bass.isdigit():
        bass = ''
    elif '+' in bass or '-' in bass:
        bass = ''
    return bass

def transpose_down(root1: str, root2: str, pos1: str, pos2: str) -> Tuple[str,str,str,str]:
    new_root1, new_root2 = _previous_roots(root1, root2)
    new_pos1 = _shift_pos(pos1, root1, new_root1)
    new_pos2 = _shift_pos(pos2, root2, new_root2)
    return new_root1, new_root2, new_pos1, new_pos2

def transpose_up(root1: str, root2: str, pos1: str, pos2: str) -> Tuple[str,str,str,str]:
    new_root1, new_root2 = _next_roots(root1, root2)
    new_pos1 = _shift_pos(pos1, root1, new_root1)
    new_pos2 = _shift_pos(pos2, root2, new_root2)
    return new_root1, new_root2, new_pos1, new_pos2

def _previous_root(root: str) -> str:
    note = m21.note.Note(root)
    previous = note.transpose(-1).name
    if '-' in previous:
        previous = previous.replace('-', 'b')
    return previous

def _next_root(root: str) -> str:
    note = m21.note.Note(root)
    nextr = note.transpose(+1).name
    if '-' in nextr:
        nextr = nextr.replace('-', 'b')
    return nextr

def _get_midi_diff(root1: str, root2: str) -> int:
    midi2 = m21.note.Note(root2).pitch.midi
    midi1 = m21.note.Note(root1).pitch.midi
    midi1 = midi1 % 12
    midi2 = midi2 % 12
    diff = midi2 - midi1
    if diff > 6:
        diff = diff - 12
    if diff < -6:
        diff = diff + 12
    return diff

def _next_roots(root1: str, root2: str) -> Tuple[str, str]:
    nr1 = _next_root(root1)
    nr2 = _next_root(root2)
    diff1 = _get_midi_diff(root1, nr1)
    diff2 = _get_midi_diff(root2, nr2)
    if diff1 != diff2:
        ddiff1 = diff1
        nnr1 = nr1
        while ddiff1 < diff2:
            nnr1 = _next_root(nnr1)
            ddiff1 = _get_midi_diff(root1, nnr1)
        if ddiff1 == diff2:
            return nnr1, nr2
        else:
            ddiff2 = diff2
            nnr2 = nr2
            while ddiff2 < diff1:
                nnr2 = _next_root(nnr2)
                ddiff2 = _get_midi_diff(root2, nnr2)
            if ddiff2 == diff1:
                return nr1, nnr2
    else:
        return nr1, nr2

def _previous_roots(root1: str, root2: str) -> Tuple[str, str]:
    pr1 = _previous_root(root1)
    pr2 = _previous_root(root2)
    diff1 = _get_midi_diff(root1, pr1)
    diff2 = _get_midi_diff(root2, pr2)
    if diff1 != diff2:
        ddiff1 = diff1
        ppr1 = pr1
        while ddiff1 > diff2:
            ppr1 = _previous_root(ppr1)
            ddiff1 = _get_midi_diff(root1, ppr1)
        if ddiff1 == diff2:
            return ppr1, pr2
        else:
            ddiff2 = diff2
            ppr2 = pr2
            while ddiff2 > diff1:
                ppr2 = _previous_root(ppr2)
                ddiff2 = _get_midi_diff(root2, ppr2)
            if ddiff2 == diff1:
                return pr1, ppr2
    else:
        return pr1, pr2


def _shift_pos(pos: str, root: str, new_root: str) -> str:
    diff = _get_midi_diff(root, new_root)
    if diff == 0:
        return pos
    else:
        new_pos = transpose_pos(pos, diff)
    return new_pos

def transpose_pos(pos: str, diff: int) -> str:
    new_pos = ''
    for char in pos.split('.'):
        if char in ['x', '']:
            new_pos += char
        else:
            new_char = str(int(char) + diff)
            new_pos += new_char
        new_pos += '.'
    return new_pos[:-1]

def reach_twelfth_fret(pos: str) -> bool:
    for fret in pos.split('.'):
        if fret in ['x', '']:
            continue
        if int(fret) >= 12:
            return True
    return False

def replace_root(chord: str, old_root: str, new_root: str) -> str:
    out = chord.replace(old_root, new_root, 1)
    return out

def replace_bass(chord: str, old_bass: str, new_bass: str) -> str:
    out = chord.replace('/' + old_bass, '/' + new_bass)
    return out

def update_chord(chord: str, old_root: str, new_root: str,
                old_bass: str, new_bass: str) -> str:
    if old_bass == '':
        if new_bass != '':
            raise ValueError(f"Why is old bass empty and not new bass?")
    out = replace_root(chord, old_root, new_root)
    out = replace_bass(out, old_bass, new_bass)
    return out

def transpose(chordname: str, pos: str, shift: int) -> Tuple[str, str]:
    root = get_root_from_chordname(chordname)
    bass = get_bass_from_chordname(chordname)
    if shift == 1:
        try:
            new_root = _next_root(root)
        except m21.pitch.PitchException:
            raise E.RootError
        if bass != '':
            try:
                new_bass = _next_root(bass)
            except m21.pitch.PitchException:
                raise E.RootError
        else:
            new_bass = ''
        new_pos = transpose_pos(pos, shift)
        new_chord = update_chord(chordname, root, new_root, bass, new_bass)
    elif shift == -1:
        try:
            new_root = _previous_root(root)
        except m21.pitch.PitchException:
            raise E.RootError
        if bass != '':
            #print('bass:', bass)
            try:
                new_bass = _previous_root(bass)
            except m21.pitch.PitchException:
                raise E.RootError
        else:
            new_bass = ''
        new_pos = transpose_pos(pos, shift)
        new_chord = update_chord(chordname, root, new_root, bass, new_bass)
    else:
        raise ValueError(f"Shift other than +/- 1 is not supported yet. You tried shifting with {shift}")
    return new_chord, new_pos

