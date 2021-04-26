#
# A code that automatically converts CMRIF NIFTI 1 and DICOM files into BIDS format
# requires dcm2niix and dos2unix to be installed 
    
ORIG_DATA_DIR="/media/sf_Box_Sync/CoganLab"
OUTPUT_DIR="/media/sf_Ubuntu_files/Workspace" 


SUB_IDS=(D47 D48) 
TASKS=(Phoneme_sequencing)

#declare -l mylist[30]

#BIDS_DIR="$OUTPUT_DIR/$TASK/BIDS"

for SUB_ID in ${SUB_IDS[@]}
 do 
    
    #IDSPLIT=( $(grep -Eo '[^[:digit:]]+|[[:digit:]]+' <<<"SUB_ID") )
    #NEW_ID="${IDSPLIT[0]}$(printf %04d ${IDSPLIT[1]})"

    mkdir -p "$OUTPUT_DIR/$SUB_ID"
    find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/elec_recon" -name "postInPre.nii.gz" -type f -exec cp {} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_CT.nii.gz" \;
    find "$ORIG_DATA_DIR/../ECoG_Recon/$SUB_ID/elec_recon" -name "${SUB_ID}_elec_locations_RAS.txt" -type f -exec cp {} "$OUTPUT_DIR/$SUB_ID/" \;
    find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/mri" -name "orig.mgz" -type f -exec cp {} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_T1w.mgz" \; | head -1
    for TASK in ${TASKS[@]}
     do
        find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -name "$SUB_ID*.edf" -type f -exec cp -t "$OUTPUT_DIR/$SUB_ID/" {} +
        find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\/mat\/.*[tT]rial[(Info)s].*\.mat" -exec cp -t "$OUTPUT_DIR/$SUB_ID/" {} + 
    done
    
        
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