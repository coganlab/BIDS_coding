#
    
ORIG_DATA_DIR="/media/sf_Box_Sync/CoganLab"
SUB_IDS=(D47 D48) 
TASKS=(Phoneme_sequencing)

#declare -l mylist[30]

#BIDS_DIR="$OUTPUT_DIR/$TASK/BIDS"
for TASK in ${TASKS[@]}
 do

    OUTPUT_DIR="/media/sf_Ubuntu_files/Workspace/$TASK" 
    BIDS_DIR="$OUTPUT_DIR/BIDS"
    
    if [ -d $BIDS_DIR ]
     then
        rm -rf $BIDS_DIR
    fi
    mkdir -p $BIDS_DIR

    for SUB_ID in ${SUB_IDS[@]}
    do 
        #bring wanted files to work space
        #IDSPLIT=( $(grep -Eo '[^[:digit:]]+|[[:digit:]]+' <<<"SUB_ID") )
        #NEW_ID="${IDSPLIT[0]}$(printf %04d ${IDSPLIT[1]})"

        if [ -d "$OUTPUT_DIR/$SUB_ID" ]
        then
            rm -rf "$OUTPUT_DIR/$SUB_ID"
        fi
        mkdir -p "$OUTPUT_DIR/$SUB_ID"

        #CT scan .nii
        find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/elec_recon" -name "postInPre.nii.gz" -type f -exec cp {} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_CT.nii.gz" \;
        #electrode locations .txt
        find "$ORIG_DATA_DIR/../ECoG_Recon/$SUB_ID/elec_recon" -name "${SUB_ID}_elec_locations_RAS.txt" -type f -exec cp {} "$OUTPUT_DIR/$SUB_ID/" \;
        #T1 MRI file .mgz
        find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/mri" -name "orig.mgz" -type f -exec cp {} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_T1w.mgz" \; | head -1

        #eeg .edf
        find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -name "$SUB_ID*.edf" -type f -exec cp -t "$OUTPUT_DIR/$SUB_ID/" {} +
        #event .mat
        find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\/mat\/.*[tT]rial[(Info)s].*\.mat" -exec cp -t "$OUTPUT_DIR/$SUB_ID/" {} + 
        #rename .mat
        find "$OUTPUT_DIR/$SUB_ID" -type f -regex ".*[tT]rial[(Info)s].*\.mat" | xargs -n 1 basename | xargs -I{} mv "$OUTPUT_DIR/$SUB_ID/{}" "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_{}"
        
        #the big bad python code to convert the renamed files to BIDS
        #requires numpy, nibabel, and pathlib modules
        python3 data2bids.py -c config.json -i "$OUTPUT_DIR/$SUB_ID" -o $BIDS_DIR || { echo "BIDS conversion for $SUB_ID failed, trying next subject" ; continue; }

        RAN_SUBS+=${SUB_ID}" "
        [[ $RAN_TASKS =~ (^| )$TASK( |$) ]] || RAN_TASKS+=${TASK}" "
        printf "subjects ran: $RAN_SUBS\ntasks ran: $RAN_TASKS\n"    
    done

done
    
# preprocess the BIDS formatted subject
# requires pybids, nipype, 
#cd .. 
#python3 CMRIF_preprocess.py -i $BIDS_DIR -in s${SUB_NUM} -verb || { echo "preprocessing for $SUB_ID failed, trying next subject" ; cd $CWD; continue; }
#cd /BIDS_converter

echo "Finished"