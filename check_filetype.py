#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse
from re import match
from typing import List


def get_parser() -> argparse.ArgumentParser:  # parses flags in command
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter, description="",
        epilog="""
        Made by Aaron Earle-Richardson (ae166@duke.edu)
        """)

    parser.add_argument("-d", "--directory", required=True, default=None,
                       help="""
        Input data directory
        """)

    parser.add_argument("-t", "--ext", required=True, default=None,
                        help="File type")

    return parser


def list_subdir(folder: str) -> List[str]:
    out_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            out_files.append(os.path.join(root, file))
    return out_files


def check_ext(filename: str, ext: str) -> bool:
    out = filename.lower().endswith(ext)
    return out


def main(directory: str, ext: str):
    out: List[str] = []
    dirs = os.listdir(directory)
    for pat in dirs:
        folder = os.path.join(directory, pat)
        if match("^D\\d{2}", pat) and os.path.isdir(folder):
            if not any([check_ext(file, ext) for file in list_subdir(folder)]):
                out.append(pat)
    return out


if __name__ == "__main__":
    args = get_parser().parse_args()
    print(os.path.basename(vars(args)['directory']))
    for item in main(**vars(args)):
        print(item)
