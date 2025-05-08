import lightning as L
from cds.config import NUM_FRETS, NUM_STRINGS, PITCH_CLASSES
from cds.data.dataset import TorchDataset
from cds.model.base_model import FingeringPredictor, FingeringPredictorBaseline
from cds.model.multilayer_model import MultiLayerFingeringPredictor, MultilayerBaseline
from argparse import ArgumentParser
import sys
from torch.utils.data import DataLoader
from lightning.pytorch import seed_everything
from lightning.pytorch.callbacks import ModelCheckpoint
from lightning.pytorch.callbacks.early_stopping import EarlyStopping
from lightning.pytorch.loggers import TensorBoardLogger
import pathlib
from datetime import datetime

LOGDIR = "logs/"
BATCHSIZE = 32
WORKERS = 7

def main(parser: ArgumentParser) -> int:
    args = parser.parse_args()
    seed_everything(args.seed, workers=True)
    # Datasets and Dataloaders
    dataset = TorchDataset(df_path=args.dataframe, df = None,
            augment=args.augment)
    valset = TorchDataset(df_path=args.validation_set, df=None)
    dataloader = DataLoader(dataset, batch_size=BATCHSIZE, num_workers=WORKERS, shuffle=True)
    valloader = DataLoader(valset, batch_size=BATCHSIZE, num_workers=WORKERS)
    # Lightning Trainer
    name = "{version}-{epoch}-{val_loss:.3f}-"
    name += args.ckpt_name
    ckpt_callback = ModelCheckpoint(dirpath=pathlib.Path(LOGDIR) / args.name, every_n_epochs=1,
            filename=name)
    early_stopping_cb = EarlyStopping(monitor="Val/loss", min_delta=0.001, patience=2, verbose=True,
            mode="min")
    logger = TensorBoardLogger(save_dir=LOGDIR, name=args.name)
    trainer = L.Trainer(callbacks=[ckpt_callback, early_stopping_cb],
            deterministic=True, logger=logger, detect_anomaly=False)
    # Model init
    if args.multilayer:
        if args.label_only:
            model = MultilayerBaseline(learning_rate=args.learning_rate,
                    hidden_layers_sizes=args.multilayer)
        else:
            model = MultiLayerFingeringPredictor(learning_rate=args.learning_rate,
                    hidden_layers_sizes=args.multilayer)
    else:
        if args.label_only:
            model = FingeringPredictorBaseline(learning_rate=args.learning_rate)
        else:
            model = FingeringPredictor(learning_rate=args.learning_rate)
    # Training
    trainer.fit(model=model, train_dataloaders=dataloader,
            val_dataloaders=valloader)
    return 0


if __name__ == '__main__':
    parser = ArgumentParser(description="Script to train a Lightning model.")
    parser.add_argument('-df', '--dataframe', type=str,
            default="data/mySongBook/train/mySongBook-chordpairs-train-split_1111.csv")
    parser.add_argument("-vdf", "--validation-set", type=str,
            default="data/mySongBook/val/mySongBook-chordpairs-val-split_1111.csv")
    parser.add_argument('--learning-rate', type=float, default=0.001,
            help="Learning rate for implemented models.")
    parser.add_argument('--augment', action='store_true',
            help="Train with data augmentation.")
    parser.add_argument('-l', '--label-only', action="store_true",
            help="Train the baseline model that only uses label information.")
    parser.add_argument('-n', '--name', type=str, required=True,
            help="Name to give to the model trained.")
    parser.add_argument('--ckpt-name', type=str,
            default=datetime.today().strftime("%Y-%m-%d_%H-%M-%S"),
            help="String to add into checkpoint name.")
    parser.add_argument('--multilayer', nargs='+', type=int,
            help="Use the multilayer model. Optional additional hidden layer sizes can be provided.")
    parser.add_argument('-s', '--seed', type=int, default=2222)
    parser.add_argument('-vt', '--verbose-test', action='store_true')
    sys.exit(main(parser))
