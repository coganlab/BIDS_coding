#!/usr/bin/env bash

ORIG_DATA_DIR="$HOME/Box/CoganLab"
SUB_IDS=(D22 D23 D24 D25 D28 D29 D31 D35 D39 D40 D41 D42 D45 D48
D49 D52 D53 D54 D55 D56 D57 D58 D59 D60 D61 D63 D64)
TASKS=("Phoneme_Sequencing")

#declare -l mylist[30]

#BIDS_DIR="$OUTPUT_DIR/$TASK/BIDS"
for TASK in "${TASKS[@]}"
 do

    OUTPUT_DIR="$ORIG_DATA_DIR/BIDS-1.3_Phoneme_sequencing/Error"
    BIDS_DIR="$OUTPUT_DIR/../BIDS"
    ZIP=false

    if [ -d $OUTPUT_DIR ]
     then
        rm -rf $OUTPUT_DIR
    fi
    mkdir $OUTPUT_DIR

    if [ -d $BIDS_DIR ]
     then
        rm -rf $BIDS_DIR
    fi
    mkdir -p $BIDS_DIR
    mkdir -p "$OUTPUT_DIR/stimuli"
    # shellcheck disable=SC2038
    find "$ORIG_DATA_DIR/task_stimuli" -iname "$TASK" -type d -exec echo "{}/." \; | xargs -I{} cp -anfv {} "$OUTPUT_DIR/stimuli/"
    # shellcheck disable=SC2038
    find "$ORIG_DATA_DIR/task_stimuli" -iname "$TASK" -type d -exec echo "{}/" \; | xargs -I{} rsync -aP {} "$OUTPUT_DIR/stimuli/"

    for SUB_ID in "${SUB_IDS[@]}"
    do 
        #bring wanted files to work space
        #IDSPLIT=( $(grep -Eo '[^[:digit:]]+|[[:digit:]]+' <<<"SUB_ID") )
        #NEW_ID="${IDSPLIT[0]}$(printf %04d ${IDSPLIT[1]})"

        if [ -d "$OUTPUT_DIR/$SUB_ID" ]
        then
            # shellcheck disable=SC2115
            rm -rf "$OUTPUT_DIR/$SUB_ID"
        fi
        mkdir -p "$OUTPUT_DIR/$SUB_ID"

        #CT scan .nii
        find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/elec_recon" -name "postInPre.nii.gz" -type f -exec cp -vn {} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_CT.nii.gz" \;
        find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/elec_recon" -name "postInPre.nii.gz" -type f -exec rsync -P {} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_CT.nii.gz" \;
        if [ ! -f "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_CT.nii.gz" ]
        then
          find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/elec_recon" -regex ".*${SUB_ID}_CT.*" -type f -exec cp -vn {} "$OUTPUT_DIR/$SUB_ID/" \;
          find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/elec_recon" -regex ".*${SUB_ID}_CT.*" -type f -exec rsync -P {} "$OUTPUT_DIR/$SUB_ID/" \;
        fi
        #electrode locations .txt
        find "$ORIG_DATA_DIR/../ECoG_Recon/$SUB_ID/elec_recon" -name "${SUB_ID}_elec_locations_RAS.txt" -type f -exec cp -vn {} "$OUTPUT_DIR/$SUB_ID/" \;
        find "$ORIG_DATA_DIR/../ECoG_Recon/$SUB_ID/elec_recon" -name "${SUB_ID}_elec_locations_RAS.txt" -type f -exec rsync -P {} "$OUTPUT_DIR/$SUB_ID/" \;
        #T1 MRI file .mgz
        find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/elec_recon" -name "T1.nii.gz" -type f -exec cp -vn {} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_T1w.nii.gz" \; | head -1
        find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/elec_recon" -name "T1.nii.gz" -type f -exec rsync -P {} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_T1w.nii.gz" \; | head -1
        #stim file corrections
        if [ $TASK == "Phoneme_sequencing" ]
        then
            cp -vn "$ORIG_DATA_DIR/ECoG_Task_Data/response_coding/PhonemeSequencingStimStarts.txt" "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_PhonemeSequencingStimStarts.txt"
            rsync -P "$ORIG_DATA_DIR/ECoG_Task_Data/response_coding/PhonemeSequencingStimStarts.txt" "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_PhonemeSequencingStimStarts.txt"
        fi
        #eeg files

        if find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\.edf" -exec false {} +  ; then #search for edf files
            #    find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\.edf" -exec cp -v -t "$OUTPUT_DIR/$SUB_ID/" {} +
            #    if $ZIP ; then
            #        find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\.edf" | xargs -I{} basename {} | xargs -I{} echo "$OUTPUT_DIR/$SUB_ID/{}" | xargs -I{} gzip -6 -v {}
            #    fi
            # else #if no edf files find binary files
            x=( $(find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*$SUB_ID.*\.ieeg.dat" -type f | rev | sed -r "s|/|_|" | sed -r "s|/|noisseS/|" | rev | xargs -n 1 basename | sed -r "s|${SUB_ID}_||") )
            y=( $(find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*$SUB_ID.*\.ieeg.dat") )
            z=${#x[@]}
            if $ZIP ; then
                for((i=0;i<=$z-1;i+=1));  do gzip -c -6 -v ${y[$i]} > "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_${x[$i]}.gz" ; done
            else 
                for((i=0;i<=$z-1;i+=1));  do rsync -vP ${y[$i]} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_${x[$i]}" ; done
            fi
        else

            if $ZIP ; then
                find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\.edf" | xargs -I{} basename {} | xargs -I{} echo "$OUTPUT_DIR/$SUB_ID/{}" | xargs -I{} gzip -6 -v {}
            else
                find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\.edf" -exec rsync -vP {} "$OUTPUT_DIR/$SUB_ID/" \;

            fi
        fi
        #find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -type f -regex ".*$SUB_ID.*\.ieeg\.dat" | xargs -n 1 basename | xargs -I{} cp "$OUTPUT_DIR/$SUB_ID/{}" "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_{}"
        find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*experiment\.mat" -exec cp -v -t "$OUTPUT_DIR/$SUB_ID/" {} +
        #event .mat
        find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\/mat\/.*[tT]rial[(Info)s].*\.mat" -exec cp -v -t "$OUTPUT_DIR/$SUB_ID/" {} +
        #triggers
        #find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*[Tt]rigger[0-9]?[0-9]?\.mat$" -exec cp -t "$OUTPUT_DIR/$SUB_ID/" {} +
        #rename .mat
        find "$OUTPUT_DIR/$SUB_ID" -type f -regex ".*\.mat" | xargs -n 1 basename | xargs -I{} mv -v "$OUTPUT_DIR/$SUB_ID/{}" "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_{}"
        #rename .dat
        #find "$ORIG_DATA_DIR/ECoG_Task_Data" -type f -regex "Timestamps [MASTER].xlsx"  -exec cp -v {} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_timstamps.xlsx" \;
        #the big bad python code to convert the renamed files to BIDS
        #requires numpy, nibabel, and pathlib modules
        python3 data2bids.py -c config.json -i "$OUTPUT_DIR/$SUB_ID" -o $BIDS_DIR -v || { echo "BIDS conversion for $SUB_ID failed, trying next subject" ; continue; }
		    rm -rf "$OUTPUT_DIR/$SUB_ID"

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