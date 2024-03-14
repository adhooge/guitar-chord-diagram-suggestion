from src.model.base_model import FingeringPredictor, FingeringPredictorBaseline
import torch 
from typing import Any, List
from src.config import NUM_FRETS, NUM_STRINGS, PITCH_CLASSES
from torch import nn


class MultiLayerFingeringPredictor(FingeringPredictor):
    def __init__(self, hidden_layers_sizes: List[int], 
            with_mute: bool = False, learning_rate: float = 0.001,
            *args: Any, **kwargs: Any) -> None:
        super().__init__(with_mute=with_mute, learning_rate=learning_rate, **kwargs)
        # Input and Output sizes cannot change
        input_layer = nn.Linear((self.num_frets*NUM_STRINGS) + 2*PITCH_CLASSES,
                out_features=hidden_layers_sizes[0])
        output_layer = nn.Linear(hidden_layers_sizes[-1], out_features=NUM_STRINGS*self.num_frets)
        hidden_layers = []
        if len(hidden_layers_sizes) > 1:
            for i, size in enumerate(hidden_layers_sizes[1:]):
                layer = nn.Linear(in_features=hidden_layers_sizes[i-1], out_features=size)
                hidden_layers.append(layer)
        self.model = nn.Sequential(input_layer,
                                   *hidden_layers,
                                   output_layer)
        print(self.model)


class MultilayerBaseline(FingeringPredictorBaseline):
    def __init__(self, hidden_layers_sizes: List[int], 
            with_mute: bool = False, learning_rate: float = 0.001,
            *args: Any, **kwargs: Any) -> None:
        super().__init__(with_mute=with_mute, learning_rate=learning_rate, **kwargs)
        # Input and Output sizes cannot change
        input_layer = nn.Linear(2*PITCH_CLASSES,
                out_features=hidden_layers_sizes[0])
        output_layer = nn.Linear(hidden_layers_sizes[-1], out_features=NUM_STRINGS*self.num_frets)
        hidden_layers = []
        if len(hidden_layers_sizes) > 1:
            for i, size in enumerate(hidden_layers_sizes[1:]):
                layer = nn.Linear(in_features=hidden_layers_sizes[i-1], out_features=size)
                hidden_layers.append(layer)
        self.model = nn.Sequential(input_layer,
                                   *hidden_layers,
                                   output_layer)
        print(self.model)

