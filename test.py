#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import scipy.io as sio
import json
import pandas as pd

if __name__ == '__main__':

    with open('BIDS_converter/config.json', 'r') as fst:
        config = json.load(fst)
    mat1 = sio.loadmat("/home/sbf/Desktop/Workspace/Phoneme_sequencing/D48/D48_Trials.mat")
    mat2 = sio.loadmat("/home/sbf/Desktop/Workspace/Phoneme_sequencing/D48/D48_trialInfo.mat")

    newmat = np.ndarray(shape=(208,0), dtype=float, order='F')
    newmat_names = []
    newmat_dtype = []
    for i in list(mat1):
        if "__" not in i and "readme" not in i:
            if mat1[i].dtype.names is not None:
                for j in mat1[i].dtype.names:
                    #print(np.transpose(mat1[i][j]).shape, newmat.shape)
                    newmat = np.append(newmat, np.transpose(mat1[i][j]),axis=1)
                    newmat_names.append(j)
                    newmat_dtype.append(mat1[i][j][0][0].dtype)
                df = pd.DataFrame(newmat,columns=newmat_names)
                
                #Set correct data types for smooth looking data in .tsv format
                for k in range(len(newmat_names)):
                    df[newmat_names[k]] = df[newmat_names[k]].astype(newmat_dtype[k])
                #print(df)
                df.to_csv(i+".tsv",sep="\t")
    
        


