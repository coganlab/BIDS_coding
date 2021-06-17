#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from BIDS_converter.data2bids import Data2Bids
import shutil
import os
import tarfile

def test_1():

    os.makedirs("BIDS_converter/samples/BIDS",exist_ok=True)

<<<<<<< HEAD
    with tarfile.open("data.tar.xz") as f:
        f.extractall(members=[ tarinfo for tarinfo in f.getmembers() 
            if tarinfo.name.startswith("D52/")],path="BIDS_converter/samples")
=======
    with tarfile.open("test_data.tar.xz") as f:
        f.extractall(path="BIDS_converter/samples")
>>>>>>> d1d04efcc80dcd518685731b19f1dfa8fa75e538

    Data2Bids(input_dir='BIDS_converter/samples/D52', output_dir='BIDS_converter/samples/BIDS').run()

    xlist =[]

    for x in os.listdir('BIDS_converter/samples/BIDS/sub-D0052'):
        #os.close(x)
        xlist.append(x)

    while os.path.isdir("BIDS_converter/samples"):
        shutil.rmtree("BIDS_converter/samples", ignore_errors=True)

    return xlist

def test_2():

    os.makedirs("BIDS_converter/samples/BIDS",exist_ok=True)

<<<<<<< HEAD
    with tarfile.open("data.tar.xz") as f:
        f.extractall(members=[ tarinfo for tarinfo in f.getmembers() 
            if tarinfo.name.startswith("D48/")],path="BIDS_converter/samples")
=======
    with tarfile.open("test_data.tar.xz") as f:
        f.extractall(path="BIDS_converter/samples")
>>>>>>> d1d04efcc80dcd518685731b19f1dfa8fa75e538

    Data2Bids(input_dir='BIDS_converter/samples/D48', output_dir='BIDS_converter/samples/BIDS').run()

    xlist =[]

    for x in os.listdir('BIDS_converter/samples/BIDS/sub-D0048'):
        #os.close(x)
        xlist.append(x)

    while os.path.isdir("BIDS_converter/samples"):
        shutil.rmtree("BIDS_converter/samples", ignore_errors=True)

    return xlist
