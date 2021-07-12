#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from BIDS_converter.data2bids import Data2Bids
import shutil
import os
import tarfile


def test_D52():
    os.makedirs("Data/Phoneme_Sequencing/BIDS", exist_ok=True)

    error = None
    files = None

    print("Unzipping: D52 201213 COGAN_PHONEMESEQUENCE.edf.tar.xz")

    with tarfile.open("Data/Phoneme_Sequencing/eeg_data/D52 201213 COGAN_PHONEMESEQUENCE.edf.tar.xz", mode="r:xz") as f:
        f.extractall(path="Data/Phoneme_Sequencing/sourcedata/D52")
    try:
        Data2Bids(input_dir='Data/Phoneme_Sequencing/sourcedata/D52', output_dir='Data/Phoneme_Sequencing/BIDS',
                  verbose=True).run()
        files = [x for x in os.listdir('Data/Phoneme_Sequencing/BIDS/sub-D0052')]
    except Exception as e:
        error = e
    finally:
        while os.path.isdir("Data/Phoneme_Sequencing/BIDS"):
            shutil.rmtree("Data/Phoneme_Sequencing/BIDS", ignore_errors=True)
        os.chmod("Data/Phoneme_Sequencing/sourcedata/D52/D52 201213 COGAN_PHONEMESEQUENCE.edf", 0o777)
        os.remove("Data/Phoneme_Sequencing/sourcedata/D52/D52 201213 COGAN_PHONEMESEQUENCE.edf")
        if error:
            raise error
        else:
            return files


def test_D48():
    os.makedirs("Data/Phoneme_Sequencing/BIDS", exist_ok=True)

    error = None
    files = None

    print("Unzipping: D48 200906 Cogan_PhonemeSequence_Session1.edf.tar.xz")

    with tarfile.open("Data/Phoneme_Sequencing/eeg_data/D48 200906 Cogan_PhonemeSequence_Session1.edf.tar.xz",
                      mode="r:xz") as f:
        f.extractall(path="Data/Phoneme_Sequencing/sourcedata/D48")

    print("Unzipping: D48 200908 Cogan_PhonemeSequence_Session2.edf.tar.xz")

    with tarfile.open("Data/Phoneme_Sequencing/eeg_data/D48 200908 Cogan_PhonemeSequence_Session2.edf.tar.xz",
                      mode="r:xz") as f:
        f.extractall(path="Data/Phoneme_Sequencing/sourcedata/D48")

    try:

        Data2Bids(input_dir='Data/Phoneme_Sequencing/sourcedata/D48', output_dir='Data/Phoneme_Sequencing/BIDS',
                  verbose=True).run()
        files = [x for x in os.listdir('Data/Phoneme_Sequencing/BIDS/sub-D0048')]
    except Exception as e:
        error = e
    finally:
        while os.path.isdir("Data/Phoneme_Sequencing/BIDS"):
            shutil.rmtree("Data/Phoneme_Sequencing/BIDS", ignore_errors=True)
        os.chmod("Data/Phoneme_Sequencing/sourcedata/D48/D48 200906 Cogan_PhonemeSequence_Session1.edf", 0o777)
        os.chmod("Data/Phoneme_Sequencing/sourcedata/D48/D48 200908 Cogan_PhonemeSequence_Session2.edf", 0o777)
        os.remove("Data/Phoneme_Sequencing/sourcedata/D48/D48 200906 Cogan_PhonemeSequence_Session1.edf")
        os.remove("Data/Phoneme_Sequencing/sourcedata/D48/D48 200908 Cogan_PhonemeSequence_Session2.edf")
        if error:
            raise error
        else:
            return files
