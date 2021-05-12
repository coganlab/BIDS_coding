#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse
import sys
import re
import shutil
import json
import subprocess
import gzip
import numpy as np
import nibabel as nib
import csv
import subprocess
from pathlib import Path
import pydicom as dicom
import scipy.io as sio
loadmat = sio.loadmat
import pandas as pd

def get_parser(): #parses flags at onset of command
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter
        , description="""
         Data2bids is a script based on the SIMEXP lab script to convert nifti MRI files into BIDS format. This script has been modified to 
         also parse README data as well as include conversion of DICOM files to nifti. The script utilizes Chris Rorden's Dcm2niix program for 
         actual conversion. 

         This script takes one of two formats for conversion. The first is a series of DICOM files in sequence with an optional \"medata\" folder which
         contains any number of single or multi-echo uncompressed nifti files (.nii). Note that nifti files in this case must also have a corresponding 
         DICOM scan run, but not necessarily scan echo (for example, one DICOM scan for run 5 but three nifti files which are echoes 1, 2, and 3 of
         run 5). The other format is a series of nifti files and a README.txt file formatted the same way as it is in the example. Both formats are 
         shown in the examples folder.

         Both formats use a .json config file that maps either DICOM tags or text within the nifti file name to BIDS metadata. The syntax and formatting of this .json file 
         can be found here https://github.com/SIMEXP/Data2Bids#heuristic.

         The only thing this script does not account for is event files. If you have the 1D files that's taken care of, but chances are you have some other 
         format. If this is the case, I recommend https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/05-task-events.html
         so that you can make BIDS compliant event files.

         Data2bids documentation at https://github.com/SIMEXP/Data2Bids
         Dcm2niix documentation at https://github.com/rordenlab/dcm2niix"""
        , epilog="""
            Made by Aaron Earle-Richardson (ae166@duke.edu)
            """)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-i"
        , "--input_dir"
        , required=False
        , default=None
        , help="""
        Input data directory(ies), must include a readme.txt file formatted like example under examples folder. 
        Mutually exclusive with DICOM directory option. Default: current directory
        """,
        )

    parser.add_argument(
        "-c"
        , "--config"
        , required=False
        , default=None
        , help="JSON configuration file (see https://github.com/SIMEXP/Data2Bids/blob/master/example/config.json)",
        )

    parser.add_argument(
        "-o"
        , "--output_dir"
        , required=False
        , default=None
        , help="Output BIDS directory, Default: Inside current directory ",
        )

    group.add_argument(
        "-d"
        ,"--DICOM_path"
        , default=None
        , required=False
        , help="Optional DICOM directory, Mutually exclusive with input directory option",
        )

    parser.add_argument(
        "-m"
        ,"--multi_echo"
        , nargs='*'
        , type=int
        , required=False
        , help="""
        indicator of multi-echo dataset. Only necessary if NOT converting DICOMs. For example, if runs 3-6 were all multi-echo then the flag
        should look like: -m 3 4 5 6 . Additionally, the -m flag may be called by itself if you wish to let data2bids auto-detect multi echo data,
        but it will not be able to tell you if there is a mistake."""
        )

    parser.add_argument(
        "-ow"
        , "--overwrite"
        , required=False
        , action='store_true' 
        , help="overwrite preexisting BIDS file structures in destination location",
        )

    parser.add_argument(
        "-verb"
        , "--verbose"
        , required=False
        , action='store_true' 
        , help="verbosity",
        )

    return(parser)

