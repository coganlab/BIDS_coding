#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import shutil
import stat
import threading
from pathlib import Path

import exrex as ex
import numpy as np
import pandas as pd
from pyedflib import EdfReader
from scipy.io import wavfile
from typing import List, Union


class DisplayablePath:
    """this code creates a tree visual to explain the BIDS file organization

    """
    display_filename_prefix_middle = '├──'
    display_filename_prefix_last = '└──'
    display_parent_prefix_middle = '    '
    display_parent_prefix_last = '│   '

    def __init__(self, path, parent_path, is_last):
        self.path = Path(str(path))
        self.parent = parent_path
        self.is_last = is_last
        if self.parent:
            self.depth = self.parent.depth + 1
        else:
            self.depth = 0

    @property
    def displayname(self):
        if self.path.is_dir():
            return self.path.name + '/'
        return self.path.name

    @classmethod
    def make_tree(cls, root, parent=None, is_last=False, criteria=None):
        root = Path(str(root))
        criteria = criteria or cls._default_criteria

        displayable_root = cls(root, parent, is_last)
        yield displayable_root

        children = sorted(list(path
                               for path in root.iterdir()
                               if criteria(path)),
                          key=lambda s: str(s).lower())
        count = 1
        for path in children:
            is_last = count == len(children)
            if path.is_dir():
                # yield from
                for i in cls.make_tree(path,
                                       parent=displayable_root,
                                       is_last=is_last,
                                       criteria=criteria):
                    yield i
            else:
                yield cls(path, displayable_root, is_last)
            count += 1

    @classmethod
    def _default_criteria(cls, path):
        return True

    def displayable(self):
        if self.parent is None:
            return self.path

        _filename_prefix = (self.display_filename_prefix_last
                            if self.is_last
                            else self.display_filename_prefix_middle)

        parts = ['{!s} {!s}'.format(_filename_prefix,
                                    self.displayname)]

        parent = self.parent
        while parent and parent.parent is not None:
            parts.append(self.display_parent_prefix_middle
                         if parent.is_last
                         else self.display_parent_prefix_last)
            parent = parent.parent

        return ''.join(reversed(parts))


def match_regexp(config_regexp, filename, subtype=False):
    delimiter_left = config_regexp["left"]
    delimiter_right = config_regexp["right"]
    match_found = False

    if subtype:
        for to_match in config_regexp["content"]:
            if re.match(".*?"
                        + delimiter_left
                        + '(' + to_match[1] + ')'
                        + delimiter_right
                        + ".*?", filename):
                match = to_match[0]
                match_found = True
    else:
        for to_match in config_regexp["content"]:
            if re.match(".*?"
                        + delimiter_left
                        + '(' + to_match + ')'
                        + delimiter_right
                        + ".*?", filename):
                match = re.match(".*?"
                                 + delimiter_left
                                 + '(' + to_match + ')'
                                 + delimiter_right
                                 + ".*?", filename).group(1)
                match_found = True
    assert match_found
    return match


def gen_match_regexp(config_regexp, data,
                     subtype=False):
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


def cat_edf(filename):
    f = EdfReader(filename)
    for i in range(f.signals_in_file):
        print(f.readSignal(i), threading.current_thread().getName())


def read_write_edf(read_obj, chn):
    if isinstance(chn, str):
        chn = read_obj.getSignalLabels().index(chn)
    read_obj.readSignal(chn)


# this part of the code creates the tree graphic
def tree(path):
    paths = DisplayablePath.make_tree(Path(path))
    for path_to_display in paths:
        print(path_to_display.displayable())


def rot_x(alpha):
    return np.array([[1, 0, 0]
                        , [0, np.cos(alpha), np.sin(alpha)]
                        , [0, -np.sin(alpha), np.cos(alpha)]])


def rot_y(alpha):
    return np.array([[np.cos(alpha), 0, -np.sin(alpha)]
                        , [0, 1, 0]
                        , [np.sin(alpha), 0, np.cos(alpha)]])


def rot_z(alpha):
    return np.array([[np.cos(alpha), np.sin(alpha), 0]
                        , [-np.sin(alpha), np.cos(alpha), 0]
                        , [0, 0, 1]])


