import numpy as np
import matplotlib.pyplot as plt
import os
import json
import pyedflib
import pickle  # for saving trigTimes as in MATLAB

# --- File & Subject Setup ---
subject = "D110"

HOME = os.path.expanduser("~")
LAB_ROOT = os.path.join(HOME, "Box", "CoganLab")
edf_path = os.path.join(LAB_ROOT, "D_Data", "SentenceRep", "EDFs", "D110 240615 COGAN_SENTENCEREP.EDF")
f = pyedflib.EdfReader(edf_path)

with open('subjects.json') as fst:
    subjects = json.load(fst)

trigger_chan = subjects[subject]['default']['trigger']
trigger_chan_number = list(f.getSignalLabels()).index(trigger_chan)
trigger = f.readSignal(trigger_chan_number)
freq = f.getSampleFrequency(trigger_chan_number)

# Optional: Flip trigger if needed
# trigger = -trigger

# --- Plot raw trigger signal ---
plt.figure()
plt.plot(trigger)
plt.title('Raw Trigger Signal')

# --- Zero out unwanted sections ---
trigger = trigger.copy()
to_zero = np.r_[0:int(3.5e6), int(7.38e6):len(trigger)]
trigger[to_zero] = 0

plt.figure()
plt.plot(trigger)
plt.title('Trigger After Zeroing')

# --- Trigger Detection ---
thresh = 0.9e5  # adjust this as needed
seconds_between_triggers = 1.5
num_samples_between_triggers = int(seconds_between_triggers * freq)

trigs = np.where(trigger >= thresh)[0]
diff_trigs = np.diff(trigs)
big_trigs = np.where(diff_trigs > num_samples_between_triggers)[0]
trigTimes = np.r_[trigs[0], trigs[big_trigs + 1]]

# Optional: remove every other for alternate triggering
# trigTimes = trigTimes[::2]

# Optional: remove specific indices
remove_indices = [0, 53, 108, 163]
trigTimes = np.delete(trigTimes, remove_indices)

# --- Plot with trigger markers ---
plt.figure()
plt.plot(trigger)
plt.scatter(trigTimes, np.full_like(trigTimes, thresh), color='red', label='Triggers')
plt.title('Trigger Detection with Markers')
plt.legend()

# --- Save trigTimes to file ---
with open("trigTimes.pkl", "wb") as f:
    pickle.dump(trigTimes, f)

print("Trigger times saved to trigTimes.pkl")
