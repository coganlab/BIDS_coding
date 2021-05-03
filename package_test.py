#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import BIDS_converter.data2bids as d2b
import preprocess as prep
import os
import shutil

def test_1():

    os.mkdir("BIDS_converter/testing/BIDS")
    d2b.Data2Bids(input_dir='BIDS_converter/testing/D48', output_dir='BIDS_converter/testing/BIDS').run()

    xlist =[]

    for x in os.listdir('BIDS_converter/testing/BIDS/sub-D48'):
        #os.close(x)
        xlist.append(x)

    while os.path.isdir("BIDS_converter/testing/BIDS"):
        shutil.rmtree("BIDS_converter/testing/BIDS", ignore_errors=True)

    return xlist