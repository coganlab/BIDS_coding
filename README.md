# Work in Progress
See issues for updates on code completion progress
![example workflow](https://github.com/coganlab/BIDS_coding/actions/workflows/Ubuntu_test.yml/badge.svg)
![example workflow](https://github.com/coganlab/BIDS_coding/actions/workflows/Windows_test.yml/badge.svg)

![example workflow](https://github.com/coganlab/BIDS_coding/actions/workflows/Ubuntu_test.yml/badge.svg)
![example workflow](https://github.com/coganlab/BIDS_coding/actions/workflows/Windows_test.yml/badge.svg)

# BIDS_coding
These scripts are intended for the creation and manipulation of BIDS compliant IEEG data set to the new [specifications](https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/04-intracranial-electroencephalography.html). Currently focused on EEG data type conversion, although multi-echo MRI data is also supported. For more conventional fMRI type BIDS conversions it is recommended you first look at [BIDScoin](https://github.com/Donders-Institute/bidscoin) as it has great general coverage than this repository.

Each python script can be run repreatedly using an iterator shell script like the one within the bids converter.
They can also be run in the command line and will automatically iterate through a whole dataset if the top folder is indicated in the command.

BIDS_converter methodology is based off of [this project](https://github.com/SIMEXP/Data2Bids)

# Dependencies 
Software (as needed only):
Afni, Freesurfer, Fsl, Anaconda (python 3.8)

### Python packages: 
boto3, pathlib, pybids, pydicom, nipype, pip, tedana, scipy

### Optional python packages
[bids-validator](https://github.com/bids-standard/bids-validator)

### Ubuntu packages:
[dcm2niix](https://github.com/rordenlab/dcm2niix), pigz

# Host Requirements

### Linux:
xauth

### Mac:
xQuartz

# The Lab
https://www.coganlab.org/
