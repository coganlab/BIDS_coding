#
# A code that automatically converts CMRIF NIFTI 1 and DICOM files into BIDS format
# requires dcm2niix and dos2unix to be installed 
    
ORIG_DATA_DIR="$HOME/ebs/RAW" 
OUTPUT_DIR="$HOME/ebs" 
TSV_DIR="$HOME/timing_files" 
README_DIR="$HOME/readme_files"
BIDS_DIR="$HOME/ebs/BIDS"

SUB_IDS=(3033) 

#declare -l mylist[30]

for SUB_ID in ${SUB_IDS[@]}
 do 
    if [ $(hostname -d) == "us-east-2.compute.internal" ] && [ ! -d $ORIG_DATA_DIR/$SUB_ID ] ; then 
        cd ..
        python3 s3_ebs.py -l $OUTPUT_DIR -s "RAW/$SUB_ID" -b "medhavi-testing-bucket" --download
        cd BIDS_converter/
    fi

    #echo $MELIST
    
	#the big bad python code to convert the renamed files to BIDS
	#requires numpy, nibabel, and pathlib modules
    echo $PWD
    python3 data2bids.py -c config.json -d $ORIG_DATA_DIR/$SUB_ID -o $BIDS_DIR || { echo "BIDS conversion for $SUB_ID failed, trying next subject" ; continue; }

    # preprocess the BIDS formatted subject
    # requires pybids, nipype, 
    cd .. 
    python3 CMRIF_preprocess.py -i $BIDS_DIR -in s${SUB_NUM} -verb || { echo "preprocessing for $SUB_ID failed, trying next subject" ; cd $CWD; continue; }
    cd /BIDS_converter

    RAN_SUBS+=${SUB_ID}" "
    echo "subjects ran: $RAN_SUBS"

    #python data2bids.py -d /media/sf_Ubuntu_files/Workspace/${SUB_NUM} -c /media/sf_Ubuntu_files/BIDS_converter/config.json -o /media/sf_Ubuntu_files/workspace/bids -m 4

    #-f %c_%d_%e_%f_%i_%n_%p_%t_%z
done
echo "Finished"