class Data2Bids(): #main conversion and file organization program

    def __init__(self, input_dir=None, config=None, output_dir=None, 
    DICOM_path=None, multi_echo=None, overwrite=False, verbose=False): 
    #sets the .self globalization for self variables
        self._input_dir = None
        self._config_path = None
        self._config = None
        self._bids_dir = None
        self._bids_version = "1.5.2"
        self._dataset_name = None

        self.set_overwrite(overwrite)
        self.set_data_dir(input_dir,DICOM_path)
        self.set_config_path(config)
        self.set_bids_dir(output_dir)
        self.set_DICOM(DICOM_path)
        self.set_multi_echo(multi_echo)
        self.set_verbosity(verbose)
        

    def set_overwrite(self,overwrite):
        self._is_overwrite = overwrite

    def set_verbosity(self,verbose):
        self._is_verbose = verbose

    def set_multi_echo(self,multi_echo): #if -m flag is called
        if multi_echo is None:
            self.is_multi_echo = False
        else:
            self.is_multi_echo = True
            if not multi_echo:
                self._multi_echo = 0
            else:
                self._multi_echo = multi_echo

    def set_DICOM(self, ddir): #triggers only if dicom flag is called and therefore _data_dir is None
        if self._data_dir is None:
            self._data_dir = os.path.dirname(self._bids_dir)
            subdirs = [x[0] for x in os.walk(ddir)]
            files = [x[2] for x in os.walk(ddir)]
            sub_num = str(dicom.read_file(os.path.join(subdirs[1],files[1][0]))[0x10, 0x20].value).split("_",1)[1]
            sub_dir = os.path.join(os.path.dirname(self._bids_dir),"sub-{SUB_NUM}".format(SUB_NUM=sub_num)) #destination subdirectory
            if os.path.isdir(sub_dir):
                proc = subprocess.Popen("rm -rf {file}".format(file=sub_dir), shell=True, stdout=subprocess.PIPE)
                proc.communicate()
            os.mkdir(sub_dir)

            if any("medata" in x for x in subdirs):     #copy over and list me data
                melist = [x[2] for x in os.walk(os.path.join(ddir,"medata"))][0]
                runlist = []
                for me in melist:
                    if me.startswith("."):
                        continue
                    runmatch = re.match(r".*run(\d{2}).*",me).group(1)
                    if str(int(runmatch)) not in runlist:
                        runlist.append(str(int(runmatch)))
                    shutil.copyfile(os.path.join(ddir,"medata",me),os.path.join(sub_dir,me))
                self.is_multi_echo = True #will trigger even if single echo data is in medata folder. Should still be okay

            for subdir in subdirs[1:]: #not including parent folder or /medata, run dcm2niix on non me data
                try:
                    fobj = dicom.read_file(os.path.join(subdir, list(os.walk(subdir))[0][2][0]),force=True) #first dicom file of the scan
                    scan_num = str(int(os.path.basename(subdir))).zfill(2)
                except ValueError:
                    continue
                firstfile = [x[2] for x in os.walk(subdir)][0][0]
                #print(str(fobj[0x20, 0x11].value), runlist)
                # running dcm2niix, 
                if str(fobj[0x20, 0x11].value) in runlist:
                    proc = subprocess.Popen("dcm2niix -z y -f run{SCAN_NUM}_%p_%t_sub{SUB_NUM} -o {OUTPUT_DIR} -s y -b y {DATA_DIR}".format(
                        OUTPUT_DIR=sub_dir, SUB_NUM=sub_num, DATA_DIR=os.path.join(subdir,firstfile), SCAN_NUM=scan_num), shell=True, stdout=subprocess.PIPE)
                    #output = proc.stdout.read()
                    outs, errs = proc.communicate()
                    prefix = re.match(".*/sub-{SUB_NUM}/(run{SCAN_NUM}".format(SUB_NUM=sub_num,SCAN_NUM=scan_num) + "[^ \(\"\\n\.]*).*",
                        str(outs)).group(1)
                    for file in os.listdir(sub_dir):
                        mefile = re.match("run{SCAN_NUM}(\.e\d\d)\.nii".format(SCAN_NUM=scan_num),file)
                        if re.match("run{SCAN_NUM}\.e\d\d.nii".format(SCAN_NUM=scan_num),file):
                            shutil.move(os.path.join(sub_dir,file),os.path.join(sub_dir,prefix + mefile.group(1) + ".nii"))
                            shutil.copy(os.path.join(sub_dir,prefix + ".json"),os.path.join(sub_dir,prefix + mefile.group(1) + ".json"))
                    os.remove(os.path.join(sub_dir,prefix + ".nii.gz"))
                    os.remove(os.path.join(sub_dir,prefix + ".json"))
                else:
                    proc = subprocess.Popen("dcm2niix -z y -f run{SCAN_NUM}_%p_%t_sub{SUB_NUM} -o {OUTPUT_DIR} -b y {DATA_DIR}".format(
                        OUTPUT_DIR=sub_dir, SUB_NUM=sub_num, DATA_DIR=subdir, SCAN_NUM=scan_num), shell=True, stdout=subprocess.PIPE)
                    outs, errs = proc.communicate()
                sys.stdout.write(outs.decode("utf-8"))

            self._multi_echo = runlist
            self._data_dir = os.path.join(os.path.dirname(self._bids_dir), "sub-{SUB_NUM}".format(SUB_NUM=sub_num))
        self._DICOM_path = ddir

    def get_data_dir(self):
        return self._data_dir

    def set_data_dir(self, data_dir,DICOM): #check if input dir is listed
        if DICOM is None:
            if data_dir is None:
                self._data_dir = os.getcwd()
            else:
                self._data_dir = data_dir
            self._dataset_name = os.path.basename(self._data_dir)
        else:
            self._data_dir = None

    def get_config(self):
        return self._config

    def get_config_path(self):
        return self._config_path

    def _set_config(self):
        with open(self._config_path, 'r') as fst:
            self._config = json.load(fst)

    def set_config(self, config):
        self._config = config

    def set_config_path(self, config_path):
        if config_path is None:
            # Checking if a config.json is present
            if os.path.isfile(os.path.join(os.getcwd(), "config.json")):
                self._config_path = os.path.join(os.getcwd(), "config.json")
            # Otherwise taking the default config
            else:
                self._config_path = os.path.join(os.path.dirname(__file__), "config.json")
        else:
            self._config_path = config_path

        self._set_config()

    def get_bids_dir(self):
        return self._bids_dir

    def set_bids_dir(self, bids_dir):
        if bids_dir is None:
            # Creating a new directory for BIDS
            try:
                self._bids_dir = os.path.join(self._data_dir, self._dataset_name + "_BIDS")
            except TypeError:
                print("Error: Please provide input data directory if no BIDS directory...")
        
        else: #deleting old BIDS to make room for new 
            if not os.path.basename(bids_dir) == "BIDS":
                newdir = os.path.join(bids_dir,"BIDS")
            else:
                newdir = bids_dir
            if not os.path.isdir(newdir):
                os.mkdir(newdir)
            elif self._is_overwrite:
                self.force_remove(newdir)
                os.mkdir(newdir)
            bids_dir = newdir
                #proc = subprocess.Popen("rm -rf {file}".format(file=newdir), shell=True, stdout=subprocess.PIPE)
                #proc.communicate()
            
        self._bids_dir = bids_dir

    def get_bids_version(self):
        return self._bids_version

    def match_regexp(self, config_regexp, filename, subtype=False):
        delimiter_left = config_regexp["left"]
        delimiter_right = config_regexp["right"]
        match_found = False

        if subtype:
            for to_match in config_regexp["content"]:
                if re.match(".*?"
                            + delimiter_left
                            + '(' + to_match[1] + ')'
                            + delimiter_right
                            + ".*?", filename):
                    match = to_match[0]
                    match_found = True
        else:
            for to_match in config_regexp["content"]:
                if re.match(".*?"
                            + delimiter_left
                            + '(' + to_match + ')'
                            + delimiter_right
                            + ".*?", filename):
                    match = re.match(".*?"
                                     + delimiter_left
                                     + '(' + to_match + ')'
                                     + delimiter_right
                                     + ".*?", filename).group(1)
                    match_found = True
        assert match_found
        return match

    def bids_validator(self):
        assert self._bids_dir is not None, "Cannot launch bids-validator without specifying bids directory !"
        #try:
        subprocess.check_call(['bids-validator', self._bids_dir])
        #except FileNotFoundError:
        #    print("bids-validator does not appear to be installed")

    def generate_names(self, part_match, src_file_path, filename, namelist=None): #function to run through name text and generate metadata
        sess_match = None
        ce_match = None
        acq_match = None
        echo_match = None
        data_type_match = None
        task_label_match = None
        run_match = None
        dst_file_path = self._bids_dir + "/sub-" + part_match
        new_name = "/sub-" + part_match
        SeqType = None
        # Matching the session
        try:
            sess_match = self.match_regexp(self._config["sessLabel"], filename)
            dst_file_path = dst_file_path + "/ses-" + sess_match
            new_name = new_name + "_ses-" + sess_match
        except AssertionError:
            if self._is_verbose:
                print("No session found for %s" %src_file_path)
        
        # Matching the run number
        try:
            run_match = self.match_regexp(self._config["runIndex"],filename)
            new_name = new_name + "_run-" + run_match
        except AssertionError:
            pass

        # Matching the anat/fmri data type and task
        try:
            data_type_match = self.match_regexp(self._config["anat"]
                                                ,filename
                                                , subtype=True)
            dst_file_path = dst_file_path + "/anat"
        except (AssertionError, KeyError) as e:
            # If no anatomical, trying functionnal
            try:
                data_type_match = self.match_regexp(self._config["func"]
                                                    ,filename
                                                    , subtype=True)
                dst_file_path = dst_file_path + "/func"
                # Now trying to match the task
                try:
                    task_label_match = self.match_regexp(self._config["func.task"]
                                                         ,filename
                                                         , subtype=True)
                    new_name = new_name + "_task-" + task_label_match
                except AssertionError:
                    print("No task found for %s" %src_file_path)
                    return

            except (AssertionError, KeyError) as e:
                # no functional or anatomical, try ieeg
                try:
                    data_type_match = self.match_regexp(self._config["ieeg"]
                                                        ,filename
                                                        ,subtype=True)
                    dst_file_path = dst_file_path + "/ieeg"
                    # Now trying to match the task
                    try:
                        task_label_match = self.match_regexp(self._config["ieeg.task"]
                                                         ,filename
                                                         , subtype=True)
                        new_name = new_name + "_task-" + task_label_match
                    except AssertionError:
                        print("No task found for %s" %src_file_path)
                        return
                except AssertionError:
                    print("No anat, func, or ieeg data type found for %s" %src_file_path)
                    return
                except KeyError:
                    print("No anat, func, or ieeg data type found in config file, one of these data types is required")
                    return
        #check for optional labels
        try:
            acq_match = self.match_regexp(self._config["acq"],filename)
            new_name = new_name + "_acq-" + acq_match
        except (AssertionError, KeyError) as e:
            if self._is_verbose:
                print("no optional labels for %s" %src_file_path)
        try: 
            ce_match = self.match_regexp(self._config["ce"]
                                            ,filename)
            new_name = new_name + "_ce-" + ce_match
        except (AssertionError, KeyError) as e:
            if self._is_verbose:
                print("no special contrast labels for %s" %src_file_path)
        #if is an MRI
        if dst_file_path.endswith("/func") or dst_file_path.endswith("/anat"):
            try: 
                SeqType = str(self.match_regexp(self._config["pulseSequenceType"], filename, subtype=True))
            except AssertionError:
                print("No pulse sequence found for %s" %src_file_path)
            except KeyError:
                print("pulse sequence not listed for %s, will look for in file header" %src_file_path)
            try:
                echo_match = self.match_regexp(self._config["echo"],filename)
                new_name = new_name + "_echo-" + echo_match 
            except AssertionError:
                print("No echo found for %s" %src_file_path)

         
	# Adding the modality to the new filename
        new_name = new_name + "_" + data_type_match

        return(new_name,dst_file_path,run_match,
               acq_match,echo_match,sess_match,ce_match,
               data_type_match, task_label_match, SeqType)
        
    def slice_time_calc(self, TR, sNum, totNum, delay):
        intervaltime = (TR-delay) / totNum
        tslice = delay + ((sNum) * intervaltime)
        return(tslice)
    
    def multi_echo_check(self,runnum,src_file=""): # check to see if run is multi echo based on input
        if self.is_multi_echo:
            if int(runnum) in self._multi_echo: 
                return(True)
            else:
                if self._multi_echo == 0:
                    try:
                        self.match_regexp(self._config["echo"],src_file)
                    except AssertionError:
                        return(False)
                    return(True)
                else:
                    return(False)
        else:
            return(False)

    def get_params(self,folder,echo_num,run_num): #function to run through DICOMs and get metadata
        #threading?
        if self.is_multi_echo and run_num in self._multi_echo:
            vols_per_time = len(self._config['delayTimeInSec'])-1
            echo = self._config['delayTimeInSec'][echo_num]
        else:
            vols_per_time = 1
            echo = None
            
        for root, _, dfiles in os.walk(folder, topdown=True):
            dfiles.sort()
            for dfile in dfiles:
                dcm_file_path = os.path.join(root, dfile)
                fobj = dicom.read_file(str(dcm_file_path))
                if echo is None:
                    try:
                        echo = float(fobj[0x18, 0x81].value) / 1000
                    except KeyError:
                        echo = self._config['delayTimeInSec'][0]
                ImagesInAcquisition = int(fobj[0x20, 0x1002].value)
                seqlist=[]
                for i in list(range(5)):
                    try:
                        seqlist.append(fobj[0x18, (32+i)].value)
                        if seqlist[i] == 'NONE':
                            seqlist[i] = None
                        if isinstance(seqlist[i], dicom.multival.MultiValue):
                            seqlist[i] = list(seqlist[i])
                        if isinstance(seqlist[i], list):
                            seqlist[i] = ", ".join(seqlist[i])
                    except KeyError:
                        seqlist.append(None)
                [ScanningSequence, SequenceVariant, SequenceOptions, AquisitionType, SequenceName] = seqlist
                try:
                    timings
                except NameError:
                    timings = [None] * int(ImagesInAcquisition/vols_per_time)

                RepetitionTime = ((float(fobj[0x18, 0x80].value)/1000)) #TR value extracted in milliseconds, converted to seconds
                try:
                    acquisition_series = self._config['series']
                except KeyError: 
                    print("default")
                    acquisition_series = "non-interleaved"
                if acquisition_series == "even-interleaved":
                    InstackPositionNumber = 2
                else:
                    InStackPositionNumber = 1
                InstanceNumber = 0
                while None in timings:
                    if timings[InStackPositionNumber-1] is None:
                        timings[InStackPositionNumber-1] = self.slice_time_calc(RepetitionTime, InstanceNumber,
                                                                            int(ImagesInAcquisition/vols_per_time),echo)
                    if acquisition_series == "odd-interleaved" or acquisition_series == "even-interleaved" :
                        InStackPositionNumber +=2
                        if InStackPositionNumber > ImagesInAcquisition/vols_per_time and acquisition_series == "odd-interleaved":
                            InStackPositionNumber = 2
                        elif InStackPositionNumber > ImagesInAcquisition/vols_per_time and acquisition_series == "even-interleaved":
                            InStackPositionNumber = 1
                    else:
                        InStackPositionNumber += 1
                    InstanceNumber += 1
                return(timings,echo,ScanningSequence, SequenceVariant, SequenceOptions, SequenceName) 

    def set_default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        raise TypeError

    def force_remove(self, mypath):

        if os.path.isfile(mypath):
            os.remove(mypath)
        try:
            if os.path.isdir(mypath):
                self.delete_folder(Path(mypath))
        except OSError:
            shutil.rmtree(mypath,ignore_errors=True)

    def delete_folder(self, pth):
        for sub in pth.iterdir() :
            if sub.is_dir() :
                self.delete_folder(sub)
            else :
                sub.unlink()
        pth.rmdir()

    def run(self): #main function

        # First we check that every parameters are configured
        if (self._data_dir is not None
            and self._config_path is not None
            and self._config is not None
            and self._bids_dir is not None):

            print("---- data2bids starting ----")
            print(self._data_dir)
            print("\n BIDS version:")
            print(self._bids_version)
            print("\n Config from file :")
            print(self._config_path)
            print("\n Ouptut BIDS directory:")
            print(self._bids_dir)
            print("\n")

            # Create the output BIDS directory
            if not os.path.exists(self._bids_dir):
                os.makedirs(self._bids_dir)
            #else
            #    shutil.rmtree(self._bids_dir)
            

            # What is the base format to convert to
            curr_ext = self._config["dataFormat"]
            compress = self._config["compress"]

            # delay time in TR unit (if delay_time = 1, delay_time = repetition_time)
            repetition_time = self._config["repetitionTimeInSec"]
            delaytime = self._config["delayTimeInSec"]

            #dataset_description.json must be included in the folder root foolowing BIDS specs
            if os.path.exists(self._bids_dir + "/dataset_description.json"):
                #with open(dst_file_path + new_name + ".json", 'w') as fst:
                with open(self._bids_dir + "/dataset_description.json") as fst:
                    filedata=json.load(fst)
                with open(self._bids_dir + "/dataset_description.json", 'w') as fst:
                    data = {'Name': self._dataset_name,
                               'BIDSVersion': self._bids_version}
                    filedata.update(data)
                    json.dump(filedata, fst, ensure_ascii=False, indent=4)
            else:
                with open(self._bids_dir + "/dataset_description.json", 'w') as fst:
                    data = {'Name': self._dataset_name,
                               'BIDSVersion': self._bids_version}
                    json.dump(data, fst, ensure_ascii=False, indent = 4)
            # now we can scan all files and rearrange them
            names_list = []
            tsv_condition_runs = []
            tsv_fso_runs = []
            dst_file_path_list = []
            d_list = []
            part_match = None
            run_list = []
            mat_list = []
            for root, _, files in os.walk(self._data_dir, topdown=True):
                files[:] = [f for f in files if not os.path.join(root,f).startswith(self._bids_dir)] #ignore BIDS directories
                if not files:
                    continue
                files.sort()
                if self._is_verbose:
                    print(files)
                while files:
                    file=files.pop(0)
                    #print(file)
                    src_file_path = os.path.join(root, file)
                    dst_file_path = self._bids_dir
                    data_type_match = None
                    new_name = None

                    #if re.match(".*?" + "imaginary" + ".*?" ,file):
                    #    continue
                    if re.match(".*?" + ".json", file):
                        try:
                            part_match = self.match_regexp(self._config["partLabel"], file)
                        except AssertionError:
                            raise SyntaxError("file: {filename} has no matching {config}".format(filename=file,config=self._config["content"][:][0]))
                        try:
                            (new_name,dst_file_path, run_match, _,echo_match,sess_match,_,
                             data_type_match,task_label_match,SeqType) = self.generate_names(part_match, src_file_path, file)
                        except TypeError:
                            continue
                        if echo_match is None:
                            echo_match=0
                        if new_name in names_list:
                            shutil.copy(src_file_path, dst_file_path + new_name + ".json")
                            # finally, if it is a bold experiment, we need to edit the JSON file using DICOM tags
                            if os.path.exists(dst_file_path + new_name + ".json"):
                                ### https://github.com/nipy/nibabel/issues/712, that is why we take the
                                ### scanner parameters from the config.json
                                #nib_img = nib.load(src_file_path)
                                #TR = nib_img.header.get_zooms()[3]
                                for foldername in os.listdir(str(self._DICOM_path)):
                                    if run_match.zfill(4) == foldername.zfill(4):
                                        DICOM_filepath = os.path.join(self._DICOM_path, foldername)
                                        slicetimes, echotime, ScanSeq, SeqVar, SeqOpt, SeqName = self.get_params(str(DICOM_filepath), int(echo_match), int(run_match))
                                    
                                    #with open(dst_file_path + new_name + ".json", 'w') as fst:
                                with open(dst_file_path + new_name + ".json", 'r+') as fst:
                                    filedata=json.load(fst)
                                with open(dst_file_path + new_name + ".json", 'w') as fst:
                                    if data_type_match == "bold":
                                        filedata['TaskName'] = task_label_match
                                        filedata['SliceTiming'] = slicetimes
                                        if int(run_match) in self._multi_echo :
                                            filedata['EchoTime'] = echotime
                                        else:
                                            filedata['DelayTime'] = delaytime[0]
                                    if SeqType is not None:
                                        filedata['PulseSequenceType'] = SeqType
                                    if ScanSeq is not None:
                                        filedata['ScanningSequence'] = ScanSeq
                                    if SeqVar is not None: 
                                        filedata['SequenceVariant'] = SeqVar
                                    if SeqOpt is not None:
                                        filedata['SequenceOption'] = SeqOpt
                                    if SeqName is not None:
                                        filedata['SequenceName'] = SeqName
                                    json.dump(filedata, fst, ensure_ascii=False, indent=4, default=self.set_default)
                            else:
                                print("Cannot update %s" %(dst_file_path + new_name + ".json"))
                        elif any(re.search(".nii",filelist) for filelist in files):
                            files.append(src_file_path)
                            part_match = ""
                        continue
                    elif re.match(".*?" + "EADME.txt", file):  #if README.txt in image list
                        with open(src_file_path, 'r') as readmetext:
                            for line in readmetext:
                                regret_words = ["Abort","NOTE"]
                                if ". tempAttnAudT" in line:  #these lines could and should be improved by linking config["func.task"] instead of literal strings
                                    prevline="con"
                                    tsv_condition_runs.append(re.search(r'\d+', line).group()) #save the first number on the line
                                elif ". fsoSubLocal" in line:
                                    prevline="fso"
                                    tsv_fso_runs.append(re.search(r'\d+', line).group())
                                elif all(x in line for x in regret_words):
                                    if prevline == "con":
                                        del tsv_condition_runs[-1]
                                    elif prevline == "fso":
                                        del tsv_fso_runs[-1]
                                    prevline=""
                                else:
                                    prevline=""
                        if part_match is not None:   
                            if not os.path.exists(self._bids_dir + "/sub-" + part_match): #Writing both a particpant-specific and agnostic README. Requires creation of a .bidsignore file for local READMEs
                                os.makedirs(self._bids_dir + "/sub-" + part_match)
                            shutil.copy(src_file_path, self._bids_dir + "/sub-" + part_match + "/README.txt")
                            with open(src_file_path, 'r') as readmetext:
                                for line in readmetext:
                                    if os.path.exists(self._bids_dir + "/README"):
                                        with open(self._bids_dir + "/README", 'a') as f:
                                            f.write(line + "\n")
                                    else:
                                        with open(self._bids_dir + "/README", 'w') as f:
                                            f.write(line + "\n")
                            if not os.path.exists(self._bids_dir + "/.bidsignore"):
                                with open(self._bids_dir + "/.bidsignore", 'w') as f:
                                    f.write("*.txt")
                        else: 
                            files.append(src_file_path)
                        continue
                    elif re.match(".*?" + ".1D", file): 
                        d_list.append(src_file_path)
                        continue
                    elif re.match(".*?" + ".mat", file):
                        mat_list.append(src_file_path)
                        continue
                        # if the file doesn't match the extension, we skip it
                    elif not any(re.match(".*?" + ext, file) for ext in curr_ext):
                        print("Warning : Skipping %s" %src_file_path)
                        continue
                    if self._is_verbose:
                        print("trying %s" %src_file_path)
                    
                    # Matching the participant label to determine if there exists therein delete previously created BIDS subject files
                    try:
                        part_match = self.match_regexp(self._config["partLabel"], file)
                        if os.path.exists(self._bids_dir + "/sub-" + part_match) and not any("sub-" + part_match in x for x in names_list):
                            print("Deleting old BIDS directory for subject %s" %part_match)
                            shutil.rmtree(self._bids_dir + "/sub-" + part_match,onerror=self.force_remove)
                    except AssertionError:
                        print("No participant found for %s" %src_file_path)
                        continue
                    except OSError: #problem spot, may miss deleting some files causing them to erroneously carry over
                        shutil.rmtree(self._bids_dir + "/sub-" + part_match,ignore_errors=True) 
                    except TypeError: #problem spot, may miss deleting some files causing them to erroneously carry over
                        shutil.rmtree(self._bids_dir + "/sub-" + part_match,ignore_errors=True) 

                    try:
                        (new_name,dst_file_path,_,
                         _,echo_match,sess_match,_,
                         data_type_match,task_label_match,_) = self.generate_names(part_match, src_file_path, file)
                    
                    except TypeError as problem: #
                        print("\nIssue in generate names")
                        print("problem with %s:" %src_file_path, problem,"\n")
                        
                        continue

                    # Creating the directory where to store the new file
                    if not os.path.exists(dst_file_path):
                        os.makedirs(dst_file_path)

                    #print(data_type_match)
                    # finally, if the file is not nifti
                    if dst_file_path.endswith("/func") or dst_file_path.endswith("/anat"):
                        # we convert it using nibabel
                        if not any( file.endswith(ext) for ext in [".nii", ".nii.gz"] ): #check if .nii listed in config file, not if file ends with .nii
                            # loading the original image
                            nib_img = nib.load(src_file_path)
                            nib_affine = np.array(nib_img.affine)
                            nib_data = np.array(nib_img.dataobj)

                            # create the nifti1 image
                            # if minc format, invert the data and change the affine transformation
                            # there is also an issue on minc headers
                            if file.endswith(".mnc") :
                                if len(nib_img.shape) > 3:
                                    nib_affine[0:3, 0:3] = nib_affine[0:3, 0:3] 
                                    rot_z(np.pi/2) 
                                    rot_y(np.pi) 
                                    rot_x(np.pi/2)
                                    nib_data = nib_data.T
                                    nib_data = np.swapaxes(nib_data, 0, 1)

                                    nifti_img = nib.Nifti1Image(nib_data, nib_affine, nib_img.header)
                                    nifti_img.header.set_xyzt_units(xyz="mm", t="sec")
                                    zooms = np.array(nifti_img.header.get_zooms())
                                    zooms[3] = repetition_time
                                    nifti_img.header.set_zooms(zooms)
                                elif len(nib_img.shape) == 3:
                                    nifti_img = nib.Nifti1Image(nib_data, nib_affine, nib_img.header)
                                    nifti_img.header.set_xyzt_units(xyz="mm")
                            else:
                                nifti_img = nib.Nifti1Image(nib_data, nib_affine, nib_img.header)

                            #saving the image
                            nib.save(nifti_img, dst_file_path + new_name + ".nii.gz")

                        # if it is already a nifti file, no need to convert it so we just copy rename
                        if file.endswith(".nii.gz"):
                            shutil.copy(src_file_path, dst_file_path + new_name + ".nii.gz")
                        elif file.endswith(".nii"):
                            shutil.copy(src_file_path, dst_file_path + new_name + ".nii")
                            #compression just if .nii files
                            if compress is True:
                                print("zipping " + file)
                                with open(dst_file_path + new_name + ".nii", 'rb') as f_in:
                                    with gzip.open(dst_file_path + new_name + ".nii.gz", 'wb',9) as f_out:
                                        shutil.copyfileobj(f_in, f_out)
                                os.remove(dst_file_path + new_name + ".nii")

                    elif file.endswith(".edf"):
                        shutil.copy(src_file_path, dst_file_path + new_name + ".edf")
                    # move the sidecar from input to output

                    names_list.append(new_name)
                    dst_file_path_list.append(dst_file_path)
                    try:
                        run_list.append(int(run_match))
                    except UnboundLocalError:
                        pass

            if d_list :
                self.convert_1D(run_list, d_list, tsv_fso_runs, tsv_condition_runs, names_list, dst_file_path_list)

            if mat_list :
                self.mat2tsv(mat_list)
            # Output
            if self._is_verbose:
                tree(self._bids_dir)

            # Finally, we check with bids_validator if everything went alright (This wont work)
            #self.bids_validator()

        else:
            print("Warning: No parameters are defined !")        

    def mat2tsv(self, mat_files):
        df = pd.DataFrame()
        for mat_file in mat_files:
            mat = loadmat(mat_file)
            if isinstance(mat,dict): #if .mat is a struct
                for i in list(mat):
                    if "__" not in i and "readme" not in i: 
                        if self._is_verbose:
                            print(mat_file,"--->",mat_file.split(".mat")[0]+".tsv")

                        newmat_names = []
                        newmat_dtype = []
                        if mat[i].dtype.names is not None:
                            for j in mat[i].dtype.names:
                                if j in self._config['eventFormat']: #if variable is named by user
                                    karray = np.reshape(np.transpose(mat[i][j]),(-1))
                                    df[j] = pd.Series(karray, index=range(len(karray))) #assign columns to dataframe
                                    newmat_names.append(j)
                                    #print(j)
                                    newmat_dtype.append(mat[i][j][0][0].dtype)
                        elif mat[i][0][0].dtype.names is not None: #if you're psychotic and made a cell array of STRUCTURES
                            for j in mat[i][0][0].dtype.names:
                                if j in self._config['eventFormat']: #if variable is named by user
                                    #print(np.transpose(mat2[i][0][j]).shape, newmat.shape)
                                    karray = np.array([])
                                    for k in range(len(mat[i][0])):
                                        karray = np.append(karray,mat[i][0][k][j][0][0])
                                    df[j] = pd.Series(karray, index=range(len(karray)))
                                    newmat_names.append(j)
                                    newmat_dtype.append(mat[i][0][0][j][0][0].dtype)
                            
                        else: #sorry this code format doesn't leave many options for data formatting but it was the only option
                            raise KeyError("Current MATLAB data format not yet supported \nCurrent support covers stuctures and cell arrays of structures")
                        #Set correct data types for smooth looking data in .tsv format
                        for k in range(len(newmat_names)):
                            try:
                                df[newmat_names[k]] = df[newmat_names[k]].astype(newmat_dtype[k])
                                if isinstance(df[newmat_names[k]][0],str):
                                    for j in range(df[newmat_names[k]].size):
                                        df[newmat_names[k]].iloc[j] = re.sub("[\'\[\]]",'',df[newmat_names[k]].iloc[j])
                            except ValueError:
                                continue

            elif isinstance(mat,list): #if .mat is cell array
                print("\n No support for cell arrays yet")
            elif isinstance(mat,np.ndarray): #if .mat is matlab array
                print("\n No support for matlab arrays yet")
            else:
                datatype = type(mat)
                print("\n Uknown data type %s" %datatype)

        #print(df[self._config["eventFormat.IDcol"]].iloc[0],df[self._config["eventFormat.IDcol"]].iloc[-1])
        try:
            
            if self._config["eventFormat.IDcol"] in df.columns:
                if df[self._config["eventFormat.IDcol"]].iloc[0] == df[self._config["eventFormat.IDcol"]].iloc[-1]: 
                    #construct fake orig data name to run through name generator
                    match_name = mat_file.split(os.path.basename(mat_file))[0]+df[self._config["eventFormat.IDcol"]][0] + ".edf"
                else:
                    raise KeyError
            else:
                raise KeyError
        except KeyError:
            match_name = mat_file
        try:
            part_match = self.match_regexp(self._config["partLabel"], os.path.basename(match_name))
        except AssertionError:
            raise SyntaxError("file: {filename} has no matching {config}\n".format(filename=match_name,config=self._config["content"][:][0]))
        try:
            (new_name,dst_file_path, run_match, _,echo_match,sess_match,_,
                data_type_match,task_label_match,SeqType) = self.generate_names(
                    part_match, match_name, os.path.basename(match_name))
        except TypeError as e:
            raise e
        df.to_csv(dst_file_path + new_name.split("ieeg")[0] + "event.tsv",sep="\t")


    def convert_1D(self, run_list, d_list, tsv_fso_runs, tsv_condition_runs, names_list, dst_file_path_list):
        #This section is for converting .1D files to tsv event files. If you have the 1D files that's great, but chances are you have some other 
        #format if this is the case, I recommend https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/05-task-events.html
        #so that you can make BIDS compliant event files 
        fields = list( list() for _ in range(max(run_list)))
        categories = list( list() for _ in range(max(run_list)))
        writenames = list( list() for _ in range(max(run_list)))
        n=0                                # creating variables to save and write from
        for d_file in d_list :
            #print(d_file)
            n += 1
            
            try:
                category = re.search("-[0-9]{4}-[0-9]{1,2}-(.*)\\.1D", d_file).group(1) #search filename for category label
            except AttributeError:
                try:
                    category = re.search("-[0-9]{4}-(.{1,2}-?.*)\\.1D", d_file).group(1)
                except AttributeError:
                    print (d_file +" has no pattern matching: -####-(????)")
                    continue
            nfso = 0
            ncon = 0 
            with open(d_file) as lines: #loop through .tsv file line by line (each is a different run)
                for line in lines:
                    if "fso-" in d_file :
                        try:
                            runnum=int(tsv_fso_runs[nfso])
                            nfso += 1 
                        except IndexError:
                            print('Error, index was %s while list was:' %str(nfso))
                            print(tsv_fso_runs)
                            continue
                    elif "condition-" in d_file:
                        try:
                            runnum=int(tsv_condition_runs[ncon])
                            ncon += 1
                        except IndexError:
                            print('Error, index was %s while list was:' %str(ncon))
                            print(tsv_condition_runs)
                            continue
                    else:
                        continue
                    i=0
                    for name in names_list:
                        try:
                            if runnum is int(re.search("run-([0-9]{2})",name).group(1)):
                                if re.match(".*?" + "_bold" + ".*?", name):
                                    name = name.replace("_bold","")
                                    if re.match(".*?" + "_echo-[0-9]" + ".*?", name):
                                        name = name.replace(re.search("(_echo-[0-9]{2})",name).group(1),"")
                                for field in line.strip("\\n").split(): # saving the data to variables to write later
                                    if field != '0' and field != '1':
                                        fields[runnum-1].append(float(field))
                                        categories[runnum-1].append(category)
                                        writenames[runnum-1].append(dst_file_path_list[i] + name)
                                break
                            i+=1
                        except AttributeError:
                            print(str(runnum) +"is not in this list:" )
        for j in range(max(run_list)): #actually writing the file
            if fields[j]:
                #print(len(fields[j]), len(TRfields[j]))
                categories[j] = [categories[j] for _,categories[j] in sorted(zip(fields[j],categories[j]))]
                #TRfields[j] = [TRfields[j] for _,TRfields[j] in sorted(zip(fields[j],TRfields[j]))]
                fields[j].sort()
                #print(len(writenames[j]), len(categories[j]), len(fields[j]), len(TRfields[j]), len(tempTRcategories[j]))
                for i in range(len(writenames[j])+1):
                    tsvnames = []
                    if self.multi_echo_check(j+1):
                        for k in range((len(self._config["delayTimeInSec"])-1)):
                            tsvnames.append("_echo-" + str(k+1).zfill(2) + "_events.tsv")
                    else:
                        tsvnames.append("_events.tsv")
                    for ending in tsvnames:
                        if i == 0:
                            with open(writenames[j][0] + ending, 'a') as out_file:
                                tsv_writer = csv.writer(out_file, delimiter='\t')           
                                tsv_writer.writerow(['onset', 'duration', 'trial_type'])#,'TR_condition'])
                        else:
                            if i < len(writenames[j]):
                                duration = float(fields[j][i]) - float(fields[j][i-1])
                            with open(writenames[j][i-1] + ending, 'a') as out_file:
                                tsv_writer = csv.writer(out_file, delimiter='\t')           
                                tsv_writer.writerow([fields[j][i-1], duration, categories[j][i-1]])#,TRfields[j][i-1]])
                    

