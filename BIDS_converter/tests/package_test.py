from BIDS_converter.data2bids import Data2Bids
from BIDS_converter import utils
import shutil
import os
import tarfile
import pytest

src_path = "Data/Phoneme_Sequencing/sourcedata"
eeg_path = "Data/Phoneme_Sequencing/eeg_data"
BIDS_path = "Data/Phoneme_Sequencing/BIDS"


@pytest.mark.parametrize("sub", [
    "D52",
    "D48"
])
def test_sub(sub):
    pass
    # os.makedirs(BIDS_path, exist_ok=True)
    #
    # error = None
    # files = None
    #
    # my_list = [i for i in os.listdir(eeg_path) if i.startswith(sub)]
    # assert my_list
    # eeg_files = []
    # for file in my_list:
    #     eeg_fullfile = os.path.join(eeg_path, file)
    #     print("Unizipping: {}".format(eeg_fullfile))
    #     eeg_files.append(file.rstrip(".tar.xz"))
    #     with tarfile.open(eeg_fullfile, mode="r:xz") as f:
    #         f.extractall(path=os.path.join(src_path, sub))
    # try:
    #     d2b = Data2Bids(input_dir=os.path.join(src_path, sub),
    #                     output_dir=BIDS_path,
    #                     stim_dir=os.path.join(src_path, "stimuli"),
    #                     overwrite=True,
    #                     verbose=True)
    #     d2b.run()
    #     part_match_z = d2b.part_check(eeg_files[0])[1]
    #     files = [x for x in os.listdir(os.path.join(BIDS_path,
    #                                                 "sub-" + part_match_z))]
    # except Exception as e:
    #     error = e
    # finally:
    #     while os.path.isdir(BIDS_path):
    #         shutil.rmtree(BIDS_path, ignore_errors=True)
    #     for file in eeg_files:
    #         eeg_full_path = os.path.join(src_path, sub, file)
    #         os.chmod(eeg_full_path, 0o777)
    #         os.remove(eeg_full_path)
    #     if error:
    #         raise error
    #     else:
    #         return files
