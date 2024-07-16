# Work in Progress
See issues for updates on code completion progress

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


### BIDS Coding (makes BIDS files)
1. Run makeTrials_GL.m (/Users/jinjiang-macair/Library/CloudStorage/Box-Box/CoganLab/D_Data/GlobalLocal/makeTrials_GL.m) with the subject id (D##) and date (YYMMDD) to create a Trials.mat file for that subject. Need to add makeTrials_GL.m to path as well as MATLAB-env folder (/Users/jinjiang-macair/Documents/MATLAB/MATLAB-env). If MATLAB-env isn't there, you can clone it from https://github.com/coganlab/MATLAB-env
2. Run BIDS_convert_wsl.sh (within BIDS_coding repository, global local branch)  
   2a. To install dependencies, need to ```conda create env environment.yml``` on Mac if not already created, and give it an environment name. Or do ```conda env create -f environment.yml``` from the envs folder if on Windows.
   2b. Need to ```conda activate BIDS_coding``` or whatever you named the conda environment.  
   2c. Now cd into the BIDS_converter subfolder within BIDS_coding repository, and do ```./BIDS_convert_wsl.sh``` after modifying BIDS_convert_wsl.sh with your chosen SUB_IDS (line 18). Or, BIDS_convert_mac or whichever script fits your OS.
3. Copy the BIDS folder into Box (run it locally because it's faster)
   
   
### Windows FSL
1. Need to open xquartz on windows before running fsl in the ubuntu app. https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/FslInstallation/Windows
2. When running XLaunch, it is critical to deselect Native OpenGL and select Disable access control in the Extra Settings panel. https://superuser.com/questions/1372854/do-i-launch-the-app-xlaunch-for-every-login-to-use-gui-in-ubuntu-wsl-in-windows
3. Need to run the line, export DISPLAY=:0 in Ubuntu first before running fsl command for gui to work.
4. Also need to mount the Z: drive on ubuntu every time we open it. Run this command every time: ```sudo mount –t drvfs Z: /mnt/Egner```
5. Now to get to this folder, do ```cd /mnt/Egner```. In the FSL gui, it should also be ```/mnt/Egner```
6. To make the inputs to paste, run the makeInputsForFSL.ipynb script that's in the GlobalLocal folder right now, changing the subjects range.
7. Then, open fsl feat in ubuntu and do emacs fslSecondLevelInputs.txt, and highlight all and do edit -> copy. Then can paste this as input into the fsl feat input window. Also change the number of cope images in the GUI.
8. To make the EV matrix, run the next cell in makeInputsForFSL.ipynb

