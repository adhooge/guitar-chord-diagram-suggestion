from torch import optim, nn, mean
import torch
import lightning as L
from typing import Any
from pytorch_lightning.utilities.types import STEP_OUTPUT, OptimizerLRScheduler
from src.config import NUM_FRETS, NUM_STRINGS, PITCH_CLASSES, PLAYABILITY_THRESHOLD
import src.config as C
from torchmetrics import Accuracy, Precision, Recall, F1Score
from src.data.dataset import TorchDataset
from src.model.losses import pitch_class_loss, completeness_metric, open_chord_metric, playability_metric
import src.model.losses as Lo
import music21 as m21

class FingeringPredictor(L.LightningModule):
    def __init__(self, span_loss_coeff: float = 0.0, with_mute: bool = False, 
            learning_rate: float = 1e-3,
            *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.save_hyperparameters()
        self.with_mute = with_mute
        self.num_frets = NUM_FRETS + 1 if with_mute else NUM_FRETS
        self.model = nn.Linear((self.num_frets*NUM_STRINGS) + 2*PITCH_CLASSES,
                out_features=(NUM_STRINGS*self.num_frets))
        self.activation = nn.Sigmoid()
        self.pc_loss = pitch_class_loss
        self.loss = nn.BCELoss()
        self.span_loss = Lo.hand_span_loss
        self.oc_metric = open_chord_metric
        self.acc = Accuracy(task="binary")
        self.prec = Precision(task="binary")
        self.rec = Recall(task="binary")
        self.sf_prec = Lo.stringfret_precision
        self.sf_rec = Lo.stringfret_recall
        self.sf_f1 = Lo.stringfret_f1
        self.lr = learning_rate
        self.f1 = F1Score(task="binary")
        self.sf_exactness = Lo.stringwise_exactness
        self.playability = playability_metric
        self.completeness = completeness_metric
        self.span_loss_coeff = span_loss_coeff

    def forward(self, x) -> Any:
        z = self.model(x)
        y_hat = self.activation(z) # [B, NUM_FRETS*NUM_STRINGS]
        if not self.with_mute:
            return y_hat
        if x.ndim == 2:
            y_hat = nn.functional.normalize(y_hat.view((x.size()[0], NUM_STRINGS, self.num_frets)),
                    p=1, dim=2).flatten(start_dim=1)
        else:
            y_hat = nn.functional.normalize(y_hat.view((NUM_STRINGS, self.num_frets)),
                    p=1, dim=1).flatten()
        return y_hat

    def training_step(self, batch, batch_idx, *args: Any, **kwargs: Any) -> STEP_OUTPUT:
        x, y = batch
        y_hat = self(x)
        loss = self.loss(y_hat, y)
        if self.span_loss_coeff > 0 :
            span_loss = self.span_loss(torch.unflatten(y_hat, dim=1, sizes=(NUM_STRINGS, self.num_frets)),
                    with_mute=self.with_mute)
            loss = loss + self.span_loss_coeff*span_loss
            self.log("Train/span-loss", span_loss, prog_bar=True)
        self.log("Train/loss", loss, prog_bar=True)
        return loss

    def validation_step(self, batch, batch_idx, *args: Any, **kwargs: Any) -> STEP_OUTPUT:
        x, y = batch
        y_hat = self(x)
        loss = self.loss(y_hat, y)
        if self.span_loss_coeff > 0 :
            span_loss = self.span_loss(torch.unflatten(y_hat, dim=1, sizes=(NUM_STRINGS, self.num_frets)),
                    with_mute=self.with_mute)
            loss = loss + self.span_loss_coeff*span_loss
            self.log("Val/span-loss", span_loss, prog_bar=True)
        self.log("Val/loss", loss, prog_bar=True)
        self.log("val_loss", loss, prog_bar=False)
        return loss

    def binarize(self, tensor) -> torch.Tensor:
        if self.with_mute:
            max_tensor = torch.max(torch.unflatten(tensor, 1, 
                (-1, self.num_frets)), dim=-1).values
            pred_bin = torch.where(torch.unflatten(tensor, 1, 
                (-1, self.num_frets)) == max_tensor[:, :, None], 1, 0)
        else:
            pred_bin = tensor > 0.5
            pred_bin = torch.unflatten(pred_bin, 1, (-1, self.num_frets))
        return pred_bin

    def test_step(self, batch, batch_idx, *args: Any, **kwargs: Any) -> STEP_OUTPUT:
        x, y = batch
        batch_size = len(y)
        y_hat = self(x)
        loss = self.loss(y_hat, y)
        acc = self.acc(y_hat, y)
        rec = self.rec(y_hat, y)
        prec = self.prec(y_hat, y)
        f1 = self.f1(y_hat, y)
        pred_bin = self.binarize(y_hat)
        fingerings = pred_bin.view((y_hat.size()[0], NUM_STRINGS, self.num_frets))
        expected = y.view((y_hat.size()[0], NUM_STRINGS, self.num_frets))
        expected_notes = Lo._midi_notes_from_fingering_batchwise(expected[:, :,:-1])
        expected_notes = [[m21.note.Note(a).name for a in expected_notes[i] if a !=0] for i in range(len(expected_notes))]
        pred_notes = Lo._midi_notes_from_fingering_batchwise(pred_bin[:, :, :-1])
        pred_notes = [[m21.note.Note(a).name for a in pred_notes[i] if a !=0] for i in range(len(pred_notes))]
        pc_prec = torch.Tensor([Lo.pc_precision(expected_notes[i], pred_notes[i]) for i in range(len(expected_notes))])
        pc_rec = torch.Tensor([Lo.pc_recall(expected_notes[i], pred_notes[i]) for i in range(len(expected_notes))])
        oc = self.oc_metric(fingerings, expected)
        sw_exact = self.sf_exactness(fingerings, expected)
        sf_prec = self.sf_prec(fingerings, expected, with_mute=self.with_mute)
        sf_rec = self.sf_rec(fingerings, expected, with_mute=self.with_mute)
        sf_f1 = self.sf_f1(fingerings, expected, with_mute=self.with_mute)
        pc_f1 = torch.div(2*pc_prec*pc_rec, pc_prec+pc_rec)
        pc_f1 = torch.nan_to_num(pc_f1, nan=0)
        diagrams = [TorchDataset.fingering_from_target_tensor(pred_bin.view((batch_size, NUM_STRINGS, self.num_frets))[i], with_mute=self.with_mute) for i in range(batch_size)]
        diagrams_previous = [TorchDataset.fingering_from_source_tensor(x[i], with_mute=self.with_mute) for i in range(batch_size)]
        playability = torch.Tensor([Lo.anatomical_score(diagrams[i])[0] for i in range(len(diagrams))])
        unplayable = playability < PLAYABILITY_THRESHOLD
        best_fingerings = [Lo.anatomical_score(diagrams[i])[1] for i in range(len(diagrams))]
        best_fingerings_previous = [Lo.anatomical_score(diagrams_previous[i])[1] for i in range(batch_size)]
        transition_costs = torch.Tensor([Lo.transition_cost(best_fingerings_previous[i],
                                                            best_fingerings[i]) for i in range(batch_size)])
        c_r_muted = [Lo.ratio_muted_strings(current_diag) for current_diag in diagrams_previous]
        c_r_open = [Lo.ratio_open_strings(current_diag) for current_diag in diagrams_previous]
        c_num_strings = [Lo.num_strings_played(current_diag) for current_diag in diagrams_previous]
        c_centroid = [Lo.string_centroid(current_diag) for current_diag in diagrams_previous]
        c_r_unique = [Lo.ratio_unique_notes(current_diag) for current_diag in diagrams_previous]
        n_r_muted = [Lo.ratio_muted_strings(current_diag) for current_diag in diagrams]
        n_r_open = [Lo.ratio_open_strings(current_diag) for current_diag in diagrams]
        n_num_strings = [Lo.num_strings_played(current_diag) for current_diag in diagrams]
        n_centroid = [Lo.string_centroid(current_diag) for current_diag in diagrams]
        n_r_unique = [Lo.ratio_unique_notes(current_diag) for current_diag in diagrams]
        r_muted_diff = [abs(c_r_muted[i] - n_r_muted[i]) for i in range(batch_size)]
        r_open_diff = [abs(c_r_open[i] - n_r_open[i]) for i in range(batch_size)]
        num_strings_diff = [abs(c_num_strings[i] - n_num_strings[i]) for i in range(batch_size)]
        centroid_diff = [abs(c_centroid[i] - n_centroid[i]) for i in range(batch_size)]
        r_unique_diff = [abs(c_r_unique[i] - n_r_unique[i]) for i in range(batch_size)]
        self.log("Test/loss", loss, prog_bar=False)
        self.log("Test/acc", acc)
        self.log("Test/rec", rec)
        self.log("Test/prec", prec)
        self.log("Test/SF rec", sf_rec.mean())
        self.log("Test/SF prec", sf_prec.mean())
        self.log("Test/SF F1", sf_f1.mean())
        self.log("Test/PC F1", pc_f1.mean())
        self.log("Test/F1", f1)
        self.log("Test/exactness", self.exact_acc(pred_bin, y))
        self.log("Test/StringExactness", sw_exact.mean())
        self.log("Test/PC-Recall", pc_rec.mean())
        self.log("Test/playability", playability.mean())
        self.log("Test/unplayable", unplayable.mean(dtype=torch.float32))
        self.log("Test/open-closed", oc.mean(dtype=torch.float32))
        self.log("Test/PC-Precision", pc_prec.mean())
        self.log('Test/transition_cost', transition_costs.mean())
        self.log('Test/ratio_muted', torch.Tensor(n_r_muted).mean())
        self.log('Test/ratio_open', torch.Tensor(n_r_open).mean())
        self.log('Test/num_strings', torch.Tensor(n_num_strings).mean())
        self.log('Test/centroid', torch.Tensor(n_centroid).mean())
        self.log('Test/ratio_unique_notes', torch.Tensor(n_r_unique).mean())
        self.log('Test/ratio_muted_diff', torch.Tensor(r_muted_diff).mean())
        self.log('Test/ratio_open_diff', torch.Tensor(r_open_diff).mean())
        self.log('Test/num_strings_diff', torch.Tensor(num_strings_diff).mean())
        self.log('Test/centroid_diff', torch.Tensor(centroid_diff).mean())
        self.log('Test/ratio_unique_notes_diff', torch.Tensor(r_unique_diff).mean())
        return loss

    def exact_acc(self, pred, target, threshold: float = 0.5):
        tmp = torch.eq(torch.flatten(pred,start_dim=1), target)
        return torch.mean(torch.all(tmp, dim=-1), dtype=torch.float16)
        
    def configure_optimizers(self) -> OptimizerLRScheduler:
        optimizer = optim.Adam(self.parameters(), lr=self.lr)
        return optimizer
        

class FingeringPredictorBaseline(FingeringPredictor):
    def __init__(self, learning_rate: float = 0.001, *args: Any, **kwargs: Any) -> None:
        super().__init__(learning_rate=learning_rate, **kwargs)
        self.model = nn.Linear(2*PITCH_CLASSES, self.num_frets*NUM_STRINGS)

    def forward(self, x) -> Any:
        # drop chord fingering info (first dim is batch size)
        if x.dim() > 1:
            x = x[:, -2*PITCH_CLASSES:]
        else:
            x = x[-2*PITCH_CLASSES:]
        z = self.model(x)
        y_hat = self.activation(z)
        return y_hat
