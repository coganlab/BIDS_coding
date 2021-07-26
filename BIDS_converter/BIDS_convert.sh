##!/bin/bash

ORIG_DATA_DIR="$HOME/Desktop/sf_Box_Sync/CoganLab"
SUB_IDS=(D52 D48) 
TASKS=(Phoneme_sequencing)

#declare -l mylist[30]

#BIDS_DIR="$OUTPUT_DIR/$TASK/BIDS"
for TASK in "${TASKS[@]}"
 do

    OUTPUT_DIR="$HOME/Desktop/sf_host/Workspace/sourcedata/$TASK"
    BIDS_DIR="$OUTPUT_DIR/../../$TASK/BIDS"
    ZIP=false
    
    if [ -d $BIDS_DIR ]
     then
        rm -rf $BIDS_DIR
    fi
    mkdir -p $BIDS_DIR
    mkdir -p "$BIDS_DIR/stimuli"
    cp -R "$ORIG_DATA_DIR/task_stimuli/$TASK/." "$BIDS_DIR/stimuli/"

    for SUB_ID in "${SUB_IDS[@]}"
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
        find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/elec_recon" -name "T1.nii.gz" -type f -exec cp {} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_T1w.nii.gz" \; | head -1

        #eeg files
        if ! find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\.edf" -exec false {} +  ; then #search for edf files
            find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\.edf" -exec cp -t "$OUTPUT_DIR/$SUB_ID/" {} + 
            if $ZIP ; then
                find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\.edf" | xargs -I{} basename {} | xargs -I{} echo "$OUTPUT_DIR/$SUB_ID/{}" | xargs -I{} gzip -6 -v {}
            fi
        else #if no edf files find binary files
            x=( $(find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*$SUB_ID.*\.ieeg.dat" -type f | rev | sed -r "s|/|_|" | sed -r "s|/|noisseS/|" | rev | xargs -n 1 basename | sed -r "s|${SUB_ID}_||") )
            y=( $(find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*$SUB_ID.*\.ieeg.dat") )
            z=${#x[@]}
            if $ZIP ; then
                for((i=0;i<=$z-1;i+=1));  do gzip -c -6 -v ${y[$i]} > "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_${x[$i]}.gz" ; done
            else 
                for((i=0;i<=$z-1;i+=1));  do cp ${y[$i]} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_${x[$i]}" ; done
            fi
        fi
        #find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -type f -regex ".*$SUB_ID.*\.ieeg\.dat" | xargs -n 1 basename | xargs -I{} cp "$OUTPUT_DIR/$SUB_ID/{}" "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_{}"
        find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*experiment\.mat" -exec cp -t "$OUTPUT_DIR/$SUB_ID/" {} + 
        #event .mat
        find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\/mat\/.*[tT]rial[(Info)s].*\.mat" -exec cp -t "$OUTPUT_DIR/$SUB_ID/" {} + 
        #triggers
        #find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*[Tt]rigger[0-9]?[0-9]?\.mat$" -exec cp -t "$OUTPUT_DIR/$SUB_ID/" {} +
        #rename .mat
        find "$OUTPUT_DIR/$SUB_ID" -type f -regex ".*\.mat" | xargs -n 1 basename | xargs -I{} mv "$OUTPUT_DIR/$SUB_ID/{}" "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_{}"
        #rename .dat
        #find "$OUTPUT_DIR/$SUB_ID" -type f -regex "\.mat" | xargs -n 1 basename | xargs -I{} mv "$OUTPUT_DIR/$SUB_ID/{}" "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_{}"
        #the big bad python code to convert the renamed files to BIDS
        #requires numpy, nibabel, and pathlib modules
        python3 data2bids.py -c config.json -i "$OUTPUT_DIR/$SUB_ID" -o $BIDS_DIR -v -ow|| { echo "BIDS conversion for $SUB_ID failed, trying next subject" ; continue; }

        [[ $RAN_SUBS =~ (^| )$SUB_ID( |$) ]] || RAN_SUBS+=${SUB_ID}" "
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