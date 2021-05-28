#!/usr/bin/env python3
# -*- coding: utf-8 -*-



from BIDS_converter.data2bids import Data2Bids
#Data2Bids = BIDS_converter.data2bids.Data2Bids
import shutil
import os

def test_1():

    
    os.makedirs("BIDS_converter/samples/BIDS",exist_ok=True)
    Data2Bids(input_dir='BIDS_converter/samples/D52', output_dir='BIDS_converter/samples/BIDS').run()

    xlist =[]

    for x in os.listdir('BIDS_converter/samples/BIDS/sub-D0052'):
        #os.close(x)
        xlist.append(x)

    while os.path.isdir("BIDS_converter/samples/BIDS"):
        shutil.rmtree("BIDS_converter/samples/BIDS", ignore_errors=True)

    return xlist

def test_2():

    os.makedirs("BIDS_converter/samples/BIDS",exist_ok=True)

    Data2Bids(input_dir='BIDS_converter/samples/D48', output_dir='BIDS_converter/samples/BIDS').run()

    xlist =[]

    for x in os.listdir('BIDS_converter/samples/BIDS/sub-D0048'):
        #os.close(x)
        xlist.append(x)

    while os.path.isdir("BIDS_converter/samples/BIDS"):
        shutil.rmtree("BIDS_converter/samples/BIDS", ignore_errors=True)

    return xlist
