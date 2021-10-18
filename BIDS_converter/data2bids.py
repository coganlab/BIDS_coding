#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import argparse
import datetime
import gc
import gzip
import json
import subprocess
import sys
from typing import Union, List

import nibabel as nib
import pydicom as dicom
from bids import layout
from matgrab import mat2df
from pyedflib import highlevel
from scipy.io import wavfile

from BIDS_converter.utils import *


def get_parser():  # parses flags at onset of command
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description="""
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
         Dcm2niix documentation at https://github.com/rordenlab/dcm2niix""", epilog="""
            Made by Aaron Earle-Richardson (ae166@duke.edu)
            """)

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-i", "--input_dir", required=False, default=None, help="""
        Input data directory(ies), must include a readme.txt file formatted like example under examples folder. 
        Mutually exclusive with DICOM directory option. Default: current directory
        """, )

    parser.add_argument("-c", "--config", required=False, default=None,
                        help="JSON configuration file (see https://github.com/SIMEXP/Data2Bids/blob/master/example/config.json)", )

    parser.add_argument("-o", "--output_dir", required=False, default=None,
                        help="Output BIDS directory, Default: Inside current directory ", )

    group.add_argument("-d", "--DICOM_path", default=None, required=False,
                       help="Optional DICOM directory, Mutually exclusive with input directory option", )

    parser.add_argument("-m", "--multi_echo", nargs='*', type=int, required=False, help="""
        indicator of multi-echo dataset. Only necessary if NOT converting DICOMs. For example, if runs 3-6 were all multi-echo then the flag
        should look like: -m 3 4 5 6 . Additionally, the -m flag may be called by itself if you wish to let data2bids auto-detect multi echo data,
        but it will not be able to tell you if there is a mistake.""")

    parser.add_argument("-ow", "--overwrite", required=False, action='store_true',
                        help="overwrite preexisting BIDS file structures in destination location", )

    parser.add_argument("-ch", "--channels", nargs='*', required=False, help="""
        Indicator of channels to keep from edf files. 
        """)

    parser.add_argument("-s", "--stim_dir", required=False, default=None, help="directory containing stimuli files", )

    parser.add_argument("-v", "--verbose", required=False, action='store_true', help="verbosity", )

    return parser


class Data2Bids:  # main conversion and file organization program

    def __init__(self, input_dir=None, config=None, output_dir=None, DICOM_path=None, multi_echo=None, overwrite=False,
                 stim_dir=None, channels=None, verbose=False):
        # sets the .self globalization for self variables
        self._input_dir = None
        self._config_path = None
        self._config = None
        self._bids_dir = None
        self._bids_version = "1.6.0"
        self._dataset_name = None
        self._data_types = {"anat": False, "func": False, "ieeg": False}
        self._ignore = []

        self.set_overwrite(overwrite)
        self.set_data_dir(input_dir, DICOM_path)
        self.set_config_path(config)
        self.set_bids_dir(output_dir)
        self.set_DICOM(DICOM_path)
        self.set_multi_echo(multi_echo)
        self.set_verbosity(verbose)
        self.set_stim_dir(stim_dir)
        self.set_channels(channels)

    def check_ignore(self, file):

        assert os.path.isabs(file), file + "must be given with the absolute path including root"
        if not os.path.exists(file):
            raise FileNotFoundError(file + " does not exist")

        ans = False
        for item in self._ignore:
            if os.path.isfile(item) and Path(file).resolve() == Path(item).resolve():
                ans = True
            elif os.path.isdir(item):
                for root, dirs, files in os.walk(item):
                    if os.path.basename(file) in files and Path(root).resolve() == Path(
                            os.path.dirname(file)).resolve():
                        ans = True
        return ans

    def set_stim_dir(self, dir):
        if dir is None:
            if "stimuli" in os.listdir(self._data_dir):  # data2bids can be called at the parent folder
                dir = os.path.join(self._data_dir, "stimuli")
            elif "stimuli" in os.listdir(os.path.dirname(self._data_dir)):  # or subject folder level
                dir = os.path.join(os.path.dirname(self._data_dir), "stimuli")
            else:
                self.stim_dir = None
                return
            if not os.path.isdir(os.path.join(self._bids_dir, "stimuli")):
                os.mkdir(os.path.join(self._bids_dir, "stimuli"))
        for item in os.listdir(dir):
            shutil.copyfile(os.path.join(dir, item), os.path.join(self._bids_dir, "stimuli", item))
        self.stim_dir = dir
        self._ignore.append(dir)

    def set_channels(self, channels):
        try:
            headers_dict = self._config["ieeg"]["headerData"]
        except KeyError:
            headers_dict = None
        self.channels = {}
        self.sample_rate = {}
        part_match = None
        task_label_match = None
        if self._data_dir:
            for root, _, files in os.walk(self._data_dir):
                # ignore BIDS directories and stimuli
                files[:] = [f for f in files if not self.check_ignore(os.path.join(root, f))]
                i = 1
                while files:
                    file = files.pop(0)
                    src = os.path.join(root, file)
                    if not part_match == match_regexp(self._config["partLabel"], file):
                        part_match = match_regexp(self._config["partLabel"], file)
                        self.channels[part_match] = []
                    part_match_z = self.part_check(part_match)[1]
                    df = None
                    for name, var in self._config["ieeg"]["channels"].items():
                        if name in src:
                            df = mat2df(src, var)
                            if "highpass_cutoff" in df.columns.to_list():
                                df = df.rename(columns={"highpass_cutoff": "high_cutoff"})
                            if "lowpass_cutoff" in df.columns.to_list():
                                df = df.rename(columns={"lowpass_cutoff": "low_cutoff"})
                    name_gen = self.generate_names(src, part_match=part_match, verbose=False)
                    if name_gen is not None and name_gen[-2] is not None:
                        task_label_match = name_gen[-2]
                    if df is None:
                        continue
                    elif task_label_match is None:
                        i += 1
                        if i > 40:
                            raise NameError("No tasks could be found in files:\n", os.listdir(os.path.dirname(src)))
                        else:
                            files.append(file)
                            continue
                    else:
                        i = 1
                    filename = os.path.join(self._bids_dir, "sub-" + part_match_z,
                                            "sub-" + part_match_z + "_task-" + task_label_match + "_channels.tsv")
                    os.mkdir(os.path.dirname(filename))
                    df.to_csv(filename, sep="\t", index=False)
                    if part_match not in headers_dict.keys():
                        try:
                            var = headers_dict["default"]
                            if isinstance(var, str):
                                var = [var]
                            self.channels[part_match] = self.channels[part_match] + [v for v in var if
                                                                                     v not in self.channels[part_match]]
                        except KeyError:
                            pass
                    for name, var in headers_dict.items():
                        if name == part_match:
                            if isinstance(var, str):
                                var = [var]
                            self.channels[part_match] = self.channels[part_match] + [v for v in var if
                                                                                     v not in self.channels[part_match]]
                        elif re.match(".*?" + part_match + ".*?" + name,
                                      src):  # some sort of checking for .mat or txt files?
                            if name.endswith(".mat") and re.match(".*?" + part_match + ".*?" + name, src):
                                self.channels[part_match] = self.channels[part_match] + mat2df(src, var).tolist()
                                try:
                                    self.sample_rate[part_match] = mat2df(src, self._config['ieeg']['sampleRate']).iloc[
                                        0]
                                except KeyError:
                                    self.sample_rate[part_match] = None
                                except AttributeError:
                                    raise IndexError(self._config['ieeg']['sampleRate'] + " not found in " + src)
                                self._ignore.append(src)
                            elif name.endswith((".txt", ".csv", ".tsv")) and re.match(".*?" + part_match + ".*?" + name,
                                                                                      src):
                                f = open(name, 'r')
                                content = f.read()
                                f.close()
                                self.channels[part_match] = self.channels[part_match] + content.split()
                            elif name.endswith(tuple(self._config['dataFormat'])) and re.match(
                                    ".*?" + part_match + ".*?" + name, src):
                                raise NotImplementedError(
                                    src + "\nthis file format does not yet support {ext} files for "
                                          "channel labels".format(ext=os.path.splitext(src)[1]))
        if isinstance(channels, str) and channels not in channels[part_match]:
            self.channels[part_match] = self.channels[part_match] + [channels]
        elif channels is not None:
            self.channels[part_match] = self.channels[part_match] + [c for c in channels if
                                                                     c not in self.channels[part_match]]
        for i, chan in enumerate(self.channels[part_match]):
            if re.match(".*\.xls.*", chan):
                trig_label = trigger_from_excel(chan, part_match)
            if (signal["label"] or i) == trig_label:
                signal["label"] = "Trigger"

    def set_overwrite(self, overwrite):
        self._is_overwrite = overwrite

    def set_verbosity(self, verbose):
        self._is_verbose = verbose

    def set_multi_echo(self, multi_echo):  # if -m flag is called
        if multi_echo is None:
            self.is_multi_echo = False
        else:
            self.is_multi_echo = True
            if not multi_echo:
                self._multi_echo = 0
            else:
                self._multi_echo = multi_echo

    def set_DICOM(self, ddir):  # triggers only if dicom flag is called and therefore _data_dir is None
        if self._data_dir is None:
            self._data_dir = os.path.dirname(self._bids_dir)
            subdirs = [x[0] for x in os.walk(ddir)]
            files = [x[2] for x in os.walk(ddir)]
            sub_num = str(dicom.read_file(os.path.join(subdirs[1], files[1][0]))[0x10, 0x20].value).split("_", 1)[1]
            sub_dir = os.path.join(os.path.dirname(self._bids_dir),
                                   "sub-{SUB_NUM}".format(SUB_NUM=sub_num))  # destination subdirectory
            if os.path.isdir(sub_dir):
                proc = subprocess.Popen("rm -rf {file}".format(file=sub_dir), shell=True, stdout=subprocess.PIPE)
                proc.communicate()
            os.mkdir(sub_dir)

            if any("medata" in x for x in subdirs):  # copy over and list me data
                melist = [x[2] for x in os.walk(os.path.join(ddir, "medata"))][0]
                runlist = []
                for me in melist:
                    if me.startswith("."):
                        continue
                    runmatch = re.match(r".*run(\d{2}).*", me).group(1)
                    if str(int(runmatch)) not in runlist:
                        runlist.append(str(int(runmatch)))
                    shutil.copyfile(os.path.join(ddir, "medata", me), os.path.join(sub_dir, me))
                self.is_multi_echo = True  # will trigger even if single echo data is in medata folder. Should still  # be okay
            for subdir in subdirs[1:]:  # not including parent folder or /medata, run dcm2niix on non me data
                try:
                    fobj = dicom.read_file(os.path.join(subdir, list(os.walk(subdir))[0][2][0]),
                                           force=True)  # first dicom file of the scan
                    scan_num = str(int(os.path.basename(subdir))).zfill(2)
                except ValueError:
                    continue
                firstfile = [x[2] for x in os.walk(subdir)][0][0]
                # print(str(fobj[0x20, 0x11].value), runlist)
                # running dcm2niix, 
                if str(fobj[0x20, 0x11].value) in runlist:
                    proc = subprocess.Popen(
                        "dcm2niix -z y -f run{SCAN_NUM}_%p_%t_sub{SUB_NUM} -o {OUTPUT_DIR} -s y -b y {DATA_DIR}".format(
                            OUTPUT_DIR=sub_dir, SUB_NUM=sub_num, DATA_DIR=os.path.join(subdir, firstfile),
                            SCAN_NUM=scan_num), shell=True, stdout=subprocess.PIPE)
                    # output = proc.stdout.read()
                    outs, errs = proc.communicate()
                    prefix = re.match(".*/sub-{SUB_NUM}/(run{SCAN_NUM}".format(SUB_NUM=sub_num,
                                                                               SCAN_NUM=scan_num) + r"[^ \(\"\\n\.]*).*",
                                      str(outs)).group(1)
                    for file in os.listdir(sub_dir):
                        mefile = re.match(r"run{SCAN_NUM}(\.e\d\d)\.nii".format(SCAN_NUM=scan_num), file)
                        if re.match(r"run{SCAN_NUM}\.e\d\d.nii".format(SCAN_NUM=scan_num), file):
                            shutil.move(os.path.join(sub_dir, file),
                                        os.path.join(sub_dir, prefix + mefile.group(1) + ".nii"))
                            shutil.copy(os.path.join(sub_dir, prefix + ".json"),
                                        os.path.join(sub_dir, prefix + mefile.group(1) + ".json"))
                    os.remove(os.path.join(sub_dir, prefix + ".nii.gz"))
                    os.remove(os.path.join(sub_dir, prefix + ".json"))
                else:
                    proc = subprocess.Popen(
                        "dcm2niix -z y -f run{SCAN_NUM}_%p_%t_sub{SUB_NUM} -o {OUTPUT_DIR} -b y {DATA_DIR}".format(
                            OUTPUT_DIR=sub_dir, SUB_NUM=sub_num, DATA_DIR=subdir, SCAN_NUM=scan_num), shell=True,
                        stdout=subprocess.PIPE)
                    outs, errs = proc.communicate()
                sys.stdout.write(outs.decode("utf-8"))

            self._multi_echo = runlist
            self._data_dir = os.path.join(os.path.dirname(self._bids_dir), "sub-{SUB_NUM}".format(SUB_NUM=sub_num))
        self._DICOM_path = ddir

    def get_data_dir(self):
        return self._data_dir

    def set_data_dir(self, data_dir, DICOM):  # check if input dir is listed
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
                newdir = self._data_dir + "/BIDS"
            except TypeError:
                print("Error: Please provide input data directory if no BIDS directory...")

        # deleting old BIDS to make room for new
        elif not os.path.basename(bids_dir) == "BIDS":
            newdir = os.path.join(bids_dir, "BIDS")
        else:
            newdir = bids_dir
        if not os.path.isdir(newdir):
            os.mkdir(newdir)
        elif self._is_overwrite:
            force_remove(newdir)
            os.mkdir(newdir)
        self._bids_dir = newdir
        self._ignore.append(newdir)
        # as of BIDS ver 1.6.0, CT is not a part of BIDS, so check for CT files and add to .bidsignore
        self.bidsignore("*_CT.*")

    def get_bids_version(self):
        return self._bids_version

    def bids_validator(self):
        assert self._bids_dir is not None, "Cannot launch bids-validator without specifying bids directory !"
        # try:
        subprocess.check_call(['bids-validator',
                               self._bids_dir])  # except FileNotFoundError:

    def generate_names(self, src_file_path, filename=None,  # function to run through name text and generate metadata
                       part_match=None, sess_match=None, ce_match=None, acq_match=None, echo_match=None,
                       data_type_match=None, task_label_match=None, run_match=None, verbose=None, debug=False):
        if filename is None:
            filename = os.path.basename(src_file_path)
        if part_match is None:
            part_match = match_regexp(self._config["partLabel"], filename)
        if verbose is None:
            verbose = self._is_verbose
        try:
            if re.match(r"^[^\d]{1,3}", part_match):
                part_matches = re.split(r"([^\d]{1,3})", part_match, 1)
                part_match_z = part_matches[1] + str(int(part_matches[2])).zfill(self._config["partLabel"]["fill"])
            else:
                part_match_z = str(int(part_match)).zfill(self._config["partLabel"]["fill"])
        except KeyError:
            pass
        dst_file_path = self._bids_dir + "/sub-" + part_match_z
        new_name = "/sub-" + part_match_z
        SeqType = None
        # Matching the session
        try:
            if sess_match is None:
                sess_match = match_regexp(self._config["sessLabel"], filename)
            dst_file_path = dst_file_path + "/ses-" + sess_match
            new_name = new_name + "_ses-" + sess_match
        except AssertionError:
            if verbose:
                print("No session found for %s" % src_file_path)

        # Matching the run number
        try:
            if run_match is None:
                run_match = match_regexp(self._config["runIndex"], filename)
            try:
                if re.match(r"^[^\d]{1,3}", run_match):
                    run_matches = re.split(r"([^\d]{1,3})", run_match, 1)
                    run_match = run_matches[1] + str(int(run_matches[2])).zfill(self._config["runIndex"]["fill"])
                else:
                    run_match = str(int(run_match)).zfill(self._config["runIndex"]["fill"])
            except KeyError:
                pass

        except AssertionError:
            pass

        # Matching the anat/fmri data type and task
        try:
            if data_type_match is None:
                data_type_match = match_regexp(self._config["anat"], filename, subtype=True)
            dst_file_path = dst_file_path + "/anat"
            self._data_types["anat"] = True
        except (AssertionError, KeyError) as e:
            # If no anatomical, trying functionnal
            try:
                if data_type_match is None:
                    data_type_match = match_regexp(self._config["func"], filename, subtype=True)
                dst_file_path = dst_file_path + "/func"
                self._data_types["func"] = True
                # Now trying to match the task
                try:
                    if task_label_match is None:
                        task_label_match = match_regexp(self._config["func.task"], filename, subtype=True)
                    new_name = new_name + "_task-" + task_label_match
                except AssertionError as e:
                    print("No task found for %s" % src_file_path)
                    if debug:
                        raise e
                    return

            except (AssertionError, KeyError) as e:
                # no functional or anatomical, try ieeg
                try:
                    if data_type_match is None:
                        data_type_match = match_regexp(self._config["ieeg"], filename, subtype=True)
                    dst_file_path = dst_file_path + "/ieeg"
                    self._data_types["ieeg"] = True
                    # Now trying to match the task
                    try:
                        if task_label_match is None:
                            task_label_match = match_regexp(self._config["ieeg.task"], filename, subtype=True)
                        new_name = new_name + "_task-" + task_label_match
                    except AssertionError as e:
                        print("No task found for %s" % src_file_path)
                        if debug:
                            raise e
                        return
                except AssertionError as e:
                    if verbose:
                        print("No anat, func, or ieeg data type found for %s" % src_file_path)
                    if debug:
                        raise e
                    return
                except KeyError as e:
                    print("No anat, func, or ieeg data type found in config file, one of these data types is required")
                    if debug:
                        raise e
                    return

        # if is an MRI
        if dst_file_path.endswith("/func") or dst_file_path.endswith("/anat"):
            try:
                SeqType = str(match_regexp(self._config["pulseSequenceType"], filename, subtype=True))
            except AssertionError:
                if verbose:
                    print("No pulse sequence found for %s" % src_file_path)
            except KeyError:
                if verbose:
                    print("pulse sequence not listed for %s, will look for in file header" % src_file_path)
            try:
                if echo_match is None:
                    echo_match = match_regexp(self._config["echo"], filename)
                new_name = new_name + "_echo-" + echo_match
            except AssertionError:
                if verbose:
                    print("No echo found for %s" % src_file_path)

        # check for optional labels
        try:
            if acq_match is None:
                acq_match = match_regexp(self._config["acq"], filename)
            try:
                if re.match(r"^[^\d]{1,3}", acq_match):
                    acq_matches = re.split(r"([^\d]{1,3})", acq_match, 1)
                    acq_match = acq_matches[1] + str(int(acq_matches[2])).zfill(self._config["acq"]["fill"])
                else:
                    acq_match = str(int(acq_match)).zfill(self._config["acq"]["fill"])
            except KeyError:
                pass

            new_name = new_name + "_acq-" + acq_match
        except (AssertionError, KeyError) as e:
            if verbose:
                print("no optional labels for %s" % src_file_path)
        try:
            if ce_match is None:
                ce_match = match_regexp(self._config["ce"], filename)
            new_name = new_name + "_ce-" + ce_match

        except (AssertionError, KeyError) as e:
            if verbose:
                print("no special contrast labels for %s" % src_file_path)

        if run_match is not None:
            new_name = new_name + "_run-" + run_match

        # Adding the modality to the new filename
        new_name = new_name + "_" + data_type_match

        return (new_name, dst_file_path, part_match, run_match, acq_match,
                echo_match, sess_match, ce_match,
                data_type_match, task_label_match, SeqType)

    def multi_echo_check(self, runnum, src_file=""):  # check to see if run is multi echo based on input
        if self.is_multi_echo:
            if int(runnum) in self._multi_echo:
                return (True)
            else:
                if self._multi_echo == 0:
                    try:
                        match_regexp(self._config["echo"], src_file)
                    except AssertionError:
                        return (False)
                    return (True)
                else:
                    return (False)
        else:
            return (False)

    def get_params(self, folder, echo_num, run_num):  # function to run through DICOMs and get metadata
        # threading?
        if self.is_multi_echo and run_num in self._multi_echo:
            vols_per_time = len(self._config['delayTimeInSec']) - 1
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
                seqlist = []
                for i in list(range(5)):
                    try:
                        seqlist.append(fobj[0x18, (32 + i)].value)
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
                    timings = []
                except NameError:
                    timings = [None] * int(ImagesInAcquisition / vols_per_time)

                RepetitionTime = (
                    (float(fobj[0x18, 0x80].value) / 1000))  # TR value extracted in milliseconds, converted to seconds
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
                    if timings[InStackPositionNumber - 1] is None:
                        timings[InStackPositionNumber - 1] = slice_time_calc(RepetitionTime, InstanceNumber,
                                                                             int(ImagesInAcquisition / vols_per_time),
                                                                             echo)
                    if acquisition_series == "odd-interleaved" or acquisition_series == "even-interleaved":
                        InStackPositionNumber += 2
                        if InStackPositionNumber > ImagesInAcquisition / vols_per_time and acquisition_series == "odd-interleaved":
                            InStackPositionNumber = 2
                        elif InStackPositionNumber > ImagesInAcquisition / vols_per_time and acquisition_series == "even-interleaved":
                            InStackPositionNumber = 1
                    else:
                        InStackPositionNumber += 1
                    InstanceNumber += 1
                return (timings, echo, ScanningSequence, SequenceVariant, SequenceOptions, SequenceName)

    def read_edf(self, file_name, channels=None, extra_arrays=None, extra_signal_headers=None):

        [edfname, dst_path, part_match] = self.generate_names(file_name, verbose=False)[0:3]
        header = highlevel.make_header(patientname=part_match, startdate=datetime.datetime(1, 1, 1))
        edf_name = dst_path + edfname + ".edf"
        d = {str: [], int: []}
        for i in channels:
            d[type(i)].append(i)

        f = EdfReader(file_name)
        chn_nums = d[int] + [i for i, x in enumerate(f.getSignalLabels()) if x in channels]
        f.close()
        chn_nums.sort()

        try:
            check_sep = self._config["eventFormat"]["Sep"]
        except (KeyError, AssertionError) as e:
            check_sep = None

        gc.collect()  # helps with memory

        if check_sep:
            # read edf
            print("Reading " + file_name + "...")
            [array, signal_headers, _] = highlevel.read_edf(file_name, ch_nrs=chn_nums,
                                                            digital=self._config["ieeg"]["digital"], verbose=True)
            if extra_arrays:
                array = array + extra_arrays
            if extra_signal_headers:
                signal_headers = signal_headers + extra_signal_headers
            """
            # replace trigger channels with trigger label ("DC1")
            if part_match in self._config["ieeg"]["headerData"].keys():
                trig_label = self._config["ieeg"]["headerData"][part_match]
            else:
                trig_label = self._config["ieeg"]["headerData"]["default"]
            for i, signal in enumerate(signal_headers):
                # print(re.match(".*\.xls.*", trig_label))
                if re.match(".*\.xls.*", str(trig_label)):
                    trig_label = trigger_from_excel(str(trig_label), part_match)
                if (signal["label"] or i) == trig_label:
                    signal["label"] = "Trigger"
                    """

            return dict(name=file_name, bids_name=edf_name, nsamples=array.shape[1], signal_headers=signal_headers,
                        file_header=header, data=array, reader=f)
        elif channels:
            highlevel.drop_channels(file_name, edf_name, channels, verbose=self._is_verbose)
            return None
        else:
            shutil.copy(file_name, edf_name)
            return None

    def part_check(self, part_match=None, filename=None):
        # Matching the participant label to determine if
        # there exists therein delete previously created BIDS subject files

        assert part_match or filename

        if filename:

            try:
                part_match = match_regexp(self._config["partLabel"], filename)
            except AssertionError:
                print("No participant found for %s" % filename)
            except KeyError as e:
                print("Participant label pattern must be defined")
                raise e

        if re.match(r"^[^\d]{1,3}", part_match):
            part_matches = re.split(r"([^\d]{1,3})", part_match, 1)
            part_match_z = part_matches[1] + str(int(part_matches[2])).zfill(self._config["partLabel"]["fill"])
        else:
            part_match_z = str(int(part_match)).zfill(self._config["partLabel"]["fill"])

        return part_match, part_match_z

    def bidsignore(self, string: str):
        if not os.path.isfile(self._bids_dir + "/.bidsignore"):
            with open(self._bids_dir + "/.bidsignore", 'w') as f:
                f.write(string + "\n")
        else:
            with open(self._bids_dir + "/.bidsignore", "r+") as f:
                if string not in f.read():
                    f.write(string + "\n")

    def run(self):  # main function

        # First we check that every parameters are configured
        if (
                self._data_dir is not None and self._config_path is not None and self._config is not None and self._bids_dir is not None):

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
            # else
            #    shutil.rmtree(self._bids_dir)

            # What is the base format to convert to
            curr_ext = self._config["dataFormat"]
            compress = self._config["compress"]

            # delay time in TR unit (if delay_time = 1, delay_time = repetition_time)
            repetition_time = self._config["repetitionTimeInSec"]
            delaytime = self._config["delayTimeInSec"]

            # dataset_description.json must be included in the folder root foolowing BIDS specs
            if os.path.exists(self._bids_dir + "/dataset_description.json"):
                # with open(dst_file_path + new_name + ".json", 'w') as fst:
                with open(self._bids_dir + "/dataset_description.json") as fst:
                    filedata = json.load(fst)
                with open(self._bids_dir + "/dataset_description.json", 'w') as fst:
                    data = {'Name': self._dataset_name, 'BIDSVersion': self._bids_version}
                    filedata.update(data)
                    json.dump(filedata, fst, ensure_ascii=False, indent=4)
            else:
                with open(self._bids_dir + "/dataset_description.json", 'w') as fst:
                    data = {'Name': self._dataset_name, 'BIDSVersion': self._bids_version}
                    json.dump(data, fst, ensure_ascii=False, indent=4)

            try:
                for key, data in self._config["JSON_files"].items():
                    with open(self._bids_dir + '/' + key, 'w') as fst:
                        json.dump(data, fst, ensure_ascii=False, indent=4)
            except KeyError:
                pass

            # add a README file
            if not os.path.exists(self._bids_dir + "/README"):
                with open(self._bids_dir + "/README", 'w') as fst:
                    data = ""
                    fst.write(data)

            # now we can scan all files and rearrange them
            part_match = None
            part_match_z = None
            for root, _, files in os.walk(self._data_dir, topdown=True):
                # each loop is a new participant so long as participant is top level
                files[:] = [f for f in files if not self.check_ignore(os.path.join(root, f))]
                eeg = []
                dst_file_path_list = []
                names_list = []
                mat_list = []
                run_list = []
                tsv_condition_runs = []
                tsv_fso_runs = []
                d_list = []
                txt_df_list = []
                correct = None
                if not files:
                    continue
                files.sort()
                part_match = None
                i = 0
                while part_match is None:
                    try:
                        part_match, part_match_z = self.part_check(filename=files[i])
                    except:
                        i += 1
                        continue
                if self.channels:
                    if self._is_verbose and self.channels[part_match] is not None:
                        print("Channels for participant " + part_match + " are")
                        print(self.channels[part_match])
                        for i in self._ignore:
                            if part_match in i:
                                print("From " + i)
                if self._is_verbose:
                    print(files)
                while files:  # loops over each participant file
                    file = files.pop(0)
                    if self._is_verbose:
                        print(file)
                    src_file_path = os.path.join(root, file)
                    """
                    dst_file_path = self._bids_dir
                    data_type_match = None
                    new_name = None
                    if re.match(".*?" + ".json", file):
                        try:
                            (new_name, dst_file_path, part_match, run_match, 
                             acq_match, echo_match, sess_match, ce_match, 
                             data_type_match, task_label_match, SeqType) = \
                                self.generate_names(src_file_path,
                                                    part_match=part_match)
                        except TypeError:
                            continue
                        if echo_match is None:
                            echo_match = 0
                        if new_name in names_list:
                            shutil.copy(src_file_path,
                                        dst_file_path + new_name + ".json")
                            # finally, if it is a bold experiment, we need to edit the JSON file using DICOM tags
                            if os.path.exists(dst_file_path + new_name + ".json"):
                                # https://github.com/nipy/nibabel/issues/712, that is why we take the
                                # scanner parameters from the config.json
                                # nib_img = nib.load(src_file_path)
                                # TR = nib_img.header.get_zooms()[3]
                                for foldername in os.listdir(str(self._DICOM_path)):
                                    if run_match.zfill(4) == foldername.zfill(4):
                                        DICOM_filepath = os.path.join(self._DICOM_path, foldername)
                                        slicetimes, echotime, ScanSeq, SeqVar, SeqOpt, SeqName = self.get_params(
                                            str(DICOM_filepath), int(echo_match), int(run_match))

                                    # with open(dst_file_path + new_name + ".json", 'w') as fst:
                                with open(dst_file_path + new_name + ".json", 'r+') as fst:
                                    filedata = json.load(fst)
                                with open(dst_file_path + new_name + ".json", 'w') as fst:
                                    if data_type_match == "bold":
                                        filedata['TaskName'] = task_label_match
                                        filedata['SliceTiming'] = slicetimes
                                        if int(run_match) in self._multi_echo:
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
                                    json.dump(filedata, fst, ensure_ascii=False, indent=4, default=set_default)
                            else:
                                print("Cannot update %s" % (dst_file_path + new_name + ".json"))
                        elif any(re.search("\\.nii", filelist) for filelist in files):
                            files.append(src_file_path)
                        continue
                        """
                    if re.match(".*?" + "\\.mat", file):
                        mat_list.append(src_file_path)
                        continue  # if the file doesn't match the extension, we skip it
                    elif re.match(".*?" + "\\.txt", file):
                        if part_match is None:
                            files.append(file)
                        else:
                            try:
                                df = pd.read_table(src_file_path, header=None, sep="\s+")
                                e = None
                            except Exception as e:
                                df = None
                            txt_df_list.append(dict(name=file, data=df, error=e))
                        continue
                    elif not any(re.match(".*?" + ext, file) for ext in curr_ext):
                        print("Warning : Skipping %s" % src_file_path)
                        continue
                    if self._is_verbose:
                        print("trying %s" % src_file_path)
                    try:
                        (new_name, dst_file_path, part_match, run_match, acq_match, echo_match, sess_match, ce_match,
                         data_type_match, task_label_match, _) = self.generate_names(src_file_path,
                                                                                     part_match=part_match)
                    except TypeError as problem:  #
                        print("\nIssue in generate names")
                        print("problem with %s:" % src_file_path, problem, "\n")

                        continue

                    # Creating the directory where to store the new file
                    if not os.path.exists(dst_file_path):
                        os.makedirs(dst_file_path)

                    # print(data_type_match)
                    # finally, if the file is not nifti
                    if dst_file_path.endswith("/func") or dst_file_path.endswith("/anat"):
                        # we convert it using nibabel
                        if not any(file.endswith(ext) for ext in [".nii", ".nii.gz"]):
                            # check if .nii listed in config file, not if file ends with .nii
                            # loading the original image
                            nib_img = nib.load(src_file_path)
                            nib_affine = np.array(nib_img.affine)
                            nib_data = np.array(nib_img.dataobj)

                            # create the nifti1 image
                            # if minc format, invert the data and change the affine transformation
                            # there is also an issue on minc headers
                            if file.endswith(".mnc"):
                                if len(nib_img.shape) > 3:
                                    nib_affine[0:3, 0:3] = nib_affine[0:3, 0:3]
                                    rot_z(np.pi / 2)
                                    rot_y(np.pi)
                                    rot_x(np.pi / 2)
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

                            # saving the image
                            nib.save(nifti_img, dst_file_path + new_name + ".nii.gz")

                        # if it is already a nifti file, no need to convert it so we just copy rename
                        if file.endswith(".nii.gz"):
                            shutil.copy(src_file_path, dst_file_path + new_name + ".nii.gz")
                        elif file.endswith(".nii"):
                            shutil.copy(src_file_path, dst_file_path + new_name + ".nii")
                            # compression just if .nii files
                            if compress is True:
                                print("zipping " + file)
                                with open(dst_file_path + new_name + ".nii", 'rb') as f_in:
                                    with gzip.open(dst_file_path + new_name + ".nii.gz", 'wb',
                                                   self._config["compressLevel"]) as f_out:
                                        shutil.copyfileobj(f_in, f_out)
                                os.remove(dst_file_path + new_name + ".nii")

                    elif dst_file_path.endswith("/ieeg"):
                        remove_src_edf = True
                        headers_dict = self.channels[part_match]
                        if file.endswith(".edf"):
                            remove_src_edf = False
                        elif file.endswith(".edf.gz"):
                            with gzip.open(src_file_path, 'rb', self._config["compressLevel"]) as f_in:
                                with open(src_file_path.rsplit(".gz", 1)[0], 'wb') as f_out:
                                    shutil.copyfileobj(f_in, f_out)
                        elif not self._config["ieeg"]["binary?"]:
                            raise NotImplementedError(
                                "{file} file format not yet supported. If file is binary format, please indicate so "
                                "and what encoding in the config.json file".format(file=file))
                        elif headers_dict and any(".mat" in i for i in files) and self.sample_rate[
                            part_match] is not None:
                            # assume has binary encoding
                            try:  # open binary file and write decoded numbers as array where rows = channels
                                # check if zipped
                                if file.endswith(".gz"):
                                    with gzip.open(src_file_path, 'rb', self._config["compressLevel"]) as f:
                                        data = np.frombuffer(f.read(),
                                                             dtype=np.dtype(self._config["ieeg"]["binaryEncoding"]))
                                else:
                                    with open(src_file_path, mode='rb') as f:
                                        data = np.fromfile(f, dtype=self._config["ieeg"]["binaryEncoding"])
                                array = np.reshape(data, [len(headers_dict), -1],
                                                   order='F')  # byte order is Fortran encoding, dont know why
                                signal_headers = highlevel.make_signal_headers(headers_dict,
                                                                               sample_rate=self.sample_rate[part_match],
                                                                               physical_max=np.amax(array),
                                                                               physical_min=(np.amin(array)))
                                print("converting binary" + src_file_path + " to edf" + os.path.splitext(src_file_path)[
                                    0] + ".edf")
                                highlevel.write_edf(os.path.splitext(src_file_path)[0] + ".edf", array, signal_headers,
                                                    digital=self._config["ieeg"]["digital"])
                            except OSError as e:
                                print("eeg file is either not detailed well enough in config file or file type not yet "
                                      "supported")
                                raise e
                        else:
                            raise FileNotFoundError("{file} header could not be found".format(file=file))

                        f = EdfReader(os.path.splitext(src_file_path)[0] + ".edf")
                        # check for extra channels in data, not working in other file modalities
                        extra_arrays = []
                        extra_signal_headers = []
                        if any(len(mat2df(os.path.join(root, fname))) == f.samples_in_file(0) for fname in
                               [i for i in files if i.endswith(".mat")]) or any(
                            len(mat2df(os.path.join(root, fname))) == f.samples_in_file(0) for fname in
                            [i for i in mat_list if i.endswith(".mat")]):

                            for fname in [i for i in files + mat_list if i.endswith(".mat")]:
                                sig_len = f.samples_in_file(0)
                                if not os.path.isfile(fname):
                                    fname = os.path.join(root, fname)
                                if mat2df(fname) is None:
                                    continue
                                elif len(mat2df(fname)) == sig_len:
                                    if fname in files:
                                        files.remove(fname)
                                    if fname in mat_list:
                                        mat_list.remove(fname)
                                    df = pd.DataFrame(mat2df(fname))
                                    for cols in df.columns:
                                        extra_arrays = np.vstack([extra_arrays, df[cols]])
                                        extra_signal_headers.append(
                                            highlevel.make_signal_header(os.path.splitext(os.path.basename(fname))[0],
                                                                         sample_rate=self.sample_rate[part_match]))
                                elif sig_len * 0.99 <= len(mat2df(fname)) <= sig_len * 1.01:
                                    raise BufferError(
                                        file + "of size" + sig_len + "is not the same size as" + fname + "of size" + len(
                                            mat2df(fname)))
                        f.close()
                        # read edf and either copy data to BIDS file or save data as dict for writing later
                        eeg.append(
                            self.read_edf(os.path.splitext(src_file_path)[0] + ".edf", headers_dict, extra_arrays,
                                          extra_signal_headers))
                        if remove_src_edf:
                            if self._is_verbose:
                                print("Removing " + os.path.splitext(src_file_path)[0] + ".edf")
                            os.remove(os.path.splitext(src_file_path)[0] + ".edf")

                    # move the sidecar from input to output
                    names_list.append(new_name)
                    dst_file_path_list.append(dst_file_path)
                    try:
                        if run_match is not None:
                            run_list.append(int(run_match))
                    except UnboundLocalError:
                        pass

                if d_list:
                    self.convert_1D(run_list, d_list, tsv_fso_runs, tsv_condition_runs, names_list, dst_file_path_list)

                if mat_list:  # deal with remaining .mat files
                    self.mat2tsv(mat_list)

                if txt_df_list:
                    for txt_df_dict in txt_df_list:
                        if self._config["coordsystem"] in txt_df_dict["name"]:
                            if txt_df_dict["error"] is not None:
                                raise txt_df_dict["error"]
                            df = txt_df_dict["data"]
                            df.columns = ["name1", "name2", "x", "y", "z", "hemisphere", "del"]
                            df["name"] = df["name1"] + df["name2"].astype(str).str.zfill(2)
                            df["hemisphere"] = df["hemisphere"] + df["del"]
                            df = df.drop(columns=["name1", "name2", "del"])
                            df = pd.concat([df["name"], df["x"], df["y"], df["z"], df["hemisphere"]], axis=1)
                            df.to_csv(
                                self._bids_dir + "/sub-" + part_match_z + "/sub-" + part_match_z + "_space-Talairach_electrodes.tsv",
                                sep="\t", index=False)
                        elif self._config["eventFormat"]["AudioCorrection"] in txt_df_dict["name"]:
                            if txt_df_dict["error"] is not None:
                                raise txt_df_dict["error"]
                            correct = txt_df_dict["data"]
                        else:
                            print("skipping " + txt_df_dict["name"])

                # check final file set
                for new_name in names_list:
                    print(new_name)
                    file_path = dst_file_path_list[names_list.index(new_name)]
                    full_name = file_path + new_name + ".edf"
                    task_match = re.match(".*_task-(\w*)_.*", full_name)
                    if task_match:
                        task_label_match = task_match.group(1)
                    # split any edfs according to tsvs
                    pattern = "{}(?:_acq-{})?_run-{}_events\.tsv".format(new_name.split("_ieeg")[0].split("/", 1)[1],
                                                                         self._config["acq"]["content"][0],
                                                                         self._config["runIndex"]["content"][0])
                    match_set = [re.match(pattern, set_file) for set_file in os.listdir(file_path)]
                    if new_name.endswith("_ieeg") and any(match_set):  # if edf is not yet split

                        if self._is_verbose:
                            print("Reading for split... ")
                        if full_name in [i["bids_name"] for i in eeg]:
                            eeg_dict = eeg[[i["bids_name"] for i in eeg].index(full_name)]
                        else:
                            raise LookupError(
                                "This error should not have been raised, was edf file " + full_name + " ever written?",
                                [i["name"] for i in eeg])
                        [array, signal_headers, header] = [eeg_dict["data"], eeg_dict["signal_headers"],
                                                           eeg_dict["file_header"]]
                        start_nums = []
                        matches = []
                        for file in sorted(os.listdir(file_path)):
                            match_tsv = re.match(new_name.split("_ieeg", 1)[0].split("/", 1)[1] + "(?:_acq-" +
                                                 self._config["acq"]["content"][0] + ")?_run-(" +
                                                 self._config["runIndex"]["content"][0] + ")_events.tsv", file)
                            if match_tsv:
                                df = pd.read_csv(os.path.join(file_path, file), sep="\t", header=0)
                                # converting signal start and end to correct sample rate for data
                                eval_col = eval_df(df, self._config["eventFormat"]["Timing"]["end"], self.stim_dir)
                                end_num = str2num(eval_col.iloc[-1])
                                i = -1
                                while not is_number(end_num):
                                    i -= 1
                                    end_num = str2num(eval_col.iloc[i])

                                eval_col = eval_df(df, self._config["eventFormat"]["Timing"]["start"], self.stim_dir)
                                start_num = eval_col.iloc[0]
                                i = 0
                                while not is_number(start_num):
                                    i += 1
                                    start_num = str2num(eval_col.iloc[i])

                                num_list = [round(
                                    (float(x) / float(self._config["eventFormat"]["SampleRate"])) * signal_headers[0][
                                        "sample_rate"]) for x in (start_num, end_num)]
                                start_nums.append(tuple(num_list))
                                matches.append(match_tsv)
                        for i in range(len(start_nums)):
                            if i == 0:
                                start = 0
                                practice = os.path.join(file_path,
                                                        "practice" + new_name.split("_ieeg", 1)[0] + "_ieeg.edf")
                                if not os.path.isfile(practice) and self._config["split"]["practice"]:
                                    os.makedirs(os.path.join(file_path, "practice"), exist_ok=True)
                                    highlevel.write_edf(practice, np.split(array, [0, start_nums[0][0]], axis=1)[1],
                                                        signal_headers, header, digital=self._config["ieeg"]["digital"])
                                    self.bidsignore("*practice*")
                            else:
                                start = start_nums[i - 1][1]

                            if i == len(start_nums) - 1:
                                end = array.shape[1]
                            else:
                                end = start_nums[i + 1][0]
                            new_array = np.split(array, [start, end], axis=1)[1]
                            tsv_name: str = os.path.join(file_path, matches[i].string)
                            edf_name: str = os.path.join(file_path,
                                                         matches[i].string.split("_events.tsv", 1)[0] + "_ieeg.edf")
                            full_name = os.path.join(file_path, new_name.split("/", 1)[1] + ".edf")
                            if self._is_verbose:
                                print(full_name + "(Samples[" + str(start) + ":" + str(end) + "]) ---> " + edf_name)
                            highlevel.write_edf(edf_name, new_array, signal_headers, header,
                                                digital=self._config["ieeg"]["digital"])
                            df = pd.read_csv(tsv_name, sep="\t", header=0)
                            os.remove(tsv_name)
                            # all column manipulation and math in frame2bids
                            df_new = self.frame2bids(df, self._config["eventFormat"]["Events"],
                                                     self.sample_rate[part_match], correct, start)
                            df_new.to_csv(tsv_name, sep="\t", index=False, na_rep="n/a")
                            # dont forget .json files!
                            self.write_sidecar(edf_name)
                            self.write_sidecar(tsv_name)
                        continue
                    # write JSON file for any missing files
                    self.write_sidecar(file_path + new_name)

                # write any indicated .json files
                try:
                    json_list = self._config["JSON_files"]
                except KeyError:
                    json_list = dict()
                for jfile, contents in json_list.items():
                    print(part_match_z, task_label_match, jfile)
                    file_name = os.path.join(self._bids_dir, "sub-" + part_match_z,
                                             "sub-" + part_match_z + "_task-" + task_label_match + "_" + jfile)
                    with open(file_name, "w") as fst:
                        json.dump(contents, fst)
            # Output
            if self._is_verbose:
                tree(self._bids_dir)

            # Finally, we check with bids_validator if everything went alright (This wont work)  # self.bids_validator()

        else:
            print("Warning: No parameters are defined !")

    def write_sidecar(self, full_file):
        if full_file.endswith(".tsv"):  # need to search BIDS specs for list of possible known BIDS columns
            data = dict()
            df = pd.read_csv(full_file, sep="\t")
            return
        elif os.path.dirname(full_file).endswith("/ieeg"):
            if not full_file.endswith(".edf"):
                full_file = full_file + ".edf"
            entities = layout.parse_file_entities(full_file)
            f = EdfReader(full_file)
            if f.annotations_in_file == 0:
                description = "n/a"
            elif f.getPatientAdditional():
                description = f.getPatientAdditional()
            elif f.getRecordingAdditional():
                description = f.getRecordingAdditional()
            elif any((not i.size == 0) for i in f.readAnnotations()):
                description = [i for i in f.readAnnotations()]
                print("description:", description)
            else:
                raise SyntaxError(full_file + "was not annotated correctly")
            signals = [sig for sig in f.getSignalLabels() if "Trigger" not in sig]
            data = dict(TaskName=entities['task'], InstitutionName=self._config["institution"],
                        iEEGReference=description, SamplingFrequency=int(f.getSignalHeader(0)["sample_rate"]),
                        PowerLineFrequency=60, SoftwareFilters="n/a", ECOGChannelCount=len(signals),
                        TriggerChannelCount=1, RecordingDuration=f.file_duration)

        elif os.path.dirname(full_file).endswith("/anat"):
            entities = layout.parse_file_entities(full_file + ".nii.gz")
            if entities["suffix"] == "CT":
                data = {}
            elif entities["suffix"] == "T1w":
                data = {}
            else:
                raise NotImplementedError(full_file + "is not yet accounted for")
        else:
            data = {}
        if not os.path.isfile(os.path.splitext(full_file)[0] + ".json"):
            with open(os.path.splitext(full_file)[0] + ".json", "w") as fst:
                json.dump(data, fst)

    def frame2bids(self, df: pd.DataFrame, events: Union[dict, List[dict]], data_sample_rate=None,
                   audio_correction=None, start_at=0):
        new_df = None
        if isinstance(events, dict):
            events = list(events)
        event_order = 0
        for event in events:
            event_order += 1
            temp_df = pd.DataFrame()
            for key, value in event.items():
                if key == "stim_file":
                    temp_df["stim_file"] = df[value]
                    temp_df["duration"] = eval_df(df, value, self.stim_dir)
                else:
                    temp_df[key] = eval_df(df, value)
            if "trial_num" not in temp_df.columns:
                temp_df["trial_num"] = [1 + i for i in list(range(temp_df.shape[0]))]
            '''
            if "duration" not in temp_df.columns:
                if "stim_file" in temp_df.columns:
                    temp = []
                    t_correct = []
                    for _, fname in temp_df["stim_file"].iteritems():
                        if fname.endswith(".wav"):
                            if self.stim_dir is not None:
                                fname = os.path.join(self.stim_dir, fname)
                                dir = self.stim_dir
                            else:
                                dir = self._data_dir
                            try:
                                frames, data = wavfile.read(fname)
                            except FileNotFoundError as e:
                                print(fname + " not found in current directory or in " + dir)
                                raise e
                            if audio_correction is not None:
                                correct = audio_correction.set_index(0).squeeze()[os.path.basename(
                                    os.path.splitext(fname)[0])] * self._config["eventFormat"]["SampleRate"]
                            else:
                                correct = 0
                            duration = (data.size / frames) * self._config["eventFormat"]["SampleRate"]
                        else:
                            raise NotImplementedError("current build only supports .wav stim files")
                        temp.append(duration)
                        t_correct.append(correct)
                    temp_df["duration"] = temp
                    # audio correction
                    if t_correct:
                        temp_df["correct"] = t_correct
                        temp_df["duration"] = temp_df.eval("duration - correct")
                        temp_df["onset"] = temp_df.eval("onset + correct")
                        temp_df = temp_df.drop(columns=["correct"])
                else:
                    raise LookupError("duration of event or copy of audio file required but not found in " +
                                      self._config_path)
            '''
            temp_df["event_order"] = event_order
            if new_df is None:
                new_df = temp_df
            else:
                new_df = new_df.append(temp_df, ignore_index=True, sort=False)

        for name in ["onset", "duration"]:
            if not (pd.api.types.is_float_dtype(new_df[name]) or pd.api.types.is_integer_dtype(new_df[name])):
                new_df[name] = pd.to_numeric(new_df[name], errors="coerce")
        if data_sample_rate is None:
            # onset is timing of even onset (in seconds)
            new_df["onset"] = new_df["onset"] / self._config["eventFormat"]["SampleRate"]
        else:
            # sample is in exact sample of event onset (at eeg sample rate)
            new_df["sample"] = (new_df["onset"] / self._config["eventFormat"][
                "SampleRate"] * data_sample_rate) - start_at
            # onset is timing of even onset (in seconds)
            new_df["onset"] = new_df["sample"] / data_sample_rate
            # round sample to nearest frame
            new_df["sample"] = pd.to_numeric(new_df["sample"].round(), errors="coerce", downcast="integer")
        # duration is duration of event (in seconds)
        new_df["duration"] = new_df["duration"] / self._config["eventFormat"]["SampleRate"]

        if self._is_verbose:
            print(new_df.sort_values(["trial_num", "event_order"]).drop(columns="event_order"))

        return new_df.sort_values(["trial_num", "event_order"]).drop(columns="event_order")

    def mat2tsv(self, mat_files):
        part_match = None
        written = True
        is_separate = None
        for mat_file in mat_files:

            if not match_regexp(self._config["partLabel"],
                                mat_file) == part_match:  # initialize dataframe if new participant
                if written:
                    df = pd.DataFrame()
                elif not part_match == match_regexp(self._config["partLabel"], mat_file):
                    b_index = [j not in df.columns.values.tolist() for j in self._config["eventFormat"]["Sep"]].index(
                        True)
                    raise FileNotFoundError("{config} variable was not found in {part}'s event files".format(
                        config=list(self._config["eventFormat"]["Sep"].values())[b_index], part=part_match))
            try:
                part_match = match_regexp(self._config["partLabel"], mat_file)
            except AssertionError:
                raise SyntaxError("file: {filename} has no matching {config}\n".format(filename=mat_file, config=
                self._config["content"][:][0]))
            df_new = mat2df(mat_file, self._config["eventFormat"]["Labels"])
            # check to see if new data is introduced. If not then keep searching
            if isinstance(df_new, pd.Series):
                df_new = pd.DataFrame(df_new)
            if df_new.shape[0] > df.shape[0]:
                df = pd.concat([df[df.columns.difference(df_new.columns)], df_new], axis=1)  # auto filters duplicates
            elif df_new.shape[0] == df.shape[0]:
                df = pd.concat([df, df_new[df_new.columns.difference(df.columns)]], axis=1)  # auto filters duplicates
            else:
                continue
            written = False

            if self._is_verbose:
                print(df)
            try:
                if self._config["eventFormat"]["IDcol"] in df.columns.values.tolist():  # test if edfs should be
                    # separated by block or not
                    if len(df[self._config["eventFormat"]["IDcol"]].unique()) == 1 and self._config["split"][
                        "Sep"] not in ["all", True] or not self._config["split"]["Sep"]:
                        # CHANGE this in case literal name doesn't change
                        is_separate = False
                        print("Warning: data may have been lost if file ID didn't change but the recording session did")
                        # construct fake orig data name to run through name generator
                        # fix this as well so it works for all data types and modalities
                        match_name = mat_file.split(os.path.basename(mat_file))[0] + \
                                     df[self._config["eventFormat"]["IDcol"]][0] + self._config["ieeg"]["content"][0][1]
                    else:  # this means there was more than one recording session. In this case we will separate each
                        # trial block into a separate "run"
                        is_separate = True
                else:
                    continue
            except KeyError:
                match_name = mat_file

            # write the tsv from the dataframe
            # if not changed: check to see if there is anything new to write
            if is_separate:
                if not all(j in df.columns.values.tolist() for j in self._config["eventFormat"]["Sep"].values()):
                    if self._is_verbose:
                        print(mat_file)
                    continue

                # make sure numbers do not repeat when not wanted
                df_unique = df.filter(self._config["eventFormat"]["Sep"].values()).drop_duplicates()
                for i in range(df_unique.shape[0])[1:]:
                    for j in self._config["eventFormat"]["Sep"].keys():
                        jval = self._config["eventFormat"]["Sep"][j]
                        try:
                            if self._config[j]["repeat"] is False:
                                try:  # making sure actual key errors get caught
                                    if df_unique[jval].iat[i] in df_unique[jval].tolist()[:i]:
                                        df_unique[jval].iat[i] = str(int(max(df_unique[jval].tolist())) + 1)
                                except KeyError as e:
                                    raise ValueError(e)
                            else:
                                continue
                        except KeyError:
                            continue

                tupelist = list(
                    df.filter(self._config["eventFormat"]["Sep"].values()).drop_duplicates().itertuples(index=False))
                for i in range(len(tupelist)):  # iterate through every block
                    nindex = (df.where(
                        df.filter(self._config["eventFormat"]["Sep"].values()) == tupelist[i]) == df).filter(
                        self._config["eventFormat"]["Sep"].values()).all(axis=1)
                    match_name = mat_file.split(os.path.basename(mat_file))[0] + str(
                        df[self._config["eventFormat"]["IDcol"]][nindex].iloc[0])
                    for k in self._config["eventFormat"]["Sep"].keys():
                        if k in self._config.keys():
                            data = str(df_unique[self._config["eventFormat"]["Sep"][k]].iloc[i])
                            match_name = match_name + gen_match_regexp(self._config[k], data)

                    # fix this to check for data type
                    match_name = match_name + self._config["ieeg"]["content"][0][1]
                    item = self.generate_names(match_name, verbose=False)
                    if item is not None:
                        (new_name, dst_file_path) = item[0:2]
                    else:
                        self.generate_names(match_name, verbose=True, debug=True)
                        raise
                    writedf = df.loc[nindex]
                    if self._is_verbose:
                        print(mat_file, "--->", dst_file_path + new_name.split("ieeg")[0] + "events.tsv")
                    writedf.to_csv(dst_file_path + new_name.split("ieeg")[0] + "events.tsv", sep="\t", index=False)
            else:
                (new_name, dst_file_path) = self.generate_names(match_name, verbose=False)[0:2]
                if self._is_verbose:
                    print(mat_file, "--->", dst_file_path + new_name.split("ieeg")[0] + "events.tsv")
                df.to_csv(dst_file_path + new_name.split("ieeg")[0] + "events.tsv", sep="\t", index=False)
            written = True
    """
    def convert_1D(self, run_list, d_list, tsv_fso_runs, tsv_condition_runs, names_list, dst_file_path_list):
        # This section is for converting .1D files to tsv event files. If you have the 1D files that's great,
        # but chances are you have some other format if this is the case,I recommend
        # https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/05-task-events.html
        # so that you can make BIDS compliant event files
        fields = list(list() for _ in range(max(run_list)))
        categories = list(list() for _ in range(max(run_list)))
        writenames = list(list() for _ in range(max(run_list)))
        n = 0  # creating variables to save and write from
        for d_file in d_list:
            # print(d_file)
            n += 1

            try:
                category = re.search("-[0-9]{4}-[0-9]{1,2}-(.*)\\.1D", d_file).group(
                    1)  # search filename for category label
            except AttributeError:
                try:
                    category = re.search("-[0-9]{4}-(.{1,2}-?.*)\\.1D", d_file).group(1)
                except AttributeError:
                    print(d_file + " has no pattern matching: -####-(????)")
                    continue
            nfso = 0
            ncon = 0
            with open(d_file) as lines:  # loop through .tsv file line by line (each is a different run)
                for line in lines:
                    if "fso-" in d_file:
                        try:
                            runnum = int(tsv_fso_runs[nfso])
                            nfso += 1
                        except IndexError:
                            print('Error, index was %s while list was:' % str(nfso))
                            print(tsv_fso_runs)
                            continue
                    elif "condition-" in d_file:
                        try:
                            runnum = int(tsv_condition_runs[ncon])
                            ncon += 1
                        except IndexError:
                            print('Error, index was %s while list was:' % str(ncon))
                            print(tsv_condition_runs)
                            continue
                    else:
                        continue
                    i = 0
                    for name in names_list:
                        try:
                            if runnum is int(re.search("run-([0-9]{2})", name).group(1)):
                                if re.match(".*?" + "_bold" + ".*?", name):
                                    name = name.replace("_bold", "")
                                    if re.match(".*?" + "_echo-[0-9]" + ".*?", name):
                                        name = name.replace(re.search("(_echo-[0-9]{2})", name).group(1), "")
                                for field in line.strip("\\n").split():  # saving the data to variables to write later
                                    if field != '0' and field != '1':
                                        fields[runnum - 1].append(float(field))
                                        categories[runnum - 1].append(category)
                                        writenames[runnum - 1].append(dst_file_path_list[i] + name)
                                break
                            i += 1
                        except AttributeError:
                            print(str(runnum) + "is not in this list:")
        for j in range(max(run_list)):  # actually writing the file
            if fields[j]:
                categories[j] = [categories[j] for _, categories[j] in sorted(zip(fields[j], categories[j]))]
                fields[j].sort()
                for i in range(len(writenames[j]) + 1):
                    tsvnames = []
                    if self.multi_echo_check(j + 1):
                        for k in range((len(self._config["delayTimeInSec"]) - 1)):
                            tsvnames.append("_echo-" + str(k + 1).zfill(2) + "_events.tsv")
                    else:
                        tsvnames.append("_events.tsv")
                    for ending in tsvnames:
                        if i == 0:
                            with open(writenames[j][0] + ending, 'a') as out_file:
                                tsv_writer = csv.writer(out_file, delimiter='\t')
                                tsv_writer.writerow(['onset', 'duration', 'trial_type'])  # ,'TR_condition'])
                        else:
                            if i < len(writenames[j]):
                                duration = float(fields[j][i]) - float(fields[j][i - 1])
                            with open(writenames[j][i - 1] + ending, 'a') as out_file:
                                tsv_writer = csv.writer(out_file, delimiter='\t')
                                tsv_writer.writerow(
                                    [fields[j][i - 1], duration, categories[j][i - 1]])  # ,TRfields[j][i-1]])
    """

def main():
    args = get_parser().parse_args()
    data2bids = Data2Bids(**vars(args))
    data2bids.run()


if __name__ == '__main__':
    main()
