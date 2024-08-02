#!/usr/bin/env bash

ORIG_DATA_DIR="$HOME/Box/CoganLab"
# OUTPUT_DIR="$ORIG_DATA_DIR/BIDS-1.1_GlobalLocal"
OUTPUT_DIR="$HOME/Workspace/Neighborhood"
TASKS=("Neighborhood_Sternberg")
SUB_IDS=(D59)


for TASK in "${TASKS[@]}"
do
    BIDS_DIR="$OUTPUT_DIR/BIDS"
    ZIP=false

    if [ -d "$OUTPUT_DIR" ]; then
        rm -rf "$OUTPUT_DIR"
    fi
    mkdir "$OUTPUT_DIR"

    if [ -d "$BIDS_DIR" ]; then
        rm -rf "$BIDS_DIR"
    fi
    # mkdir -p $BIDS_DIR
    mkdir -p "$OUTPUT_DIR/stimuli"
    # shellcheck disable=SC2038
    find "$ORIG_DATA_DIR/task_stimuli" -iname "Neighborhood_Sternberg" -type d -exec echo "{}/." \; | xargs -I{} cp -afv {} "$OUTPUT_DIR/stimuli/"
    TASKLOWER=$(echo "$TASK" | tr '[:upper:]' '[:lower:]')

    for SUB_ID in "${SUB_IDS[@]}"
    do 
        if [ -d "$OUTPUT_DIR/$SUB_ID" ]; then
            rm -rf "$OUTPUT_DIR/$SUB_ID"
        fi
        mkdir -p "$OUTPUT_DIR/$SUB_ID"

        # CT scan .nii
        find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/elec_recon" -name "postimpRaw.nii.gz" -type f -exec cp -v {} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_CT.nii.gz" \;
        find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/elec_recon" -regex ".*\($SUB_ID.*CT.*\)\|\(postimpRaw\)\.nii" -type f -exec cp -v {} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_CT.nii" \;

        # Electrode locations .txt
        find "$(dirname "$ORIG_DATA_DIR")/ECoG_Recon/$SUB_ID/elec_recon" -regex ".*${SUB_ID}_elec_locations_RAS_.*\.txt" -type f -exec cp -v {} "$OUTPUT_DIR/$SUB_ID/" \;

        # T1 MRI file .mgz
        find "$ORIG_DATA_DIR/ECoG_Recon_Full/$SUB_ID/elec_recon" -name "T1.nii.gz" -type f -exec cp -v {} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_T1w.nii.gz" \;

        # Stim file corrections
        if [ "$TASK" == "Phoneme_Sequencing" ]; then
            cp -v "$ORIG_DATA_DIR/ECoG_Task_Data/response_coding/PhonemeSequencingStimStarts.txt" "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_PhonemeSequencingStimStarts.txt"
        fi

        # EEG files
        if ! find "$ORIG_DATA_DIR/D_Data/$TASK/" -iregex ".*$SUB_ID.*\.edf" -exec false {} + ; then
            find "$ORIG_DATA_DIR/D_Data/$TASK/" -iregex ".*$SUB_ID.*\.edf" -exec cp -v {} "$OUTPUT_DIR/$SUB_ID/" \;
            find "$OUTPUT_DIR/$SUB_ID/" -regex ".*\.EDF" | xargs -I{} basename -s ".EDF" {} | xargs -I{} mv -v "$OUTPUT_DIR/$SUB_ID/{}.EDF" "$OUTPUT_DIR/$SUB_ID/{}.edf"
            if $ZIP ; then
                find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\.\(EDF\)\|\(edf\)" | xargs -I{} basename {} | xargs -I{} cut -f 1 -d '.' {} | xargs -I{} echo "$OUTPUT_DIR/$SUB_ID/{}.edf" | xargs -I{} gzip -6 -v {}
            fi
        else
            x=( $(find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*$SUB_ID.*\.ieeg.dat" -type f | rev | sed -r "s|/|_|" | sed -r "s|/|noisseS/|" | rev | xargs -n 1 basename | sed -r "s|${SUB_ID}_||") )
            y=( $(find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*$SUB_ID.*\.ieeg.dat") )
            z=${#x[@]}
            if $ZIP ; then
                for((i=0;i<=$z-1;i+=1)); do gzip -c -6 -v ${y[$i]} > "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_${x[$i]}.gz"; done
            else 
                for((i=0;i<=$z-1;i+=1)); do rsync -vP ${y[$i]} "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_${x[$i]}"; done
            fi
        fi

        find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*experiment\.mat" -exec cp -v {} "$OUTPUT_DIR/$SUB_ID/" \;

        # Event .mat
        find "$ORIG_DATA_DIR/D_Data/$TASK/$SUB_ID" -regex ".*\/mat\/.*[tT]rial[(Info)s].*\.mat" -exec cp -v {} "$OUTPUT_DIR/$SUB_ID/" \;

        # Rename .mat
        find "$OUTPUT_DIR/$SUB_ID" -type f -regex ".*\.mat" | xargs -n 1 basename | xargs -I{} mv -v "$OUTPUT_DIR/$SUB_ID/{}" "$OUTPUT_DIR/$SUB_ID/${SUB_ID}_{}"

        python -m data2bids -c config.json -i "$OUTPUT_DIR/$SUB_ID" -o "$BIDS_DIR" -v || { echo "BIDS conversion for $SUB_ID failed, trying next subject" ; continue; }

        [[ $RAN_SUBS =~ (^| )$SUB_ID( |$) ]] || RAN_SUBS+="$SUB_ID "
        [[ $RAN_TASKS =~ (^| )$TASK( |$) ]] || RAN_TASKS+="$TASK "
        printf "subjects ran: $RAN_SUBS\ntasks ran: $RAN_TASKS\n"    
    done

done

echo "Finished"
