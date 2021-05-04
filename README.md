# Work in Progress
See issues for update on code completion progress

# BIDS_coding
These scripts are intended for the creation and manipulation of BIDS compliant IEEG data set to the new [specifications](https://bids-specification.readthedocs.io/en/stable/04-modality-specific-files/04-intracranial-electroencephalography.html).

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
