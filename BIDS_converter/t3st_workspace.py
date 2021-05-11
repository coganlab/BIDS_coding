#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import scipy.io as sio
import json
import pandas as pd

if __name__ == '__main__':

    with open('config.json', 'r') as fst:
        config = json.load(fst)
    mat1 = sio.loadmat("/media/sf_Ubuntu_files/Workspace/Phoneme_sequencing/D48/D48_Trials.mat")
    mat2 = sio.loadmat("/media/sf_Ubuntu_files/Workspace/Phoneme_sequencing/D48/D48_trialInfo.mat")
    for i in list(mat2):
        if "__" not in i and "readme" not in i:
            if len(mat2[i]) == 1:
                rownum = len(mat2[i][0])
            else:
                rownum = len(mat2[i])
            newmat = np.ndarray(shape=(rownum,0), dtype=float, order='F')
            newmat_names = []
            newmat_dtype = []
            karray = np.array([])
            print(mat2[i][0][0][0][0][0].dtype)
            if mat2[i].dtype.names is not None:
                for j in mat2[i][0].dtype.names:
                    #print(np.transpose(mat1[i][j]).shape, newmat.shape)
                    newmat = np.append(newmat, np.transpose(mat2[i][j]),axis=1)
                    newmat_names.append(j)
                    newmat_dtype.append(mat1[i][j][0][0].dtype)
                df = pd.DataFrame(newmat,columns=newmat_names)
                
                #Set correct data types for smooth looking data in .tsv format
                for k in range(len(newmat_names)):
                    df[newmat_names[k]] = df[newmat_names[k]].astype(newmat_dtype[k])
                #print(df)
                df.to_csv(i+".tsv",sep="\t")
                '''
                elif mat2[i][0].dtype.names is not None:
                for j in mat2[i][0].dtype.names:
                    print(np.transpose(mat2[i][k][j]).shape, newmat.shape)
                    for k in range(len(mat2[i])):
                        karray.append(mat2[i][k][j][0][0])
                    newmat = np.append(newmat,karray)
                    karray = np.array(shape=(0,0))
                    newmat_names.append(j)
                    newmat_dtype.append(mat2[i][j][0][0].dtype)
                df = pd.DataFrame(newmat,columns=newmat_names)
                
                #Set correct data types for smooth looking data in .tsv format
                for k in range(len(newmat_names)):
                    df[newmat_names[k]] = df[newmat_names[k]].astype(newmat_dtype[k])
                #print(df)
                df.to_csv(mat_file.split(".mat")[0]+".tsv",sep="\t")
                '''
            elif mat2[i][0][0].dtype.names is not None:
                for j in mat2[i][0][0].dtype.names:
                    if j in config['eventFormat']: #if variable is named by user
                        #print(np.transpose(mat2[i][0][j]).shape, newmat.shape)
                        for k in range(len(mat2[i][0])):
                            karray = np.append(karray,mat2[i][0][k][j][0][0])
                        print(karray.shape)
                        newmat = np.append(newmat,np.reshape(karray,(-1,1)),axis=1)
                        karray = np.array([])
                        newmat_names.append(j)
                        newmat_dtype.append(mat2[i][0][0][j][0][0].dtype)
                df = pd.DataFrame(newmat,columns=newmat_names)
                
                #Set correct data types for smooth looking data in .tsv format
                for k in range(len(newmat_names)):
                    try:
                        df[newmat_names[k]] = df[newmat_names[k]].astype(newmat_dtype[k])
                    except ValueError:
                        continue
                #print(df)
                df.to_csv(i+".tsv",sep="\t")
    
        


