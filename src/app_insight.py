import os
import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
import seaborn as sns

import pandas as pd
import ttkthemes

from gui_parts import TempFile
from main_gui_parts import PklSelector
from python_senpai import keypoints_proc, windows_and_mac, file_inout, vcap
from python_senpai import time_format


class App(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        master.title("Behavior Senpai Insight")
        self.pack(padx=14, pady=14)

        temp = TempFile()
        w_width, w_height = temp.get_top_window_size()
        w_height = int(w_height)

        # ボタンのフレーム
        load_frame = ttk.Frame(self)
        load_frame.pack(side=tk.TOP, anchor=tk.NW)

        self.pkl_selector = PklSelector(load_frame)
        self.pkl_selector.pack(side=tk.LEFT)
        self.pkl_selector.set_command(cmd=self.load_trk)

        self.feat_button = ttk.Button(load_frame, text="Open Feature file", command=self.load_feat)
        self.feat_button.pack(side=tk.LEFT, padx=(20, 0))
        self.feat_path_label = ttk.Label(load_frame, text="No Feature file loaded")
        self.feat_path_label.pack(side=tk.LEFT, padx=(5, 0))

        graph_setting_frame = ttk.Frame(self)
        graph_setting_frame.pack(side=tk.TOP, anchor=tk.NW, pady=(6, 0))

        fig_size_label = ttk.Label(graph_setting_frame, text="Figure size:")
        fig_size_label.pack(side=tk.LEFT)
        self.fig_width_entry = ttk.Entry(graph_setting_frame, width=5)
        self.fig_width_entry.insert(tk.END, '24')
        self.fig_width_entry.pack(side=tk.LEFT, padx=(0, 5))
        fig_height_label = ttk.Label(graph_setting_frame, text="x")
        fig_height_label.pack(side=tk.LEFT)
        self.fig_height_entry = ttk.Entry(graph_setting_frame, width=5)
        self.fig_height_entry.insert(tk.END, '8')
        self.fig_height_entry.pack(side=tk.LEFT, padx=(0, 5))

        setting_frame = ttk.Frame(self)
        setting_frame.pack(side=tk.TOP, anchor=tk.NW, pady=(6, 0))
        # member選択コンボボックス、初期値はmember
        self.member_combo = ttk.Combobox(setting_frame, state="disabled")
        self.member_combo.pack(side=tk.LEFT)
        self.member_combo["values"] = ["member"]
        self.member_combo.current(0)

        # column選択リストボックス、複数選択
        self.column_listbox = tk.Listbox(setting_frame, selectmode=tk.EXTENDED, exportselection=False)
        self.column_listbox.pack(side=tk.LEFT, padx=(5, 0))

        # scene選択リストボックス、複数選択
        self.scene_listbox = tk.Listbox(setting_frame, selectmode=tk.EXTENDED, exportselection=False)
        self.scene_listbox.pack(side=tk.LEFT, padx=(5, 0))

        test_button = ttk.Button(setting_frame, text="Draw", command=self.draw)
        test_button.pack(side=tk.LEFT, padx=(5, 0))
        self.cap = vcap.VideoCap()

        self.load_trk()

    def load_trk(self):
        pkl_path = self.pkl_selector.get_trk_path()
        load_df = file_inout.load_track_file(pkl_path)
        if load_df is None:
            self.pkl_selector.rename_pkl_path_label(self.pkl_path)
            return
        self.pkl_path = pkl_path
        self.trk_df = load_df
        self.trk_df = keypoints_proc.zero_point_to_nan(self.trk_df)
        self.trk_df = self.trk_df[~self.trk_df.index.duplicated(keep="first")]
        src_attrs = self.trk_df.attrs
        self.pkl_dir = os.path.dirname(self.pkl_path)
        self.cap.set_frame_size(src_attrs["frame_size"])
        self.cap.open_file(os.path.join(self.pkl_dir, os.pardir, src_attrs["video_name"]))

        # UIの更新
        self.pkl_selector.set_prev_next(src_attrs)
        self.scene_dict = self.trk_df.attrs['scene_table']
        self.scene_listbox.delete(0, tk.END)
        for scene, start, end in zip(self.scene_dict['description'], self.scene_dict['start'], self.scene_dict['end']):
            duration = time_format.timestr_to_msec(end) - time_format.timestr_to_msec(start)
            self.scene_listbox.insert(tk.END, f"{scene} ({duration/1000:.1f}sec)")

    def load_feat(self):
        pkl_path = file_inout.open_pkl(os.path.dirname(self.pkl_dir))
        if pkl_path is None:
            return
        self.feat_path_label["text"] = pkl_path
        self.feat_path = pkl_path
        self.feat_df = file_inout.load_track_file(pkl_path, allow_calculated_track_file=True)

        # UIの更新
        self.member_combo['state'] = 'readonly'
        self.member_combo["values"] = self.feat_df.index.get_level_values("member").unique().tolist()
        self.member_combo.current(0)
        self.column_listbox.delete(0, tk.END)
        for col in self.feat_df.columns:
            if col == 'timestamp':
                continue
            self.column_listbox.insert(tk.END, col)

    def draw(self):
        tar_member = self.member_combo.get()
        scene_selected = self.scene_listbox.curselection()
        # self.scene_dict['description']のvalueに重複があったらnumber suffixを付与
        # ['a', 'a', 'b'] -> ['a', 'a_1', 'b']
        scene_desc = self.scene_dict['description']
        scene_desc = pd.Series(scene_desc)
        scene_suffix = scene_desc.groupby(scene_desc).cumcount().astype(str)
        print(scene_suffix)
        scene_desc = scene_desc.str.cat(scene_suffix, sep='_').tolist()
        self.scene_dict['description'] = scene_desc

        scenes = [{"description": self.scene_dict['description'][idx],
                   "start": self.scene_dict['start'][idx],
                   "end": self.scene_dict['end'][idx]} for idx in scene_selected]
        scene_num = len(scenes)
        column_selected = self.column_listbox.curselection()
        columns = [self.column_listbox.get(idx) for idx in column_selected]

        margin = 0.1
        hspace = 0.05
        fig_width = int(self.fig_width_entry.get())
        fig_height = int(self.fig_height_entry.get())
        fig, axes = plt.subplots(scene_num, 2, sharex='col', sharey='all', gridspec_kw={'hspace': hspace, 'wspace': 0.1, 'top': 1-margin, 'bottom': margin})
        fig.set_size_inches(fig_width, fig_height)

        idx = pd.IndexSlice
        for i, scene in enumerate(scenes):
            start_ms = time_format.timestr_to_msec(scene["start"])
            end_ms = time_format.timestr_to_msec(scene["end"])
            duration = end_ms - start_ms
            scene_df = keypoints_proc.filter_by_timerange(self.feat_df, start_ms, end_ms)
            scene_df = scene_df.loc[idx[:, tar_member], columns+['timestamp']]
            # level=1のindexを削除
            scene_df = scene_df.reset_index(level=1, drop=True)
            scene_dfm = scene_df.melt(id_vars='timestamp', var_name='column', value_name='value')

            # グラフの外側(左側)に複数行のtextを表示
            text_step = 1 - (margin + (1-margin-hspace*1.75) * i / scene_num)
            text_content = f"{scene['description']}\n{scene['start']}-{scene['end']}\n{duration/1000:.1f}sec"
            axes[i][0].text(0.03, text_step, text_content, ha='left', va='top',
                            transform=fig.transFigure, fontsize=8, linespacing=1.5)
            plot = sns.lineplot(data=scene_dfm, x='timestamp', y='value', hue='column', ax=axes[i][0])
            plot.set_xlabel("timestamp")
            plot.set_ylabel("value")
            scene_df = scene_df.drop(columns='timestamp')
            violin = sns.violinplot(data=scene_df, ax=axes[i][1])
            print(scene["description"], scene["start"], scene["end"])
            print(scene_df)
            # i=0だけlegendを表示
            if i == 0:
                axes[i][0].legend(loc='upper right')
            else:
                axes[i][0].get_legend().remove()
        plt.show()


def quit(root):
    root.quit()
    root.destroy()


def main():
    bg_color = "#e8e8e8"
    root = ttkthemes.ThemedTk(theme="breeze")
    root.configure(background=bg_color)
    root.option_add("*background", bg_color)
    root.option_add("*Canvas.background", bg_color)
    root.option_add("*Text.background", "#fcfcfc")
    windows_and_mac.set_app_icon(root)
    s = ttk.Style(root)
    s.configure(".", background=bg_color)
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", lambda: quit(root))
    app.mainloop()


if __name__ == "__main__":
    main()
