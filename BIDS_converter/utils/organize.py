import os.path as op
import re
from os import listdir
from typing import List, Dict, Union, Any

import exrex as ex
import pandas as pd
from matgrab import mat2df
from scipy.io import wavfile
from numpy import nan

from .utils import is_number, PathLike, str2num


def gather_metadata(mat_files: List[PathLike]) -> pd.DataFrame:
    df = pd.DataFrame()
    for mat_file in mat_files:
        df_new = mat2df(mat_file)
        # check to see if new data is introduced. If not then keep
        # searching
        if isinstance(df_new, pd.Series):
            df_new = pd.DataFrame(df_new)
        if df_new.shape[0] > df.shape[0]:
            df = pd.concat(
                [df[df.columns.difference(df_new.columns)], df_new],
                axis=1)  # auto filters duplicates
        elif df_new.shape[0] == df.shape[0]:
            df = pd.concat(
                [df, df_new[df_new.columns.difference(df.columns)]],
                axis=1)  # auto filters duplicates
    return df


def frame2bids(df_in: pd.DataFrame, event_format: Dict[str, str],
               stim_dir: PathLike, data_sample_rate: int = None) -> pd.DataFrame:
    # start_at = df_in[event_format["Events"][0]["onset"]].iloc[
    #         0] / event_format["SampleRate"]
    new_df = reframe_events(df_in, event_format["Events"].copy(),
                            stim_dir, event_format["SampleRate"])

    for name in ["onset", "duration"]:
        if not (pd.api.types.is_float_dtype(
                new_df[name]) or pd.api.types.is_integer_dtype(
            new_df[name])):
            new_df[name] = pd.to_numeric(new_df[name], errors="coerce")
    if data_sample_rate is not None:
        # sample is in exact sample of event onset (at eeg sample rate)
        new_df["sample"] = new_df["onset"] * data_sample_rate
        # round sample to nearest frame
        new_df["sample"] = pd.to_numeric(new_df["sample"].round(
            ), errors="coerce", downcast="integer")

    return new_df.sort_values(["trial_num", "event_order"]).drop(
        columns="event_order")


def reframe_events(df_in: pd.DataFrame, events: Union[list, dict],
                   stim_dir: PathLike, mat_sample_rate) -> pd.DataFrame:
    df = df_in.copy()
    new_df = None
    if isinstance(events, dict):
        events = list(events)
    event_order = 0
    for event in events:
        event_order += 1
        # check if df column is actually a string of a list, then fix the data type and reorder the events
        list_dfs = []
        for val in [vals for vals in event.values() if vals in df_in.columns]:
            if isinstance(df[val][0], str) and all(char in df[val][0] for char in '[]'):
                # fix string data meant to be a list
                df[val] = df[val].apply(str2list)
            if isinstance(df[val][0], list):
                list_dfs.append(val)
                num_new = len(max(df[val], key=len))

        if list_dfs:
            # add new columns to old dataframe
            df = pd.concat([pd.DataFrame(df[x].tolist(), index=df.index).add_prefix(x) for x in
                            list_dfs] + [df], axis=1)
            # add new event config
            new_events = []
            new_event = event.copy()
            for i in range(num_new):
                for key, value in event.items():
                    if value in list_dfs:
                        new_event[key] = value + str(i)
                new_events.append(new_event.copy())
            events[event_order:event_order] = new_events
            # reset event reading with new event definitions
            event_order -= 1
            continue

        temp_df = pd.DataFrame()
        for key, value in event.items():
            if key == "stim_file":
                df[value] = check_stims(stim_dir, df[value])
                temp_df["stim_file"] = df[value]
                temp_df["duration"] = df[value].apply(
                    wavfile_dur, dir=stim_dir).astype(float)
            elif key in ["onset", "duration"]:
                temp_df[key] = eval_df(df, value).astype(
                    float) / mat_sample_rate
            else:
                temp_df[key] = eval_df(df, value)
        if "trial_num" not in temp_df.columns:
            temp_df["trial_num"] = [1 + i for i in list(range(temp_df.shape[0]))]
        temp_df.dropna(axis=0, how="all", subset=["onset", "duration"], inplace=True)
            # TODO: make code below work for non correction case
        ''' 
            if "duration" not in temp_df.columns:
            if "stim_file" in temp_df.columns:
                temp = []
                t_correct = []
                for _, fname in temp_df["stim_file"].iteritems():
                    if fname.endswith(".wav"):
                        if self.stim_dir is not None:
                            fname = op.join(self.stim_dir, fname)
                            dir = self.stim_dir
                        else:
                            dir = self._data_dir
                        try:
                            frames, data = wavfile.read(fname)
                        except FileNotFoundError as e:
                            print(fname + " not found in current directory
                             or in " + dir)
                            raise e
                        if audio_correction is not None:
                            correct = audio_correction.set_index(0).squeeze
                            ()[op.basename(
                                op.splitext(fname)[0])] * self._config["eve
                                ntFormat"]["SampleRate"]
                        else:
                            correct = 0
                        duration = (data.size / frames) * self._config["eve
                        ntFormat"]["SampleRate"]
                    else:
                        raise NotImplementedError("current build only suppo
                        rts .wav stim files")
                    temp.append(duration)
                    t_correct.append(correct)
                temp_df["duration"] = temp
                # audio correction
                if t_correct:
                    temp_df["correct"] = t_correct
                    temp_df["duration"] = temp_df.eval("duration - correct"
                    )
                    temp_df["onset"] = temp_df.eval("onset + correct")
                    temp_df = temp_df.drop(columns=["correct"])
            else:
                raise LookupError("duration of event or copy of audio file 
                required but not found in " +
                                  self._config_path)
        '''
        temp_df["event_order"] = event_order
        if new_df is None:
            new_df = temp_df
        else:
            new_df = pd.concat([new_df, temp_df], ignore_index=True, sort=False)
    return new_df


