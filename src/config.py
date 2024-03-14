import torch

# Max difference between fingers of the hand
HANDSPAN = 3 # Means that one finger on fret 4 and one on fret 1 is okay, but not fret 5 and fret 1

NUM_STRINGS = 6
NUM_FRETS = 24
PITCH_CLASSES = 12
# MIDI PITCHES FOR STANDARD TUNING
TUNING = [40, 45, 50, 55, 59, 64]

PLAYABILITY_THRESHOLD: float = 0.2

THETA1 = 0.25
THETA2 = 0.5

MIDI_MAP = torch.zeros((NUM_STRINGS, NUM_FRETS))
for s in range(NUM_STRINGS):
    MIDI_MAP[s] += TUNING[s] + torch.arange(0, NUM_FRETS, step=1)
