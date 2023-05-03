import os
import json
import re
from matgrab import mat2df
from BIDS_converter.utils.organize import from_excel
from BIDS_converter.utils.utils import is_number


HOME = os.path.expanduser("~")
DUKEDIR = os.path.join(HOME, "Box", "CoganLab", "D_Data")
TASKS = ['Environmental_Sternberg', 'GlobalLocal', 'Lexical',
         'LexicalDecRepDelay', 'LexicalDecRepNoDelay',
         'Neighborhood_Sternberg', 'Phoneme_Sequencing', 'SentenceRep',
         'timit', 'Uniqueness_Point']


def remove_from_brackets(string: str):
    pattern = r'\[[^]]*\]'
    found = re.findall(pattern, string)

    for f in found:
        string = string.replace(f, re.sub(r'\s', '', f))

    return string


def updateJsonFile(filename: str, data: dict, task: str, sub: str):

    names = [n.strip() for n in data["channels"]]
    try:
        with open(filename, "r") as jsonFile: # Open the JSON file for reading
            current = json.load(jsonFile)
    except (json.JSONDecodeError, FileNotFoundError):
        current = {}  # Read the JSON into the buffer

    # Working with buffered content
    if sub not in current.keys():
        current[sub] = {"default": data}
    elif any(n not in current[sub]['default']['channels'] for n in names):
        current[sub]['default']['channels'] = list(
            set(current[sub]['default']['channels'] + names))
    elif any(n not in names for n in current[sub]["default"]["channels"]):
        current[sub][task] = data

    # sort the dictionary
    myKeys = list(current.keys())
    myKeys.sort()
    sorted_dict = {i: current[i] for i in myKeys}

    # Save our changes to JSON file
    out_str = remove_from_brackets(json.dumps(sorted_dict, indent=4))

    with open(filename, "w+") as jsonFile:
        jsonFile.write(out_str)


for task in TASKS:
    DATADIR = os.path.join(DUKEDIR, task)
    for sub in [s for s in os.listdir(DATADIR) if s.startswith('D') and
                is_number(s[-1])]:
        for root, _, files in os.walk(os.path.join(DATADIR, sub)):
            for f in files:
                if f == "experiment.mat":
                    df = mat2df(os.path.join(root, f), "channels")
                    names = df["name"].tolist()
                    names.sort()
                    excel = os.path.join(os.path.dirname(
                        DUKEDIR), "ECoG_Task_Data", "Timestamps (MASTER).xlsx")
                    dtype = from_excel(excel, sub, "Type")
                    trig = from_excel(excel, sub, "Trigger")
                    if "grid" in dtype.lower():
                        dtype = "ecog"
                    elif "seeg" in dtype.lower():
                        dtype = "seeg"
                    else:
                        raise ValueError(f"dtype {dtype} not recognized")

                    data = {"channels": names, "dtype": dtype, "trigger": trig}

                    updateJsonFile("subjects.json", data, task, sub)

