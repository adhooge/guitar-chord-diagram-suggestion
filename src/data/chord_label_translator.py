# This script generates a chord dictionary of the form 'chord_label : (bass_pc,chord_pcs)'
# For example : 'Am7' : (9, [9, 0, 4, 7])
# The dictionary covers 95% of the chord labels found in MSB


import json
import numpy as np
import torch

pc_dict = {'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}

def generate_chord_dict():
    chord_dict = {}
    for pc_name,pc in pc_dict.items():
        # major chords
        chord_dict[pc_name]=(pc,[pc,(pc+4)%12,(pc+7)%12]) # major chord
        chord_dict[pc_name+'b']=((pc+11)%12,[(pc+11)%12,(pc+11+4)%12,(pc+11+7)%12])
        chord_dict[pc_name+'#']=((pc+1)%12,[(pc+1)%12,(pc+1+4)%12,(pc+1+7)%12])
        # minor chords
        chord_dict[pc_name+'m']=(pc,[pc,(pc+3)%12,(pc+7)%12])
        chord_dict[pc_name+'bm']=((pc+11)%12,[(pc+11)%12,(pc+11+3)%12,(pc+11+7)%12])
        chord_dict[pc_name+'#m']=((pc+1)%12,[(pc+1)%12,(pc+1+3)%12,(pc+1+7)%12])
        # power chords
        chord_dict[pc_name+'5']=(pc,[pc,(pc+7)%12])
        chord_dict[pc_name+'b5']=((pc+11)%12,[(pc+11)%12,(pc+11+7)%12])
        chord_dict[pc_name+'#5']=((pc+1)%12,[(pc+1)%12,(pc+1+7)%12])
        # sus2 chords : Asus2
        chord_dict[pc_name+'sus2']=(pc,[pc,(pc+2)%12,(pc+7)%12])
        chord_dict[pc_name+'bsus2']=((pc+11)%12,[(pc+11)%12,(pc+11+2)%12,(pc+11+7)%12])
        chord_dict[pc_name+'#sus2']=((pc+1)%12,[(pc+1)%12,(pc+1+2)%12,(pc+1+7)%12])
        # sus4 chords : Dsus4
        chord_dict[pc_name+'sus4']=(pc,[pc,(pc+5)%12,(pc+7)%12])
        chord_dict[pc_name+'bsus4']=((pc+11)%12,[(pc+11)%12,(pc+11+5)%12,(pc+11+7)%12])
        chord_dict[pc_name+'#sus4']=((pc+1)%12,[(pc+1)%12,(pc+1+5)%12,(pc+1+7)%12])
        # maj 7 #11 chords : Fmaj7(#11)
        chord_dict[pc_name+'maj7(#11)']=(pc,[pc,(pc+6)%12,(pc+4)%12,(pc+7)%12,(pc+11)%12])
        chord_dict[pc_name+'bmaj7(#11)']=((pc+11)%12,[(pc+11)%12,(pc+11+6)%12,(pc+11+4)%12,(pc+11+7)%12],(pc+11+11)%12)
        chord_dict[pc_name+'#maj7(#11)']=((pc+1)%12,[(pc+1)%12,(pc+1+6)%12,(pc+1+4)%12,(pc+1+7)%12],(pc+1+11)%12)
        # add#11 chords : Cadd#11
        chord_dict[pc_name+'add#11']=(pc,[pc,(pc+6)%12,(pc+4)%12,(pc+7)%12])
        chord_dict[pc_name+'badd#11']=((pc+11)%12,[(pc+11)%12,(pc+11+6)%12,(pc+11+4)%12,(pc+11+7)%12])
        chord_dict[pc_name+'#add#11']=((pc+1)%12,[(pc+1)%12,(pc+1+6)%12,(pc+1+4)%12,(pc+1+7)%12])
        # add11 chords : Gadd11
        chord_dict[pc_name+'add11']=(pc,[pc,(pc+5)%12,(pc+4)%12,(pc+7)%12])
        chord_dict[pc_name+'badd11']=((pc+11)%12,[(pc+11)%12,(pc+11+5)%12,(pc+11+4)%12,(pc+11+7)%12])
        chord_dict[pc_name+'#add11']=((pc+1)%12,[(pc+1)%12,(pc+1+5)%12,(pc+1+4)%12,(pc+1+7)%12])
        # madd11 chords : Bmadd11
        chord_dict[pc_name+'madd11']=(pc,[pc,(pc+5)%12,(pc+3)%12,(pc+7)%12])
        chord_dict[pc_name+'bmadd11']=((pc+11)%12,[(pc+11)%12,(pc+11+5)%12,(pc+11+3)%12,(pc+11+7)%12])
        chord_dict[pc_name+'#madd11']=((pc+1)%12,[(pc+1)%12,(pc+1+5)%12,(pc+1+3)%12,(pc+1+7)%12])
        # add9 chords : Cadd9
        chord_dict[pc_name+'add9']=(pc,[pc,(pc+2)%12,(pc+4)%12,(pc+7)%12])
        chord_dict[pc_name+'badd9']=((pc+11)%12,[(pc+11)%12,(pc+11+2)%12,(pc+11+4)%12,(pc+11+7)%12])
        chord_dict[pc_name+'#add9']=((pc+1)%12,[(pc+1)%12,(pc+1+2)%12,(pc+1+4)%12,(pc+1+7)%12])
        # madd9 chords : Emadd9
        chord_dict[pc_name+'madd9']=(pc,[pc,(pc+2)%12,(pc+3)%12,(pc+7)%12])
        chord_dict[pc_name+'bmadd9']=((pc+11)%12,[(pc+11)%12,(pc+11+2)%12,(pc+11+3)%12,(pc+11+7)%12])
        chord_dict[pc_name+'#madd9']=((pc+1)%12,[(pc+1)%12,(pc+1+2)%12,(pc+1+3)%12,(pc+1+7)%12])
        # seventh chords : A7
        chord_dict[pc_name+'7']=(pc,[pc,(pc+4)%12,(pc+7)%12,(pc+10)%12])
        chord_dict[pc_name+'b7']=((pc+11)%12,[(pc+11)%12,(pc+11+4)%12,(pc+11+7)%12,(pc+11+10)%12])
        chord_dict[pc_name+'#7']=((pc+1)%12,[(pc+1)%12,(pc+1+4)%12,(pc+1+7)%12,(pc+1+10)%12])
        # augmented dominant seventh chords : F7(#5)
        chord_dict[pc_name+'7(#5)']=(pc,[pc,(pc+4)%12,(pc+8)%12,(pc+10)%12])
        chord_dict[pc_name+'b7(#5)']=((pc+11)%12,[(pc+11)%12,(pc+11+4)%12,(pc+11+8)%12,(pc+11+10)%12])
        chord_dict[pc_name+'#7(#5)']=((pc+1)%12,[(pc+1)%12,(pc+1+4)%12,(pc+1+8)%12,(pc+1+10)%12])
        # 7sus4 chords : A7sus4
        chord_dict[pc_name+'7sus4']=(pc,[pc,(pc+5)%12,(pc+7)%12,(pc+10)%12])
        chord_dict[pc_name+'b7sus4']=((pc+11)%12,[(pc+11)%12,(pc+11+5)%12,(pc+11+7)%12,(pc+11+10)%12])
        chord_dict[pc_name+'#7sus4']=((pc+1)%12,[(pc+1)%12,(pc+1+5)%12,(pc+1+7)%12,(pc+1+10)%12])
        # 7sus9 chords : A7sus9
        chord_dict[pc_name+'7sus9']=(pc,[pc,(pc+2)%12,(pc+7)%12,(pc+10)%12])
        chord_dict[pc_name+'b7sus9']=((pc+11)%12,[(pc+11)%12,(pc+11+2)%12,(pc+11+7)%12,(pc+11+10)%12])
        chord_dict[pc_name+'#7sus9']=((pc+1)%12,[(pc+1)%12,(pc+1+2)%12,(pc+1+7)%12,(pc+1+10)%12])
        # dominant sharp ninth chords : C7(#9)
        chord_dict[pc_name+'7(#9)']=(pc,[pc,(pc+3)%12,(pc+4)%12,(pc+7)%12,(pc+10)%12])
        chord_dict[pc_name+'#7(b9)']=((pc+11)%12,[(pc+11)%12,(pc+11+3)%12,(pc+11+4)%12,(pc+11+7)%12,(pc+11+10)%12])
        chord_dict[pc_name+'#7(#9)']=((pc+1)%12,[(pc+1)%12,(pc+1+3)%12,(pc+1+4)%12,(pc+1+7)%12,(pc+1+10)%12])
        # 7b9 chords : C7(b9)
        chord_dict[pc_name+'7(b9)']=(pc,[pc,(pc+1)%12,(pc+4)%12,(pc+7)%12,(pc+10)%12])
        chord_dict[pc_name+'b7(b9)']=((pc+11)%12,[(pc+11)%12,(pc+11+1)%12,(pc+11+4)%12,(pc+11+7)%12,(pc+11+10)%12])
        chord_dict[pc_name+'#7(b9)']=((pc+1)%12,[(pc+1)%12,(pc+1+1)%12,(pc+1+4)%12,(pc+1+7)%12,(pc+1+10)%12])
        # dominant seventh add b13 chords : C7(b13)
        chord_dict[pc_name+'7(b13)']=(pc,[pc,(pc+8)%12,(pc+4)%12,(pc+7)%12,(pc+10)%12])
        chord_dict[pc_name+'b7(b13)']=((pc+11)%12,[(pc+11)%12,(pc+11+8)%12,(pc+11+4)%12,(pc+11+7)%12,(pc+11+10)%12])
        chord_dict[pc_name+'#7(b13)']=((pc+1)%12,[(pc+1)%12,(pc+1+8)%12,(pc+1+4)%12,(pc+1+7)%12,(pc+1+10)%12])
        # 9 chords : D9
        chord_dict[pc_name+'9']=(pc,[pc,(pc+2)%12,(pc+4)%12,(pc+7)%12,(pc+10)%12])
        chord_dict[pc_name+'b9']=((pc+11)%12,[(pc+11)%12,(pc+11+2)%12,(pc+11+4)%12,(pc+11+7)%12,(pc+11+10)%12])
        chord_dict[pc_name+'#9']=((pc+1)%12,[(pc+1)%12,(pc+1+2)%12,(pc+1+4)%12,(pc+1+7)%12,(pc+1+10)%12])
        # minor seventh chords : Em7
        chord_dict[pc_name+'m7']=(pc,[pc,(pc+3)%12,(pc+7)%12,(pc+10)%12])
        chord_dict[pc_name+'bm7']=((pc+11)%12,[(pc+11)%12,(pc+11+3)%12,(pc+11+7)%12,(pc+11+10)%12])
        chord_dict[pc_name+'#m7']=((pc+1)%12,[(pc+1)%12,(pc+1+3)%12,(pc+1+7)%12,(pc+1+10)%12])
        # minor sixth chords : Am6
        chord_dict[pc_name+'m6']=(pc,[pc,(pc+3)%12,(pc+7)%12,(pc+9)%12])
        chord_dict[pc_name+'bm6']=((pc+11)%12,[(pc+11)%12,(pc+11+3)%12,(pc+11+7)%12,(pc+11+9)%12])
        chord_dict[pc_name+'#m6']=((pc+1)%12,[(pc+1)%12,(pc+1+3)%12,(pc+1+7)%12,(pc+1+9)%12])
        # minor 9 chords : Em9
        chord_dict[pc_name+'m9']=(pc,[pc,(pc+2)%12,(pc+3)%12,(pc+7)%12,(pc+10)%12])
        chord_dict[pc_name+'bm9']=((pc+11)%12,[(pc+11)%12,(pc+11+2)%12,(pc+11+3)%12,(pc+11+7)%12,(pc+11+10)%12])
        chord_dict[pc_name+'#m9']=((pc+1)%12,[(pc+1)%12,(pc+1+2)%12,(pc+1+3)%12,(pc+1+7)%12,(pc+1+10)%12])
        # sixth chords : G6
        chord_dict[pc_name+'6']=(pc,[pc,(pc+4)%12,(pc+7)%12,(pc+9)%12])
        chord_dict[pc_name+'b6']=((pc+11)%12,[(pc+11)%12,(pc+11+4)%12,(pc+11+7)%12,(pc+11+9)%12])
        chord_dict[pc_name+'#6']=((pc+1)%12,[(pc+1)%12,(pc+1+4)%12,(pc+1+7)%12,(pc+1+9)%12])
        # major seventh chords : Gmaj7
        chord_dict[pc_name+'maj7']=(pc,[pc,(pc+4)%12,(pc+7)%12,(pc+11)%12])
        chord_dict[pc_name+'bmaj7']=((pc+11)%12,[(pc+11)%12,(pc+11+4)%12,(pc+11+7)%12,(pc+11+11)%12])
        chord_dict[pc_name+'#maj7']=((pc+1)%12,[(pc+1)%12,(pc+1+4)%12,(pc+1+7)%12,(pc+1+11)%12])
        # minor major seventh chords : Em(maj7)
        chord_dict[pc_name+'m(maj7)']=(pc,[pc,(pc+3)%12,(pc+7)%12,(pc+11)%12])
        chord_dict[pc_name+'bm(maj7)']=((pc+11)%12,[(pc+11)%12,(pc+11+3)%12,(pc+11+7)%12,(pc+11+11)%12])
        chord_dict[pc_name+'#m(maj7)']=((pc+1)%12,[(pc+1)%12,(pc+1+3)%12,(pc+1+7)%12,(pc+1+11)%12])
        # major seventh chords : C7M
        chord_dict[pc_name+'7M']=(pc,[pc,(pc+4)%12,(pc+7)%12,(pc+11)%12])
        chord_dict[pc_name+'b7M']=((pc+11)%12,[(pc+11)%12,(pc+11+4)%12,(pc+11+7)%12,(pc+11+11)%12])
        chord_dict[pc_name+'#7M']=((pc+1)%12,[(pc+1)%12,(pc+1+4)%12,(pc+1+7)%12,(pc+1+11)%12])
        # diminished seventh chords : Adim7
        chord_dict[pc_name+'dim7']=(pc,[pc,(pc+3)%12,(pc+6)%12,(pc+9)%12])
        chord_dict[pc_name+'bdim7']=((pc+9)%12,[(pc+11)%12,(pc+11+3)%12,(pc+11+6)%12,(pc+11+11)%12])
        chord_dict[pc_name+'#dim7']=((pc+1)%12,[(pc+1)%12,(pc+1+3)%12,(pc+1+6)%12,(pc+1+9)%12])

    # Inversions
    inverted_chord_dict = {}
    for chord_name,pcs in chord_dict.items():
        for inversion_pc_name,inversion_pc in pc_dict.items():
            inverted_chord_dict[chord_name+'/'+inversion_pc_name]=(inversion_pc,pcs[1])
            inverted_chord_dict[chord_name+'/'+inversion_pc_name+'b']=((inversion_pc+11)%12,pcs[1])
            inverted_chord_dict[chord_name+'/'+inversion_pc_name+'#']=((inversion_pc+1)%12,pcs[1])
    chord_dict = {**chord_dict, **inverted_chord_dict}
    return chord_dict

chord_dict = generate_chord_dict()

def get_chord_label_notes(chord_label):
    if chord_label in chord_dict :
        return chord_dict[chord_label]
    else :
        print('{} is not in the chord dictionary.'.format(chord_label))
        return None

def get_vector_representation(chord_label, tensor: bool = False):
    #'Am7' : (9, [9, 0, 4, 7]) : [0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,0,1,0,0,1,0,1,0,0]
    chord_tuple = get_chord_label_notes(chord_label)
    bass_vector = np.zeros(12) if not tensor else torch.zeros(12)
    bass_vector[chord_tuple[0]]=1
    other_notes_vector = np.zeros(12) if not tensor else torch.zeros(12)
    for n in chord_tuple[1]:
        other_notes_vector[n]=1
    return np.concatenate((bass_vector,other_notes_vector)) if not tensor else torch.concatenate((bass_vector, other_notes_vector))

def get_chord_label(chord_vector):
    assert len(chord_vector)==24, "chord_vector should be size 24 : {}".format(chord_vector)
    bass_vector = chord_vector[:12]
    assert np.count_nonzero(bass_vector==1)==1, "bass_vector should have exactly one digit to 1 : {}".format(bass_vector)
    other_notes_vector = chord_vector[12:]
    for chord_label_key,chord_tuple in chord_dict.items():
        # print('{}-{}'.format(chord_label_key,chord_tuple))
        bass_pc = chord_tuple[0]
        other_notes_pc_list = chord_tuple[1]
        dict_other_notes_vector = np.zeros(12)
        for n in other_notes_pc_list : dict_other_notes_vector[n]=1
        if bass_vector[bass_pc]==1 and np.array_equal(dict_other_notes_vector, other_notes_vector):
            return chord_label_key
    return 'chord symbol not found for {}'.format(chord_vector)
        

# print(get_chord_label_notes('Em'))

### Uncomment the following to compute the covering

# with open('msb_chord_label_set.json') as json_file:
#     frequency_dict = json.load(json_file)
#     total_label_number = 0
#     covered_label_number = 0
#     for chord,freq in frequency_dict.items():
#         total_label_number+=freq
#         if chord in chord_dict:
#             covered_label_number+=freq
#         else :
#             print('not covered : {} - {}'.format(chord,freq))
#     covering = covered_label_number/total_label_number
#     print("labels covered at {0:.0%}".format(covering))
