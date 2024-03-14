import torch
from src.config import NUM_FRETS, NUM_STRINGS

def shape_to_manyhot(shape: str,
        num_frets: int = NUM_FRETS, num_strings: int = NUM_STRINGS,
        with_mute: bool = False) -> torch.Tensor:
    fingerings = shape.split('.')
    if with_mute:
        # add a coeff for muted strings
        num_frets += 1
    out = torch.zeros((num_strings, num_frets), dtype=torch.bool)
    for i, f in enumerate(fingerings):
        if f == 'x':
            if with_mute:
                out[i][-1] = 1
            else:
                continue
        else:
            if int(f) >= num_frets:
                raise ValueError(f"Fret {f} cannot be included in fretboard of size {num_frets}.")
            out[i][int(f)] = 1
    return out
