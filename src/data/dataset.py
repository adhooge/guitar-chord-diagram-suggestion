import pandas as pd
import torch
from src.data.shape_to_manyhot import shape_to_manyhot
from src.data.chord_label_translator import get_vector_representation, get_chord_label_notes, get_chord_label
from src.config import NUM_FRETS, NUM_STRINGS, PITCH_CLASSES
import src.data.chord_functions as F
from src.data.open_chords import shape_is_open_chord
from tqdm import tqdm
import src.exceptions as E

class SimpleDataset():

    def __init__(self, df_path: str | None, df: pd.DataFrame | None) -> None:
        self.df_path: str | None
        self.df: pd.DataFrame
        self.unique_df: pd.DataFrame
        self.df_path = df_path
        self.df = pd.read_csv(df_path, index_col=0) if df_path is not None else df
        if 'filename' in self.df.columns:
            self.df = self.df.drop_duplicates(
                    subset=['filename', 'current_chord', 'next_chord',
                        'current_position', 'next_position'])
    
    def previous_chord(self):
        return self.df['current_chord']

    def previous_position(self):
        return self.df['current_position']

    def current_chord(self):
        return self.df['next_chord']

    def current_position(self):
        return self.df['next_position']

    def target(self):
        return self.current_position()

    def source(self):
        return (self.previous_chord(), self.previous_position(),
    self.current_chord())

    def __len__(self):
        return len(self.df)


