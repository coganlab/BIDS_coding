#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from BIDS_converter.data2bids import Data2Bids
import shutil
import os
import tarfile
import pytest

src_path = "Data/Phoneme_Sequencing/sourcedata"
eeg_path = "Data/Phoneme_Sequencing/eeg_data"
BIDS_path = "Data/Phoneme_Sequencing/BIDS"


@pytest.mark.parametrize("sub", [
    "D52",
    "D48"
])
def test_sub(sub):
    os.makedirs(BIDS_path, exist_ok=True)

    error = None
    files = None

    my_list = [i for i in os.listdir(eeg_path) if i.startswith(sub)]
    assert my_list
    eeg_files = []
    for file in my_list:
        eeg_fullfile = os.path.join(eeg_path, file)
        print("Unizipping: {}".format(eeg_fullfile))
        eeg_files.append(file.rstrip(".tar.xz"))
        with tarfile.open(eeg_fullfile, mode="r:xz") as f:
            f.extractall(path=os.path.join(src_path, sub))
    try:
        d2b = Data2Bids(input_dir=os.path.join(src_path, sub),
                        output_dir=BIDS_path,
                        stim_dir=os.path.join(src_path, "stimuli"),
                        overwrite=True,
                        verbose=True)
        d2b.run()
        part_match_z = d2b.part_check(eeg_files[0])[1]
        files = [x for x in os.listdir(os.path.join(BIDS_path,
                                                    "sub-" + part_match_z))]
    except Exception as e:
        error = e
    finally:
        while os.path.isdir(BIDS_path):
            shutil.rmtree(BIDS_path, ignore_errors=True)
        for file in eeg_files:
            eeg_full_path = os.path.join(src_path, sub, file)
            os.chmod(eeg_full_path, 0o777)
            os.remove(eeg_full_path)
        if error:
            raise error
        else:
            return files

"""
def test_D48():
    os.makedirs("Data/Phoneme_Sequencing/BIDS", exist_ok=True)

    error = None
    files = None

    print("Unzipping: D48 200906 Cogan_PhonemeSequence_Session1.edf.tar.xz")

    with tarfile.open(
            "Data/Phoneme_Sequencing/eeg_data/D48 200906 Cogan_PhonemeSequence_Session1.edf.tar.xz",
            mode="r:xz") as f:
        f.extractall(path="../Data/Phoneme_Sequencing/sourcedata/D48")

    print("Unzipping: D48 200908 Cogan_PhonemeSequence_Session2.edf.tar.xz")

    with tarfile.open(
            "Data/Phoneme_Sequencing/eeg_data/D48 200908 Cogan_PhonemeSequence_Session2.edf.tar.xz",
            mode="r:xz") as f:
        f.extractall(path="Data/Phoneme_Sequencing/sourcedata/D48")

    try:

        Data2Bids(input_dir='Data/Phoneme_Sequencing/sourcedata/D48', output_dir='Data/Phoneme_Sequencing/BIDS',
                  stim_dir="Data/Phoneme_Sequencing/sourcedata/stimuli", overwrite=True, verbose=True).run()
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
"""