def is_number(s: str) -> bool:
    if isinstance(s, str):
        try:
            float(s)
            return True
        except ValueError:
            return False
    elif isinstance(s, (np.number, int, float)):
        return True
    elif isinstance(s, pd.DataFrame):
        try:
            s.astype(float)
            return True
        except Exception:
            return False
    elif isinstance(s, pd.Series):
        try:
            pd.to_numeric(s)
            return True
        except Exception:
            return False
    else:
        return False


def str2num(s: str) -> Union[float, str]:
    if is_number(s):
        return float(s)
    else:
        return s


def slice_time_calc(TR, sNum, totNum, delay):
    intervaltime = (TR - delay) / totNum
    tslice = delay + ((sNum) * intervaltime)
    return tslice


def delete_folder(pth: os.PathLike):
    for sub in pth.iterdir():
        if sub.is_dir():
            delete_folder(sub)
        else:
            sub.unlink()
    pth.rmdir()


def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError


def force_remove(mypath: os.PathLike):
    x = 0
    e = None
    while os.path.isfile(mypath) or os.path.isdir(mypath):
        x += 1
        if os.path.isfile(mypath):
            os.remove(mypath)
        try:
            if os.path.isdir(mypath):
                delete_folder(Path(mypath))
        except OSError:
            try:
                shutil.rmtree(mypath)
            except PermissionError:
                for root, dirs, files in os.walk(mypath, topdown=False):
                    for file in files:
                        fullfile = os.path.join(root, file)
                        os.chmod(fullfile, stat.S_IWUSR)
                        os.remove(fullfile)
                    for dir in dirs:
                        try:
                            delete_folder(os.path.join(root, dir))
                        except AttributeError:
                            os.rmdir(os.path.join(root, dir))
                shutil.rmtree(mypath, ignore_errors=True)
            except Exception as e:
                shutil.rmtree(mypath, ignore_errors=True)
        if x >= 1000:
            if e is not None:
                raise RuntimeError(
                    mypath + " could not remove all files or directories becau"
                             "se of " + e)
            else:
                raise


def eval_df(df: pd.DataFrame, exp: str,
            file_dir: os.PathLike = "") -> pd.Series:
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
            elif os.path.isfile(os.path.join(file_dir, str(df[name].iloc[0]))):
                for i, (_, fname) in enumerate(df[name].iteritems()):
                    fname = os.path.join(file_dir, fname)
                    frames, data = wavfile.read(fname)
                    duration = data.size / frames
                    df[name].iat[i] = duration
                df[name] = df[name].astype(float)
            else:
                df[name] = df[name]
        elif not is_number(name):
            if len([i for i in re.split(r"[ +\-/*%]", exp) if i != '']) > 1:
                continue
                raise ValueError("The name {} is not a column in the file, and therefore"
                                 " cannot be in the experession {}\nColumns are {}".format(name, exp, df.columns))
            return pd.Series([name] * df.shape[0], dtype="string")
        else:
            df[name] = pd.Series([float(name)] * df.shape[0], dtype="float")
    return df.eval(exp).squeeze()


def trigger_from_excel(filename: os.PathLike, participant: str) -> Union[int, str]:
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


def str2list(x: str) -> list:
    ttable = "".maketrans({'[': '', ']': '', '\'': ''})
    return [str2num(x) for x in x.translate(ttable).split()]


def check_stims(stim_dir: os.PathLike, labels: pd.Series) -> pd.Series:
    out_label = labels.copy()
    files = os.listdir(stim_dir)
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


def reframe_events(df_in: pd.DataFrame, events: Union[list, dict],
                   stim_dir: os.PathLike) -> pd.DataFrame:
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
                temp_df["duration"] = eval_df(df, value, stim_dir)
            else:
                temp_df[key] = eval_df(df, value)
        if "trial_num" not in temp_df.columns:
            temp_df["trial_num"] = [1 + i for i in list(range(temp_df.shape[0]))]
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


def check_lower(item: str, string_list: List[str]) -> str:
    for stim_file in string_list:
        if item in stim_file.lower():
            return stim_file
    raise FileNotFoundError("No stim files match {}".format(item))