class DisplayablePath(): # this code simply creates a tree visual to explain the BIDS file organization
    display_filename_prefix_middle = '├──'
    display_filename_prefix_last = '└──'
    display_parent_prefix_middle = '    '
    display_parent_prefix_last = '│   '

    def __init__(self, path, parent_path, is_last):
        self.path = Path(str(path))
        self.parent = parent_path
        self.is_last = is_last
        if self.parent:
            self.depth = self.parent.depth + 1
        else:
            self.depth = 0

    @property
    def displayname(self):
        if self.path.is_dir():
            return self.path.name + '/'
        return self.path.name

    @classmethod
    def make_tree(cls, root, parent=None, is_last=False, criteria=None):
        root = Path(str(root))
        criteria = criteria or cls._default_criteria

        displayable_root = cls(root, parent, is_last)
        yield displayable_root

        children = sorted(list(path
                               for path in root.iterdir()
                               if criteria(path)),
                          key=lambda s: str(s).lower())
        count = 1
        for path in children:
            is_last = count == len(children)
            if path.is_dir():
		        #yield from
    	        for i in cls.make_tree(path,
                                       parent=displayable_root,
                                       is_last=is_last,
                                       criteria=criteria):
                    yield i
            else:
                yield cls(path, displayable_root, is_last)
            count += 1

    @classmethod
    def _default_criteria(cls,path):
        return True

    def displayable(self):
        if self.parent is None:
            return self.path

        _filename_prefix = (self.display_filename_prefix_last
                            if self.is_last
                            else self.display_filename_prefix_middle)

        parts = ['{!s} {!s}'.format(_filename_prefix,
                                    self.displayname)]

        parent = self.parent
        while parent and parent.parent is not None:
            parts.append(self.display_parent_prefix_middle
                         if parent.is_last
                         else self.display_parent_prefix_last)
            parent = parent.parent

        return ''.join(reversed(parts))
#this part of the code creates the tree graphic
def tree(path):
    paths = DisplayablePath.make_tree(Path(path))
    for path_to_display in paths:
        print(path_to_display.displayable())

def rot_x(alpha):
    return np.array([[1, 0, 0]
                     , [0, np.cos(alpha), np.sin(alpha)]
                     , [0, -np.sin(alpha), np.cos(alpha)]])

def rot_y(alpha):
    return np.array([[np.cos(alpha), 0, -np.sin(alpha)]
                     , [0, 1, 0]
                     , [np.sin(alpha), 0, np.cos(alpha)]])

def rot_z(alpha):
    return np.array([[np.cos(alpha), np.sin(alpha), 0]
                     , [-np.sin(alpha), np.cos(alpha), 0]
                     , [0, 0, 1]])

def main():
    args = get_parser().parse_args()
    #print(args)
    data2bids = Data2Bids(**vars(args))
    data2bids.run()
    
if __name__ == '__main__':
    main()
