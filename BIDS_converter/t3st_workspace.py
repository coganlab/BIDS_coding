#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import json
import gzip


if __name__ == '__main__':

    with open('config.json', 'r') as fst:
        config = json.load(fst)
    headers=np.zeros(194)
    files = ["/home/sbf/Desktop/git/BIDS_coding/BIDS_converter/testing/D52/D52_Session001_PhonemeSequencing_201213.ieeg.dat.gz",
                "/home/sbf/Desktop/share/workspace/D52_PhonemeSequencing_201213.ieeg.dat"]
    for file in files:
        try:
            if file.endswith(".gz"):
                with gzip.open(file,'rb',config["compressLevel"]) as f:
                    #f_in = gzip.GzipFile(fileobj=f,mode='rb',compresslevel=config["compressLevel"])
                    #content = f.read()
                    #data = content.decode(config["ieeg"]["binaryEncoding"])
                    #print(type(f_in.myfileobj.))
                    #f_out = gzip.decompress(f_in.fileobj.read())
                    data = np.frombuffer(f.read(),dtype=np.dtype(config["ieeg"]["binaryEncoding"]))
                    print(type(data))
            else:
                with open(file,mode='rb') as f:
                    data = np.fromfile(f,dtype=config["ieeg"]["binaryEncoding"])
                    print(data.shape)
            array = np.reshape(data,[len(headers),-1],order='F')
            print(array.shape)
        except ValueError as e:
            print(e)
        


