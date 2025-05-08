# Guitar Chord Diagram Suggestion for Western Popular Music

Public repository of the implementation of a Guitar Diagram Suggestion system, as presented to
SMC 2024. If you use this repository for anything research-related, please cite the corresponding paper:

```BibTex
@inproceedings{dhoogeDiagram2024,
  TITLE = {{Guitar Chord Diagram Suggestion for Western Popular Music}},
  AUTHOR = {D'Hooge, Alexandre and Bigo, Louis and D{\'e}guernel, Ken and Martin, Nicolas},
  URL = {https://hal.science/hal-04575300},
  BOOKTITLE = {{Sound and Music Computing Conference}},
  ADDRESS = {Porto, Portugal},
  YEAR = {2024},
  MONTH = Jul,
  KEYWORDS = {Guitar Tablatures ; Chords ; Composition Assistee par Ordinateur ; Musique assist{\'e}e par ordinateur},
  HAL_ID = {hal-04575300},
  HAL_VERSION = {v1},
}
```

If you are just looking for a __quick demo__, you should probably go [here](https://huggingface.co/spaces/adhooge/guitar-chord-diagram-suggestion).

## Setup

You will need a Python 3.10 environment for running this repository.
You can prepare a setup the way I usually do, which is:

```
python3.10 -m venv env
source env/bin/activate
pip install -r requirements.txt
```

## Data Preparation

### Use the pre-computed data

If you don't have your own dataset, you can simply use the data we used in the paper.
To avoid unnecessary computation, we provide directly the chord information for
both [mySongBook](https://mysongbook.com) and [DadaGP](https://zenodo.org/records/5624597).
Everything necessary is in the `data/` folder.

### Use your own data or recompute DadaGP

**I would not recommend reprocessing the whole dataset as it is very long.**
**The explanations are provided  so that you can adapt it to your own data if necessary.**

 Besides, the script assumes that the 
files from DadaGP were all converted to `.gp` (the latest GuitarPro8 format), tracks split into separate files
and then all files unzipped to extract the internal `.gpif` files. The first two steps can 
be automated with the GuitarPro software, the latter with a simple bash script, but I don't provide the code for that here. 

To be fully transparent, the code for processing the dataset is nonetheless available on this repository. 

The first step is to identify in the dataset the measures that contain chord diagrams (~2hours). 
```
python cds/data/extract_chorded_measures.py
```

You'll have to set the path to your DadaGP dataset. 
This will generate one `.csv` file per DadaGP track, containing information about the chords. One row 
looks like that: 

| id | File | Measure | Duration | Chords | Offsets | Shapes |
|----|------|---------|----------|--------|---------|--------|
| 669| 3 Doors Down - Be Like That (2)-Track 2.gpif | 31 | 4 | ['G', 'Dsus2'] | [0.0, 2.5] | ['3.2.0.0.3.3', 'x.x.0.2.3.0'] | 

Once all the files have been processed, you will also obtain a big 20MB `dadaGP_chords.csv` file compiling all 
subfiles into one. It's saved to disk just in case but it's actually 
safer to process DadaGP files individually since there are so many.

The `.csv` files are then processed to make pairs of diagrams:
```
python cds/data/make_chord_pairs.py -S <path/to/csv/files>  
```

This will generate new `.csv` files. The most important ones are `chordpairs`, you have one for the full dataset, and three for train/val/test. 


## Model Training

We provide checkpoints of the models we trained for the paper (in the `logs/` folder), but you can reproduce the 
training procedure or train your own model using the script `cds/train.py`

```
python -m cds.train -n <a name for the trained model>
```

It will create a new subfolder in `logs/` with your best checkpoint as well as some info about training.

## Testing

You can reproduce the results of the paper with the provided checkpoints (or your own) by
running `cds/test.py`.

```
python -m cds.test -s <path/to/ckpt> -T 
```

### Getting stats on data

In the paper, we provide statistics for the features on the test data to get 
a reference.
You can reproduce this with `cds/data/stats_on_df-script.py`.
