from collections import defaultdict
import torch
from argparse import ArgumentParser
import sys
import pathlib
import pandas as pd
import lightning as L

from torch.utils.data.dataloader import DataLoader
from cds.model.base_model import FingeringPredictor, FingeringPredictorBaseline
from cds.model.multilayer_model import MultiLayerFingeringPredictor, MultilayerBaseline
from cds.data.dataset import TorchDataset
from cds.data.shape_to_manyhot import shape_to_manyhot
from cds.data.chord_label_translator import get_vector_representation
from cds.model.losses import playability_metric, _midi_notes_from_fingering, completeness_metric, pitch_class_loss, pc_precision, pc_recall
import cds.model.losses as Lo
import music21 as m21
from statistics import mean, stdev


def main(parser: ArgumentParser) -> int:
    args = parser.parse_args()
    SOURCEPATH = pathlib.Path(args.sourcepath)
    if SOURCEPATH.is_dir():
        ckpts = sorted(list(SOURCEPATH.glob("*.ckpt")))
    else:
        ckpts = [SOURCEPATH]
    DATAPATH = pathlib.Path(args.data)
    if DATAPATH.is_dir():
        datasets = sorted(list(DATAPATH.glob("*.csv")))
    else:
        datasets = [DATAPATH]
    results = defaultdict(list)
    for c, ckpt in enumerate(ckpts):
        dataset = datasets[c]
        if args.verbose:
            print(f"Loading model {ckpt}...")
        print(ckpt)
        if args.label:
            if args.multilayer:
                model = MultilayerBaseline.load_from_checkpoint(ckpt)
            else:
                model = FingeringPredictorBaseline.load_from_checkpoint(ckpt)
        elif args.multilayer:
            model = MultiLayerFingeringPredictor.load_from_checkpoint(ckpt)
        else:
            model = FingeringPredictor.load_from_checkpoint(ckpt)
        if args.full_test:
            if args.verbose:
                print(f"Testing the model on {DATAPATH}")
            if args.strict:
                data = TorchDataset(dataset, None, model.with_mute, drop_duplicates_strict=True) 
            elif args.stricter:
                data = TorchDataset(dataset, None, model.with_mute, drop_duplicates_stricter=True) 
            elif args.strictest:
                data = TorchDataset(dataset, None, model.with_mute, drop_duplicates_strictest=True) 
            else:
                data = TorchDataset(dataset, None, model.with_mute) 
            print("Final dataset size is: ", data.__len__())
            dataloader = DataLoader(data, batch_size=args.batch_size)
            trainer = L.Trainer()
            trainer.test(model, dataloader)
            for k,v in trainer.logged_metrics.items():
                results[k].append(v.item())
        elif args.save_pred:
            df = pd.read_csv(DATAPATH)
            out_df = pd.DataFrame(columns=['file', 'measure', 'previous_fingering',
                                           'previous_label', 'expected_label',
                                           'expected_fingering', 'pred'])
            out_list = []
            for i, row in df.iterrows():
                label = row['current_chord']
                exp_label = row['next_chord']
                fing = row['current_position']
                exp_fing = row['next_position']
                exp_vec = shape_to_manyhot(exp_fing, with_mute=model.with_mute)
                try:
                    chord_vec = get_vector_representation(exp_label, tensor=True)
                except TypeError:
                    print(f"Can't process {exp_label} label")
                    continue
                fing_vec = shape_to_manyhot(fing, with_mute=model.with_mute)
                pred = model(torch.concat([torch.flatten(fing_vec), chord_vec], dim=-1))
                pred_bin = model.binarize(pred[None,:])
                completeness = completeness_metric(chord_vec, pred_bin, with_mute=model.with_mute)
                expected_pc = _midi_notes_from_fingering(exp_vec[:, :-1])
                pred_pc = _midi_notes_from_fingering(pred_bin[:, :, :-1])
                expected_notes = [m21.note.Note(a).name for a in expected_pc if a != 0]
                pred_notes = [m21.note.Note(a).name for a in pred_pc[0] if a != 0]
                pc_prec = pc_precision(expected_notes, pred_notes)
                pc_rec = pc_recall(expected_notes, pred_notes)
                pred_fing = TorchDataset.fingering_from_target_tensor(pred_bin, with_mute=model.with_mute)
                playability = Lo.anatomical_score(pred_fing)[0]
                if True:
                #if not (pred_bin == exp_vec).all():
                    dico = {'file': row['filename'],
                            'measure': row['measure'],
                            'previous_fingering': fing,
                            'previous_label': label,
                            'expected_label': exp_label,
                            'expected_fingering': exp_fing,
                            'pred': pred_fing,
                            'expected_notes': str(expected_notes),
                            'pred_notes': str(pred_notes),
                            'pc precision': pc_prec,
                            'pc recall': pc_rec,
                            'playability': playability,
                            }
                    out_list.append(pd.DataFrame(dico, index=[0]))
            out_df = pd.concat(out_list, ignore_index=True)
            out_df.to_csv(args.save_pred)
        else:
            if args.verbose:
                print("Testing the model on a single query.")
                print(f"Previous fingering is: {args.previous_fingering}")
                print(f"and requested chord label is {args.chord_label}.")
            x = torch.cat([shape_to_manyhot(args.previous_fingering,
                with_mute=model.with_mute).flatten(),
                           get_vector_representation(args.chord_label, tensor=True)])
            y_hat = model(x)
            max_tensor = torch.max(torch.unflatten(y_hat, 0, 
                        (-1, model.num_frets)), dim=-1).values
            pred_bin = torch.where(torch.unflatten(y_hat, 0, 
                        (-1, model.num_frets)) == max_tensor[:, None], 1, 0)
            if args.verbose:
                print("The model suggests the following fingering:")
            print(TorchDataset.fingering_from_target_tensor(pred_bin, with_mute=model.with_mute))
    return 0


if __name__ == '__main__':
    parser = ArgumentParser(description="Helper script for testing lightning module.")
    parser.add_argument('-s', '--sourcepath', type=str, required=True,
            help="Path to model checkpoint(s) to load.")
    parser.add_argument('-T', '--full-test', action='store_true',
            help="Run the whole testing loop.")
    parser.add_argument('-d', '--data', type=str,
            default="/home/alexandre/PhD/chord-shape-predictor/MSB-test_chordpairs.csv",
            help="Path to the test chordpairs csv.")
    parser.add_argument('--save-pred', type=str,
            help="Test on all the test dataset and save errors in a csv file.")
    parser.add_argument('-l', '--label', action='store_true',
            help="Use the baseline model with only the chordlabel.")
    parser.add_argument('--multilayer', action='store_true',
            help="Load a multilayer model.")
    parser.add_argument('--strict', action='store_true',
            help="Drop duplicates from test set on filename, nextchord and nextposition.")
    parser.add_argument('--stricter', action='store_true',
            help="Drop duplicates from test set on nextchord and nextposition.")
    parser.add_argument('--strictest', action='store_true',
            help="Drop duplicates from test set on nextposition.")
    parser.add_argument('-B', '--batch-size', type=int,
            default=32,
            help="Batch Size for test dataloader.")
    parser.add_argument('-pF', '--previous-fingering', type=str,
            default="x.0.2.2.1.0",
            help="string representation of the previous chord fingering.")
    parser.add_argument('-cl', '--chord-label', type=str,
            default="F",
            help="Chord label for the next chord to predict.")
    parser.add_argument('-v', '--verbose', action='store_true',
            help="Enable verbose output.")
    sys.exit(main(parser))


