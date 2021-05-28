#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import scipy.io as sio
import pandas as pd
import os

def mat2df(mat_file, var=None,filepath=None): 
    if isinstance(var,str):
        var = [var]

    vnames = []
    #mat_file is a file path and var_list is a list of strings corresponding to structure field names
    if isinstance(mat_file,str):
        if os.path.isfile(mat_file):
            return mat2df(sio.loadmat(mat_file,simplify_cells=True),var,filepath=mat_file)
        else:
            print(mat_file +"is not a valid file path")
            return
    elif isinstance(mat_file,dict):
        mat=mat_file
        if any("__" in i for i in list(mat)) or any("readme" in i for i in list(mat)):
            for i in list(mat):
                if "__" not in i and "readme" not in i: 
                    return mat2df(mat[i],var,filepath)
            raise ValueError("no variable stored in {file}".format(file=filepath))
        elif any(i in mat.keys() for i in var) or any("." in i for i in var):
            df_list = []
            for i in var:
                if "." in i:
                    (left,right) = i.split(".",1)
                    if left in mat.keys():
                        df_list.append(mat2df(mat[left],right,filepath))
                elif i in mat.keys():
                    for vname in list(set(var).intersection(mat.keys())):
                        vnames.append(vname)
                    try:
                        df_list.append(pd.DataFrame(mat).filter(vnames).reset_index(drop=True)) #end
                    except ValueError as e:
                        print("warning:"+e)  
                        for vname in vnames:
                            df_list.append(pd.DataFrame(mat[vname]).reset_index(drop=True))
            return pd.concat(df_list,axis=1).squeeze()
        else:
            raise ValueError("None of the vars {vars} were found in {file}".format(vars=var,file=filepath))
    elif isinstance(mat_file,list):
        if isinstance(mat_file[0],str):
            if os.path.isfile(mat_file[0]):
                return pd.concat([mat2df(mat,var) for mat in mat_file],axis=1).squeeze()
        else:
            mat = pd.DataFrame(mat_file)
            return mat.filter(list(set(var).intersection(mat.columns.tolist()))).reset_index(drop=True).squeeze()