def get_timing_from_tsv(file_path: PathLike,
                        sample_rate: int) -> List[int]:
    """reads tsv files to determine sectioning of eeg files

    :param file_path:
    :type file_path:
    :param signal_headers:
    :type signal_headers:
    :return:
    :rtype:
    """
    df = pd.read_csv(file_path, sep="\t", header=0)
    # converting signal start and end to correct sample rate for data
    eval_col = df["duration"] + df["onset"]
    end_num = str2num(eval_col.iloc[-1])
    i = -1
    while not is_number(end_num):
        i -= 1
        end_num = str2num(eval_col.iloc[i])

    eval_col = df["onset"]
    start_num = eval_col.iloc[0]
    i = 0
    while not is_number(start_num):
        i += 1
        start_num = str2num(eval_col.iloc[i])

    num_list = [round((float(x)) * sample_rate) for x in (start_num, end_num)]
    return num_list


def reset_zero(tsv_name: PathLike, last_prior: int, sample_rate: int, verbose: bool = False):
    df = pd.read_csv(tsv_name, sep="\t", header=0)
    df["sample"] = df["sample"] - last_prior
    df["onset"] = df["sample"] / sample_rate
    if verbose:
        print(df)
    df.to_csv(tsv_name, sep="\t", index=False, na_rep="n/a")


def check_stims(stim_dir: PathLike, labels: pd.Series) -> pd.Series:
    out_label = labels.copy()
    files = listdir(stim_dir)
    for i, label in enumerate(labels.tolist()):
        if label is None:
            out_label.iloc[i] = None
        elif label in files:
            out_label.iloc[i] = label
        elif label + ".wav" in files:
            out_label.iloc[i] = label + ".wav"
        else:
            out_label.iloc[i] = check_lower(label, files)
    return out_label


def check_lower(item: str, string_list: List[str]) -> str:
    for stim_file in string_list:
        if item in stim_file.lower():
            return stim_file
    raise FileNotFoundError("No stim files match {}".format(item))


def trigger_from_excel(filename: PathLike, participant: str) -> Union[int, str]:
    """replace trigger channels with trigger label

    :param filename:
    :type filename:
    :param participant:
    :type participant:
    :return:
    :rtype:
    """
    xls_file = filename
    xls_df = pd.ExcelFile(filename).parse(participant)

    if any("Trigger" in column for column in xls_df):
        for column in xls_df:
            if "Trigger" in column:
                trig_label = xls_df[column].iloc[0]
                if is_number(trig_label):
                    return int(trig_label)
                else:
                    return trig_label
    else:
        raise KeyError("'Trigger' not found in " + xls_file)


def match_regexp(config_regexp: Dict[str, Any], filename: PathLike,
                 subtype: bool = False) -> re.match:
    delimiter_left = config_regexp["left"].replace("(", "(?:")
    delimiter_right = config_regexp["right"].replace("(", "(?:")
    match_found = False

    if subtype:
        for to_match in config_regexp["content"]:
            if re.match(".*?"
                        + delimiter_left
                        + '(' + to_match[1].replace("(", "(?:") + ')'
                        + delimiter_right
                        + ".*?", filename):
                match = to_match[0]
                match_found = True
    else:
        for to_match in config_regexp["content"]:
            if re.match(".*?"
                        + delimiter_left
                        + '(' + to_match.replace("(", "(?:") + ')'
                        + delimiter_right
                        + ".*?", filename):
                match = re.match(".*?"
                                 + delimiter_left
                                 + '(' + to_match.replace("(", "(?:") + ')'
                                 + delimiter_right
                                 + ".*?", filename).group(1)
                match_found = True
    assert match_found
    return match


