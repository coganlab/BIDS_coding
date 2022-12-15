import gzip
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from re import match
from typing import Union, TypeVar

import nibabel as nib
import numpy as np

PathLike = TypeVar("PathLike", str, os.PathLike)


def run_dcm2niix(subdir: PathLike, fobj: object, scan_num: str, runlist: list, sub_dir: PathLike, sub_num):
    # not including parent folder or /medata, run dcm2niix on non
    # me data

    firstfile = [x[2] for x in os.walk(subdir)][0][0]
    # running dcm2niix
    if str(fobj[0x20, 0x11].value) in runlist:
        proc = subprocess.Popen(
            "dcm2niix -z y -f run{SCAN_NUM}_%p_%t_sub{SUB_NUM} -o "
            "{OUTPUT_DIR} -s y -b y {DATA_DIR}".format(
                OUTPUT_DIR=sub_dir, SUB_NUM=sub_num,
                DATA_DIR=os.path.join(subdir, firstfile),
                SCAN_NUM=scan_num), shell=True,
            stdout=subprocess.PIPE)
        outs, errs = proc.communicate()
        prefix = match(".*/sub-{SUB_NUM}/(run{SCAN_NUM}".format(
            SUB_NUM=sub_num, SCAN_NUM=scan_num
        ) + r"[^ \(\"\\n\.]*).*", str(outs)).group(1)
        for file in os.listdir(sub_dir):
            mefile = match(r"run{SCAN_NUM}(\.e\d\d)\.nii"
                           r"".format(SCAN_NUM=scan_num), file)
            if match(r"run{SCAN_NUM}\.e\d\d.nii".format(
                    SCAN_NUM=scan_num), file):
                shutil.move(os.path.join(sub_dir, file),
                            os.path.join(sub_dir, prefix + mefile.group(
                                1) + ".nii"))
                shutil.copy(os.path.join(sub_dir, prefix + ".json"),
                            os.path.join(sub_dir, prefix + mefile.group(
                                1) + ".json"))
        os.remove(os.path.join(sub_dir, prefix + ".nii.gz"))
        os.remove(os.path.join(sub_dir, prefix + ".json"))
    else:
        proc = subprocess.Popen(
            "dcm2niix -z y -f run{SCAN_NUM}_%p_%t_sub{SUB_NUM} -o "
            "{OUTPUT_DIR} -b y {DATA_DIR}".format(
                OUTPUT_DIR=sub_dir, SUB_NUM=sub_num,
                DATA_DIR=subdir, SCAN_NUM=scan_num), shell=True,
            stdout=subprocess.PIPE)
        outs, errs = proc.communicate()
    sys.stdout.write(outs.decode("utf-8"))


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


def mri_file_transfer(source: PathLike, destination: PathLike,
                      new_name: str, config: dict):
    file = os.path.basename(source)
    compress = config["compress"]
    final_file = os.path.join(destination, new_name + ".nii")
    # we convert it using nibabel
    if not any(file.endswith(ext) for ext in [".nii", ".nii.gz"]):
        # check if .nii listed in config file, not if file ends with .nii
        # loading the original image
        nib_img = nib.load(source)
        nib_affine = np.array(nib_img.affine)
        nib_data = np.array(nib_img.dataobj)

        # create the nifti1 image
        # if minc format, invert the data and change the affine
        # transformation there is also an issue on minc headers
        if file.endswith(".mnc"):
            if len(nib_img.shape) > 3:
                nib_affine[0:3, 0:3] = nib_affine[0:3, 0:3]
                rot_z(np.pi / 2)
                rot_y(np.pi)
                rot_x(np.pi / 2)
                nib_data = nib_data.T
                nib_data = np.swapaxes(nib_data, 0, 1)

                nifti_img = nib.Nifti1Image(nib_data, nib_affine,
                                            nib_img.header)
                nifti_img.header.set_xyzt_units(xyz="mm", t="sec")
                zooms = np.array(nifti_img.header.get_zooms())
                zooms[3] = config["repetitionTimeInSec"]
                nifti_img.header.set_zooms(zooms)
            elif len(nib_img.shape) == 3:
                nifti_img = nib.Nifti1Image(nib_data, nib_affine,
                                            nib_img.header)
                nifti_img.header.set_xyzt_units(xyz="mm")
        else:
            nifti_img = nib.Nifti1Image(nib_data, nib_affine,
                                        nib_img.header)

        # saving the image
        nib.save(nifti_img, final_file + ".gz")

    # if it is already a nifti file, no need to convert it so we just copy
    # rename
    if file.endswith(".nii.gz"):
        copy_file(source, final_file + ".gz")
    elif file.endswith(".nii"):
        copy_file(source, final_file)
        # compression just if .nii files
        if compress is True:
            print("zipping " + file)
            with open(final_file, 'rb') as f_in:
                with gzip.open(final_file + ".gz", 'wb',
                               config["compressLevel"]) as f_out:
                    copy_file(f_in, f_out, is_obj=True)
            os.remove(final_file)


def force_remove(mypath: PathLike):
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


def delete_folder(pth: PathLike):
    for sub in pth.iterdir():
        if sub.is_dir():
            delete_folder(sub)
        else:
            sub.unlink()
    pth.rmdir()


def copy_file(src: Union[PathLike, object], dst: Union[PathLike, object], is_obj: bool = False):
    if is_obj:
        if isinstance(src, object) and isinstance(dst, object):
            shutil.copyfileobj(src, dst)
        else:
            raise TypeError("Inputs given are not objects")
    else:
        shutil.copyfile(src, dst)
