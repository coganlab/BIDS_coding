import pandas as pd
import os
from typing import List, Dict, Union
from matgrab import mat2df
from .utils import str2list, check_stims, eval_df


def gather_metadata(mat_files: List[os.PathLike], labels: List[str] = None) -> pd.DataFrame:
    df = pd.DataFrame()
    for mat_file in mat_files:
        df_new = mat2df(mat_file, labels)
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
               stim_dir: os.PathLike, data_sample_rate: int = None,
               start_at: int = 0) -> pd.DataFrame:

    new_df = reframe_events(df_in, event_format["Events"].copy(), stim_dir)

    for name in ["onset", "duration"]:
        if not (pd.api.types.is_float_dtype(
                new_df[name]) or pd.api.types.is_integer_dtype(
            new_df[name])):
            new_df[name] = pd.to_numeric(new_df[name], errors="coerce")
    if data_sample_rate is None:
        # onset is timing of even onset (in seconds)
        new_df["onset"] = new_df["onset"] / event_format["SampleRate"]
    else:
        # sample is in exact sample of event onset (at eeg sample rate)
        new_df["sample"] = (new_df["onset"] / event_format[
            "SampleRate"] * data_sample_rate) - start_at
        # onset is timing of even onset (in seconds)
        new_df["onset"] = new_df["sample"] / data_sample_rate
        # round sample to nearest frame
        new_df["sample"] = pd.to_numeric(new_df["sample"].round(),
                                         errors="coerce",
                                         downcast="integer")
    # duration is duration of event (in seconds)
    new_df["duration"] = new_df["duration"] / event_format[
        "SampleRate"]

    return new_df.sort_values(["trial_num", "event_order"]).drop(
        columns="event_order")


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