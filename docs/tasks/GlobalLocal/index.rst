**Global Local**

**Preprocessing Guide**

*ecog_preprocessing (Mat) → makeTrials_GL (Mat) → BIDS_coding (WSL)*

**Step 1**: **Download data files (Box)**

1. **Go to Box → ECoG_Task_Data → Cogan_Task_Data** and locate the
      *Subject (D#) folder → Global Local task folder → All blocks*
      subfolder

2. **Download all Box data files from “All Blocks”** folder

3. Then **Copy + Paste** files into **Local PC** folder in
      **CoganLabNL** → **InUnit Preprocessing** → **Subject (D#) →
      Global Local → All blocks**

4. **KEY**: locate the Excel csv file titled:
      **GL_MainTask_Data_D#_taskdate**

   a. **RENAME this file to** “\ **Trials**\ ”

5. **EDF file**: *2 options - Download (local PC) or Box Drive (no
      download)*

   a. **Download**: from **TaskUploadDir**

      i. **Box →** **TaskUploadDir** → **Download** → move to same local
            PC Global Local folder

         1. Only if you want to download!

   b. **Box Drive**: No download, will use Box Drive path in
         edf_filename variable instead of local PC path → **See Step
         2!**

**Step 2**: **ecog_preprocessing (Matlab)** *- general preprocessing
script*

6.  Once your files are downloaded and Trials is renamed, open Matlab
       and run the **ecog_preprocessing** script *(used for all tasks
       preprocessing)*

7.  Start the same as all other tasks → create a new **Case** for the
       task (Global Local = **009**),

8.  *Fill in all of the case variable information accordingly*: **see
       differences!**

    a. **KEY 1** - for **Global Local only**, the **ptb_trialInfo
          variable** is commented out! → *put a* **%** *(percentage
          sign) in front!*

       i. This is because we do not need to get trialInfo – it is
             replaced by the **Trials** excel sheet we renamed in Step
             1.

    b. **KEY 2** - **edf_filename** **variable (path)** will change
          depending on if you downloaded the EDF above from Box, or if
          you are uploading it directly from Box Drive:

       i.  **Downloaded EDF**: path to InUnit Preprocessing (PC)

           1. 'C:\\Users\\ncl24\\Desktop\\CoganLabNL\\InUnit
                 Preprocessing\\D81\\Lexical Delay\\D# DATE
                 COGAN_TASKNAME.EDF'

       ii. **Box Drive EDF**: path to TaskUploadDir (Box)

           1. 'C:\\Users\\ncl24\\Box\\CoganLab\\ECoG_Task_Data\\TaskUploadDir\\D#
                 DATE COGAN_TASKNAME.EDF'

9.  Once all variables are filled out, **highlight + run (F9)** to load
       into your workspace

10. *Ignore the trialInfo section* (don’t need trialInfo) → Go straight
       to the **edfread + labels** section & run!

    a. This will read the EDF file to create your **labels** variable

11. Then, run the following **extract trigger + mic channel** section

    a. This will create your **trigger** & **mic** variables, as well as
          save them as **trigger.mat** & **mic.mat** files in your task
          folder.

12. Finally, run the **.ieeg.dat + experiment** file section, that will
       save the **experiment.mat** & **.ieeg.dat** files in your task
       folder

    a. As well as create the folders **mat** & **taskdate** *(e.g.*
          **230807**\ *)*

       i.  Move the **experiment** file into the **mat** folder

       ii. At the end of Step 5, the **Trials.mat** file will
              automatically save under the **taskdate (230807) → mat**
              folder on Box!

**Step 3**: **MaketrigTimes (Matlab)** *- trigTimes +
trigTimes_audioAligned files*

13. When you reach the **maketrigtimes** section, you will open the
       **maketrigtimes.m** script and run it in a separate window next
       to ecog_preprocessing.

14. *In order to run maketrigtimes successfully, you will need to have*:

    a. The **trigger** variable already loaded in your workspace

       i. Should already be there if going straight from running
             ecog_preprocessing – but if not, double-click on trigger
             saved in folder

    b. Already run **edfread_fast**

       i. If not, go back and run this in ecog_preprocessing & make sure
             that your edf_filename variable (path to EDF) from the case
             variables is loaded in your workspace before doing so.

15. Run the first section at the top to load the graph of the triggers

    a. **Uncomment the -triggers (negative) line** **for Global Local!**

       i. Otherwise the graph will appear upside down

16. Then, proceed as usual and make the trigTimes adjustments you do for
       all other tasks

    a. **Global Local-specific Task Info**:

       i.   *Total # triggers* → **trigTimes** = **448**

       ii.  **4** **blocks** total, **112** triggers per block

            1. *Rare cases could have 512 total trigs, 128 per block*

       iii. *Seconds between triggers* = **1.5**

       iv.  *Threshold (thresh)* = **-1.25**

            1. Bc graph is inverted / negative from the -triggers line!

    b. If you need to delete excess triggers (first, last, random in
          middle) run: trigTimes([1,2,3,etc.]) = [];

       i. *Fill in brackets with which specific trigger numbers you need
             to delete!*

    c. Once **trigTimes = 448**, run the final section to save
          **trigTimes.mat** file to your PC folder!

17. Finally, return to the **ecog_preprocessing** script tab and run the
       section below, to align the audio to your saved trigTimes

    a. This will create the **trigTimes_audioAligned.mat** file and save
          it into your PC folder

**Step 4**: **Upload Files + Copy EDF to Box D_Data**

18. **Before moving on! → Upload all files to Box → D_Data** from InUnit
       Preprocessing folder: **Box → D_Data → Global Local → Subject
       (D#)**

    a. Critical because the **makeTrials_GL script pulls and uses files
          from Box only! (D_Data Global Local folder specifically)**

       i. So before running that script, all files must be uploaded
             there in order for it to work

    b. Upload the files to D_Data in the exact same way as all other
          tasks! - only difference = Trials.csv instead of trialInfo

19. **Also! →** **Copy EDF file into D_Data folder from TaskUploadDir**

    a. The edfread command in this program can only read EDFs / files
          from the D_Data folder!!!

    b. So you must Copy the EDF from TaskUploadDir into the D_Data
          folder with the rest of the uploaded files!

    c. SEE BELOW - you must also change Path to EDF!!!

       i. Of edf_filename variable + edfread_fast(edf_filename)
             commands!

**Step 5**: **makeTrials_GL (Matlab)** *- Global Local only script to
make Trials.mat*

20. Once all files have been uploaded to **Box → D_Data** folder, return
       to Matlab and run the **makeTrials_GL.m** script in another
       separate tab window → this script will output the final
       **Trials.mat** file when finished!

21. **STEPS TO RUN SUCCESSFULLY:** *(also written on script!)*

    a. **Step 1**: **Copy EDF file into D_Data Box folder!** (from
          TaskUploadDir)

       i. **KEY** - Make sure EDF file is copied into the **D_Data**
             Subject Global Local folder on Box!

    b. **Step 2: Edit info** *(specific to each subject)* **+ copy in
          command line to run each command below (A, B, C) ONE AT A
          TIME:**

       i.   **2A)** **Command 1**: change **edf_filename** variable

            1. **COMMAND**: **edf_filename =
                  'C:\\Users\\ncl24\\Box\\CoganLab\\D_Data\\GlobalLocal\\D103\\D103
                  240110 COGAN_GLOBALLOCAL.EDF';**

       ii.  **2B)** *Command 2*: change **h** variable

            1. **COMMAND**: **h =
                  edfread_fast('C:\\Users\\ncl24\\Box\\CoganLab\\D_Data\\GlobalLocal\\D103\\D103
                  240110 COGAN_GLOBALLOCAL.EDF');**

       iii. **2C)** *Command 3*: run **makeTrials_GL** function

            1. **COMMAND**: **makeTrials_GL('D103', '240110')**

               a. *Must replace*: ('subject', 'taskdate')

                  i.  Replace **subject** with **'D#'**

                  ii. Replace **date** with **'taskdate'** (e.g.
                         **'230807')**

               b. *Final format*: **makeTrials_GL('D#', 'taskdate')**

                  i. **Example**: D94

                     1. *subject* = ‘D94’

                     2. *date* = ‘230807’

                     3. **=**:**makeTrials_GL(‘D94’, ‘230807’)**

               c. You **MUST add the single ‘quotations’** around each
                     of the real variables that you enter, in order for
                     them to be registered as the values for those
                     variables!

       iv.  *Once 2C is finished running, you are done!*

    c. **Final output** = **Trials.mat** (when 2C is done ^)

       i.  **Trials.mat** file will automatically save under the
              **taskdate (e.g. 230807) → mat** **folder on Box!**

       ii. *Example path to locate Trials.mat file*:

           1. Box -> CoganLab -> D_Data -> GlobalLocal -> D103 (subj) ->
                 240110 (taskdate) -> mat -> Trials.mat

    d. If you would like to save it in your local PC folder (InUnit
          Preprocessing) as well, you can download the file from Box and
          copy it there! – you don’t have to though.

**Step 6**: **BIDS_coding (WSL → Visual Studio (VS) Code program)** *-
BIDS*

22. *Step 1*: Open WSL

23. *Step 2*: Open **BIDS_coding** workspace (folder from Desktop)

    a. **File** (top left) → **Open Folder → Desktop → BIDS_coding**

       i.  Make sure it opens into **BIDS_convert_wsl.sh** script!

       ii. **BIDS_coding → BIDS_converter → BIDS_convert_wsl.sh**

           1. C:/Users/ncl24/BIDS_coding/BIDS_converter/BIDS_convert_wsl.sh

24. *Step 3*: In “\ **Terminal**\ ” (command window at bottom), type
       **git pull**

    a. Make sure you are in the right workspace, should look like this:

       i.  .. image:: media/image5.png
                 :width: 5.42708in
                 :height: 0.1875in

       ii. Press **Enter**

25. *Step 4*: If you encounter an **error message!**

    a. *Message*:

       i. .. image:: media/image9.png
                :width: 5.25521in
                :height: 0.47775in

    b. You will need to make sure all of your changes to **ALL scripts
          in the workspace** (modified files will have an “\ **M**\ ”
          next to them in explorer left side bar) have been
          **COMMITTED** to Github **before running** the next line,
          because they will be **ERASED!!!**

       i. *To commit changes to github*: type **git push → git commit**

    c. If your only changes are the variables of subject, task, etc.
          that you make for specific subjects, then you don’t have to
          commit them – **BUT**, make sure any files you have run for
          previous subjects with the script are **SAVED TO BOX BEFORE
          RUNNING the next command**, because they will be
          **overwritten!!!**

       i. *To Save to Box*:

          1. Drag **sub-D00XX** folder into **share** folder above
                Workspace in WSL explorer → should be in **Share**
                folder on Desktop, then copy into Box →
                **BIDS-1.1_GlobalLocal** folder

26. *Step 5*: Once all previous subject files have been saved to Box
       BIDS Global Local folder, you will reset the script!

    i.   Type **git reset --hard** + Enter!

    ii.  *Should look like this when idone*:

    iii. .. image:: media/image3.png
               :width: 5.35938in
               :height: 0.31296in

27. *Step 6*: When git reset is done, **re-type** **git pull** + Enter!

28. *Step 7*: **KEY** – **Edits to make to Script after Reset**:

    a. Editing **BIDS_convert_wsl.sh** script!

    b. **EDITS**: *CRITICAL TO CHANGE THESE IN SCRIPT BEFORE RUNNING!*

       i.   **Line 4**: Change task to → **TASKS=(“GlobalLocal”)**

            1. Must change from “SentenceRep” default to GlobalLocal (or
                  any task going forward)

               a. Use the exact same name as the D_Data folder!

            2. **Final**: |image1|

       ii.  **Line 16**: **Comment out (#) whole mapfile line!**

            1. Don’t need for Global Local (will cause error)

            2. **Final**: *see full line on script*\ |image2|

       iii. **Line 17**: Change **SUB_IDS=(D#)** D# to correct Subject
               D#’s!

            1. Can run **multiple subjects at once**, or just **one**

               a. If running multiple, separate by spaces only! No
                     comma! → *see example below:*

            2. **Final**: |image3|

       iv.  **Line 35**: **Comment out (#) the whole line 35!**

            1. Global Local doesn’t have task stimuli, so don’t need
                  this line and it will cause an error if you keep it!

            2. **Final**: *see full line on script*\ |image4|

            3. Only comment this out for Global Local or tasks that
                  don’t have task stimuli!

               a. For other future tasks that do, change the
                     “sentence_rep” task name in the middle of the
                     command line (35) and insert the correct task name
                     to use proper task stimuli!

    c. **CTRL + S** **TO SAVE ALL EDITS TO SCRIPT!!!**

29. *Step 8*: When all edits have been made to script & saved (**ctrl +
       s**), type **conda activate BIDS_coding** + Enter!

30. *Step 9*: The conda activate command will change (base) at the start
       of the command path to (BIDS_coding)

    a. Once the new command line pops up below:

       i. Type **cd BIDS_converter/** + Enter!

31. *Step 10*: The cd command will take you into the BIDS_converter
       folder within BIDS_coding (adds it to end of path), which is
       where you can now run the script to perform the BIDS conversion
       functions

    a. Once the next command line pops up below with /BIDS_converter at
          the end: type **./BIDS_convert_wsl.sh** + Enter!

32. **STEPS 8, 9, 10 SHOULD LOOK LIKE THIS**: (in order top → bottom!)

    a. .. image:: media/image8.png
             :width: 6.25521in
             :height: 0.43105in

33. *Step 11*: The script should then run for a few minutes (10-15 min)
       after entering the last command to create all of the converted
       BIDS files!

    a. Final output will be on the left side bar (WSL Explorer)

       i. *To open explorer*: click double paper icon at top left corner

    b. Under **ncl24 → Workspace → GlobalLocal → BIDS**

       i.  Locate the **sub-D0XXX** folder!

           1. i.e. sub-D0100 for Subject D100

           2. .. image:: media/image10.png
                    :width: 1.97917in
                    :height: 1.39583in

       ii. This is where all of the finalized BIDS files will go!

34. *Last step*: move to **share** folder (on WSL)

    a. When it is finished creating BIDS files, in the left side bar
          with workspaces, drag and drop this **sub-D00XX** output
          folder containing the BIDS files into the “\ **share**\ ”
          folder above Workspace! (see top of pic above)

       i. Then you will be able to access it from **Share PC** folder on
             Desktop! → if not moved to share, can’t access on Windows

**Final Step**: **Upload sub-D00XX on Share folder to Box
BIDS-1.1_GlobalLocal**

35. Copy **sub-D00XX** with all finalized BIDS file outputs from
       **Share** PC folder into **Box → CoganLab → BIDS-1.1_GlobalLocal
       → BIDS** folder!

.. image:: media/image4.png
   :width: 6.72917in
   :height: 2.55952in

.. |image1| image:: media/image2.png
   :width: 2.10417in
   :height: 0.21631in
.. |image2| image:: media/image1.png
   :width: 5.30729in
   :height: 0.20833in
.. |image3| image:: media/image6.png
   :width: 3.07292in
   :height: 0.1875in
.. |image4| image:: media/image7.png
   :width: 5.17708in
   :height: 0.20833in
