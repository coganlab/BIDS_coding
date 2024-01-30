#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
from pathlib import Path
from typing import Union, TypeVar

import numpy as np
import pandas as pd

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

    def displayable(self) -> Union[Path, str]:
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



# this part of the code creates the tree graphic
def tree(path):
    paths = DisplayablePath.make_tree(Path(path))
    for path_to_display in paths:
        print(path_to_display.displayable())


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


def bids_validator(bids_dir):
    assert bids_dir is not None, "Cannot launch bids-validator wit" \
                                       "hout specifying bids directory !"
    subprocess.check_call(['bids-validator',
                           bids_dir])


def str2num(s: str) -> Union[float, str]:
    if is_number(s):
        return float(s)
    else:
        return s


def slice_time_calc(TR, sNum, totNum, delay):
    intervaltime = (TR - delay) / totNum
    tslice = delay + ((sNum) * intervaltime)
    return tslice


def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError

