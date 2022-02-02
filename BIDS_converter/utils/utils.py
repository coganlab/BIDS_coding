#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import shutil
import stat
import threading
from pathlib import Path
from typing import TypeVar, Union, Generic, get_type_hints, get_args

import exrex as ex
import numpy as np
import pandas as pd
from pyedflib import EdfReader
from scipy.io import wavfile


PathLike = TypeVar("PathLike", str, os.PathLike)


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


def is_number(s):
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


def str2num(s):
    if is_number(s):
        return float(s)
    else:
        return s


def slice_time_calc(TR, sNum, totNum, delay):
    intervaltime = (TR - delay) / totNum
    tslice = delay + ((sNum) * intervaltime)
    return tslice


def delete_folder(pth):
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


def force_remove(mypath):
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
            file_dir: PathLike = ""):
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

    assert isinstance(file_dir, (os.PathLike, str))

    for name in [i for i in re.split(r"[ +\-/*%]", exp) if i != '']:
        if name in df.columns:
            if is_number(df[name]):
                df[name] = pd.to_numeric(df[name])
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
            df[name] = pd.Series([name] * df.shape[0])
    return df.eval(exp).squeeze()


def trigger_from_excel(filename, participant):
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
