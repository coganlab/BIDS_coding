import numpy as np
import matplotlib
matplotlib.use('qt5Agg')
import matplotlib.pyplot as plt
import os
import json
import pyedflib
import re
from preprocess import LAB_ROOT

# %% --- File & Subject Setup ---
subject = "D81"
task = "SentenceRep"

edf_path = os.path.join(LAB_ROOT, "D_Data", task, "EDFs")
filenames = os.listdir(edf_path)
pattern = re.compile(rf"{subject}.*\.EDF$")
edf_file = [f for f in filenames if re.search(pattern, f)][0]
f = pyedflib.EdfReader(os.path.join(edf_path, edf_file))
plot_ds = 4  # downsample factor for plotting

with open('../subjects.json') as fst:
    subjects = json.load(fst)

trigger_chan = subjects[subject]['default']['trigger']
trigger_chan_number = list(f.getSignalLabels()).index(trigger_chan)
trigger = f.readSignal(trigger_chan_number).astype('f4')  # Convert to float32
freq = f.getSampleFrequency(trigger_chan_number)

# %% Optional: Flip trigger if needed
# trigger = -trigger

# %% --- Plot raw trigger signal ---
plt.figure()
plt.plot(range(0, len(trigger), plot_ds), trigger[::plot_ds])
plt.title('Raw Trigger Signal')
plt.show()

# %% --- Zero out unwanted sections ---
trigger = trigger.copy()
to_zero = np.r_[0:int(1.6e6), int(5.52e6):len(trigger)]
trigger[to_zero] = 0

plt.figure()
plt.plot(range(0, len(trigger), plot_ds), trigger[::plot_ds])
plt.title('Trigger After Zeroing')
plt.show()

# %% --- Trigger Detection ---
thresh = .8e5  # adjust this as needed
seconds_between_triggers = 2
num_samples_between_triggers = int(seconds_between_triggers * freq)

trigs = np.where(trigger >= thresh)[0]
diff_trigs = np.diff(trigs)
big_trigs = np.where(diff_trigs > num_samples_between_triggers)[0]
trigTimes = np.r_[trigs[0], trigs[big_trigs + 1]]

# %% Optional: remove every other for alternate triggering
# trigTimes = trigTimes[::2]

# %% Optional: remove specific indices
# remove_indices = [0, 53, 108, 163]
# trigTimes = np.delete(trigTimes, remove_indices)

# %% --- Plot with trigger markers ---
plt.figure()
plt.plot(trigger[::plot_ds])
plt.scatter(trigTimes // plot_ds, np.full_like(trigTimes // plot_ds, thresh),
            color='red', edgecolors='red', facecolors='none')
for i, x in enumerate(trigTimes // plot_ds):
    plt.text(x, thresh, str(i), color='black', fontsize=9, ha='left', va='bottom')
plt.title('Trigger Detection with Markers')
plt.show()

# %% --- add constant to trigtimes ---
trigTimes += int(round(0.0234 * freq))

# %% --- Save trigTimes to file ---
np.save('../trigTimes.npy', trigTimes)

print("Trigger times saved to trigTimes.npy")
