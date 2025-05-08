import torch

def shape_is_open_chord(shape: str) -> bool:
    return '0' in shape

def manyhot_is_open_chord(manyhot: torch.Tensor) -> bool:
    return (manyhot[:, 0] == 1).any()
