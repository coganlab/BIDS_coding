#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from BIDS_converter.data2bids import Data2Bids
import shutil
import os
import tarfile

def test_1():

    os.makedirs("Data/Phoneme_Sequencing/BIDS",exist_ok=True)

    with tarfile.open("Data/Phoneme_Sequencing/eeg_data/D52 201213 COGAN_PHONEMESEQUENCE.edf.tar.xz") as f:
        f.extractall(path="Data/Phoneme_Sequencing/sourcedata/D52")

    Data2Bids(input_dir='Data/Phoneme_Sequencing/D52', output_dir='Data/Phoneme_Sequencing/BIDS').run()

    xlist =[]

    for x in os.listdir('Data/Phoneme_Sequencing/BIDS/sub-D0052'):
        #os.close(x)
        xlist.append(x)

    while os.path.isdir("Data/Phoneme_Sequencing/BIDS"):
        shutil.rmtree("Data/Phoneme_Sequencing/BIDS", ignore_errors=True)

    return xlist

def test_2():

    os.makedirs("Data/Phoneme_Sequencing/BIDS",exist_ok=True)

    with tarfile.open("Data/Phoneme_Sequencing/eeg_data/D48 200906 Cogan_PhonemeSequence_Session1.edf.tar.xz") as f:
        f.extractall(path="Data/Phoneme_Sequencing/sourcedata/D48")
    with tarfile.open("Data/Phoneme_Sequencing/eeg_data/D48 200908 Cogan_PhonemeSequence_Session2.edf.tar.xz") as f:
        f.extractall(path="Data/Phoneme_Sequencing/sourcedata/D48")

    Data2Bids(input_dir='Data/Phoneme_Sequencing/sourcedata/D48', output_dir='Data/Phoneme_Sequencing/BIDS').run()

    xlist =[]

    for x in os.listdir('Data/Phoneme_Sequencing/BIDS/sub-D0048'):
        #os.close(x)
        xlist.append(x)

    while os.path.isdir("Data/Phoneme_Sequencing/BIDS"):
        shutil.rmtree("Data/Phoneme_Sequencing/BIDS", ignore_errors=True)

    return xlist
