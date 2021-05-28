#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from BIDS_coding.BIDS_converter.data2bids import Data2Bids
import os
import shutil

def test_1():

    try:
        os.mkdir("BIDS_converter/samples/BIDS")
    except FileExistsError:
        pass
    Data2Bids(input_dir='BIDS_converter/samples/D52', output_dir='BIDS_converter/samples/BIDS').run()

    xlist =[]

    for x in os.listdir('BIDS_converter/samples/BIDS/sub-D0052'):
        #os.close(x)
        xlist.append(x)

    while os.path.isdir("BIDS_converter/samples/BIDS"):
        shutil.rmtree("BIDS_converter/samples/BIDS", ignore_errors=True)

    return xlist

def test_2():

    try:
        os.mkdir("BIDS_converter/samples/BIDS")
    except FileExistsError:
        pass
    Data2Bids(input_dir='BIDS_converter/samples/D48', output_dir='BIDS_converter/samples/BIDS').run()

    xlist =[]

    for x in os.listdir('BIDS_converter/samples/BIDS/sub-D0048'):
        #os.close(x)
        xlist.append(x)

    while os.path.isdir("BIDS_converter/samples/BIDS"):
        shutil.rmtree("BIDS_converter/samples/BIDS", ignore_errors=True)

    return xlist