class TorchDataset(torch.utils.data.Dataset):

    @staticmethod
    def fingering_from_source_tensor(tensor: torch.Tensor,
            with_mute: bool = False) -> str:
        t = tensor[:-2*PITCH_CLASSES]
        num_frets = NUM_FRETS + 1 if with_mute else NUM_FRETS
        t = torch.reshape(t, (NUM_STRINGS, num_frets))
        out = ""
        for row in t:
            if with_mute and torch.argmax(row) == (num_frets-1):
                out += "x."
                continue
            l = torch.argwhere(row>0.5)
            if len(l) == 0:
                out += "x"
            elif len(l) == 1:
                out += str(l[0].item())
            else:
                for v in l:
                    out += str(v.item())
                    out += "|"
            out += '.'
        return out

    @staticmethod
    def fingering_from_target_tensor(tensor: torch.Tensor,
            with_mute: bool = False) -> str:
        num_frets = NUM_FRETS + 1 if with_mute else NUM_FRETS
        t = torch.reshape(tensor, (NUM_STRINGS, num_frets))
        out = ""
        for row in t:
            if with_mute and torch.argmax(row) == (num_frets-1):
                out += "x."
                continue
            l = torch.argwhere(row == 1)
            if len(l) == 0:
                out += "x"
            elif len(l) == 1:
                out += str(l[0].item())
            else:
                for v in l:
                    out += str(v.item())
                    out += "|"
            out += '.'
        return out

    @staticmethod
    def chordlabel_from_source_tensor(tensor: torch.Tensor) -> str:
        t = tensor[-2*PITCH_CLASSES:]
        return get_chord_label(t)


    def __init__(self, df_path: str | None, df: pd.DataFrame | None,
            with_mute: bool = False, drop_duplicates_strict: bool = False,
            drop_duplicates_stricter: bool = False,
            drop_duplicates_strictest: bool = False,
            augment: bool = False) -> None:
        self.df_path: str | None
        self.df: pd.DataFrame
        self.unique_df: pd.DataFrame
        self.df_path = df_path
        self.df = pd.read_csv(df_path, index_col=0) if df_path is not None else df
        self.df = self.df.reset_index(drop=True)
        self._clean_df()
        if augment:
            self.data_augment()
            self._clean_df()
        if 'filename' in self.df.columns:
            if drop_duplicates_strictest:
                self.df = self.df.drop_duplicates(
                    subset=['next_chord'])
            elif drop_duplicates_stricter:
                self.df = self.df.drop_duplicates(
                    subset=['next_chord','next_position'])
            elif drop_duplicates_strict:
                self.df = self.df.drop_duplicates(
                    subset=['filename', 'next_chord','next_position'])
            else:
                self.df = self.df.drop_duplicates(
                        subset=['filename', 'current_chord', 'next_chord',
                            'current_position', 'next_position'])
            self.df = self.df.reset_index()
        if augment:
            self.df.to_csv('cleaned_df_with_augmentation.csv')
        self.with_mute = with_mute
        super().__init__()

    def _clean_df(self):
        """
        Some chord labels are not known yet. Remove them from the df until they're
        dealt with.
        """
        to_drop = []
        for i in range(len(self.df)):
            if get_chord_label_notes(self.df.iloc[i]['next_chord']) is None:
                to_drop.append(i)
        self.df = self.df.drop(index=to_drop)
        print(f"Dropped {len(to_drop)} unknown chords.")

    def _current_fingering_from_idx(self, index):
        return shape_to_manyhot(self.df.iloc[index]['current_position'],
                with_mute=self.with_mute).type(torch.float)

    def _next_fingering_from_idx(self, index):
        return shape_to_manyhot(self.df.iloc[index]['next_position'],
                with_mute=self.with_mute).type(torch.float)

    def _next_chord_from_idx(self, index):
        return get_vector_representation(self.df.iloc[index]['next_chord'], tensor=True)

    def __getitem__(self, index):
        current_fingering = self._current_fingering_from_idx(index)
        next_fingering = self._next_fingering_from_idx(index)
        next_chord = self._next_chord_from_idx(index)
        return torch.cat((torch.flatten(current_fingering), next_chord)), torch.flatten(next_fingering)

    def __len__(self):
        return len(self.df)

    def data_augment(self):
        to_add = []
        for i, row in tqdm(self.df.iterrows()):
            if '0' in row['current_position'] or '0' in row['next_position']:
                continue
            else:
                new_df = self.augment_from_row(row)
                if new_df is None:
                    continue
                to_add.append(new_df)
        augmented_df = pd.concat(to_add, ignore_index=True)
        self.df = pd.concat([self.df, augmented_df], ignore_index=True) 
        self.df.to_csv(self.df_path + 'with_augmentation')

    def augment_from_row(self, row):
        df = pd.DataFrame(columns=self.df.columns)
        filename = row['filename'] + '-augmented'
        measure = row['measure']
        current_chord = row['current_chord']
        next_chord = row['next_chord']
        current_pos = row['current_position']
        next_pos = row['next_position']
        new_current_chord = current_chord
        new_next_chord = next_chord
        new_current_pos = current_pos
        new_next_pos = next_pos
        #print(filename, current_chord, next_chord)
        while not shape_is_open_chord(new_current_pos) and not shape_is_open_chord(new_next_pos):
            try:
                new_current_chord, new_current_pos = F.transpose(new_current_chord, new_current_pos, -1)
            except E.RootError:
                return None
            new_next_chord, new_next_pos = F.transpose(new_next_chord, new_next_pos, -1)
            df.loc[-1] = [filename, measure, new_current_chord, new_next_chord,
                          new_current_pos, new_next_pos]
            df.index += 1
            df = df.sort_index()
        new_current_chord = current_chord
        new_next_chord = next_chord
        new_current_pos = current_pos
        new_next_pos = next_pos
        while not F.reach_twelfth_fret(new_current_pos) and not F.reach_twelfth_fret(new_next_pos):
            new_current_chord, new_current_pos = F.transpose(new_current_chord, new_current_pos, 1)
            new_next_chord, new_next_pos = F.transpose(new_next_chord, new_next_pos, 1)
            df.loc[-1] = [filename, measure, new_current_chord, new_next_chord,
                          new_current_pos, new_next_pos]
            df.index += 1
            df = df.sort_index()
        return df