def gen_match_regexp(config_regexp: Dict[str, Any], data: str,
                     subtype: bool = False) -> str:
    """takes a match config and generates a matching string

    :param config_regexp:
    :type config_regexp:
    :param data:
    :type data:
    :param subtype:
    :type subtype:
    :return:
    :rtype:
    """
    if data.startswith("0"):
        data = data.lstrip("0")
    match_found = False
    for to_match in config_regexp["content"]:
        if re.match(to_match, data):
            match_found = True
    if not match_found:
        raise AssertionError(
            "{newname} doesn't match config criteria {given}".format(
                newname=data, given=config_regexp["content"]))
    left = ex.getone(config_regexp["left"])
    right = ex.getone(config_regexp["right"])
    newname = left + data + right

    try:
        if data == match_regexp(config_regexp, newname, subtype=subtype):
            return newname
        else:
            raise ValueError("{newname} doesn't match config criteria".format(
                newname=newname))
    except AssertionError:
        # return self.gen_match_regexp(config_regexp, data.lstrip("0"),subtype)
        # except RecursionError:
        raise AssertionError(
            "{newname} doesn't match config criteria {given}".format(
                newname=newname, given=config_regexp))


def prep_tsv(file_path: PathLike, task: str, pmatchz: str, ieeg_config: dict,
                bids_dir: PathLike) -> (str, pd.DataFrame):
    df = None
    for name, var in ieeg_config["channels"].items():
        if name in file_path:
            df = mat2df(file_path, var)
            if "highpass_cutoff" in df.columns.to_list():
                df = df.rename(columns={"highpass_cutoff": "high_cutoff"})
            if "lowpass_cutoff" in df.columns.to_list():
                df = df.rename(columns={"lowpass_cutoff": "low_cutoff"})
    df["type"] = ieeg_config["type"]
    df["units"] = ieeg_config["units"]
    df = df.append(
        {"name": "Trigger", "high_cutoff": 1, "low_cutoff": 1000,
         "type": "TRIG", "units": "uV"}, ignore_index=True)
    df = pd.concat([df["name"], df["type"], df["units"], df["low_cutoff"],
                    df["high_cutoff"]], axis=1)
    filename = op.join(bids_dir, "sub-{}".format(pmatchz),
                       "sub-" + pmatchz + "_task-{}".format(
                           task) + "_channels.tsv")
    return filename, df


def tsv_all_eeg(fname: PathLike, df: pd.DataFrame, data_types: Dict[str, bool]):
    """Writes tsv files into each folder containing eeg data

    :param data_types:
    :param fname:
    :type fname:
    :param df:
    :type df:
    :return:
    :rtype:
    """
    for d_type in data_types.keys():
        if not ("eeg" in d_type and data_types[d_type]):
            continue
        file_name = op.join(op.dirname(fname), d_type, op.basename(fname))
        df.to_csv(file_name, sep="\t", index=False)


def prep_coordsystem(txt_df_dict: Dict[str, Union[pd.DataFrame, str]],
                     part_match_z: str, bids_dir: PathLike) -> (
        str, pd.DataFrame):
    if txt_df_dict["error"] is not None:
        raise txt_df_dict["error"]
    df: pd.DataFrame = txt_df_dict["data"]
    df.columns = ["name1", "name2", "x", "y", "z", "hemisphere", "del"]
    df["name"] = df["name1"] + df["name2"].astype(str)
    df["hemisphere"] = df["hemisphere"] + df["del"]
    df = df.drop(columns=["name1", "name2", "del"])
    df = pd.concat(
        [df["name"], df["x"], df["y"], df["z"], df["hemisphere"]], axis=1)
    filename = op.join(bids_dir, "sub-" + part_match_z,
                       "sub-{}_space-Talairach_electrodes.tsv"
                       "".format(part_match_z))
    return filename, df


def eval_df(df: pd.DataFrame, exp: str) -> pd.Series:
    """input a df and expression and return a single dataframe column

    :param df:
    :type df:
    :param exp:
    :type exp:
    :param file_dir:
    :type file_dir:
    :return:
    :rtype:
    """
    if exp in df.columns:
        return df[exp].squeeze()
    for name in [i for i in re.split(r"[ +\-/*%]", exp) if i != '']:
        if name in df.columns:
            if is_number(df[name]):
                df[name] = df[name].astype(float)
            else:
                df[name] = df[name]
        elif not is_number(name):
            if len([i for i in re.split(r"[ +\-/*%]", exp) if i != '']) > 1:
                continue
            return pd.Series([name] * df.shape[0], dtype="string")
        else:
            df[name] = pd.Series([float(name)] * df.shape[0], dtype="float")
    return df.eval(exp).squeeze()


def wavfile_dur(filename: Union[PathLike, None], dir: PathLike = None) -> float:
    """"""
    if filename is None:
        return nan
    if dir is not None:
        filename = op.join(dir, filename)
    frames, data = wavfile.read(filename)
    duration = data.shape[0] / frames
    return float(duration)


def str2list(x: str) -> list:
    ttable = "".maketrans({'[': '', ']': '', '\'': ''})
    return [str2num(x) for x in x.translate(ttable).split()]
