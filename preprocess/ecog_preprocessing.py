# %% --- ECoG Preprocessing Pipeline ---
import matgrab
import os
import numpy as np
import re
import pandas as pd
from preprocess import LAB_ROOT
from pyedflib import EdfReader


# %% --- File & Subject Setup ---
subject = "D100"
task = "SentenceRep"

# trialInfo_path = os.path.join(LAB_ROOT, "ECoG_Task_Data", "response_coding", "response_coding_results", task, subject, "All blocks")
# pattern2 = re.compile(rf"{subject}.*\.mat$")
# mat_files = sorted(f for f in os.listdir(trialInfo_path) if pattern2.match(f))
# mat_file = mat_files[-1] # Take the last one if multiple
# mat_path = os.path.join(trialInfo_path, mat_file)
edf_path = os.path.join(LAB_ROOT, "D_Data", task, "EDFs")
pattern1 = re.compile(rf"{subject}.*\.EDF$")
edf_file = [f for f in os.listdir(edf_path) if re.search(pattern1, f)][0]
taskdate = re.search(r' (\d{6}) ', edf_file).group(0).strip()
trialInfo_path = os.path.join(LAB_ROOT, "D_Data", task, subject, taskdate,
                              "mat", "trialInfo.mat")
trialInfo = matgrab.mat2df(trialInfo_path)

# %% --- Load Trigger Times ---
# trigTimes = np.load('../trigTimes.npy')  # Load previously saved trigger times
trigTimes = np.array(matgrab.mat2df(
    os.path.join(LAB_ROOT, "D_Data", task, subject, "trigTimes.mat")))

# %% --- Load EDF and get sampling frequency ---
filenames = os.listdir(edf_path)
edf_file_full = os.path.join(edf_path, edf_file)
f = EdfReader(edf_file_full)
sfreq = f.getSampleFrequency(0)

# %% --- Create Trials.mat ---
# Create Trials structure (example for phoneme sequencing)
assert len(trialInfo) == len(trigTimes)
Trials = []
for A in range(len(trialInfo)):
    trial = {}
    trial['Subject'] = subject
    trial['Trial'] = A + 1
    # trial['Rec'] = '001'
    # trial['Day'] = taskdate
    # trial['FilenamePrefix'] = f"{subject}_{task}_{taskdate}"
    trial['Start'] = int(trigTimes[A] * (30000 / sfreq))
    trial['Auditory'] = trial['Start'] + int((trialInfo['audioStart'][A] - trialInfo['cueStart'][A]) * 30000)
    trial['Go'] = trial['Start'] - int((trialInfo['cueStart'][A] - trialInfo['goStart'][A]) * 30000)
    # trial['StartCode'] = 1
    # trial['AuditoryCode'] = 26
    # trial['GoCode'] = 51
    # trial['Noisy'] = 0
    # trial['NoResponse'] = 0
    Trials.append(trial)

Trials_df = pd.DataFrame(Trials)
out_file = os.path.join(LAB_ROOT, "D_Data", task, subject, "Trials.csv")
Trials_df.to_csv(out_file, index=False)