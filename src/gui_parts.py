import os
import tkinter as tk
from tkinter import ttk

import pandas as pd


class PklSelector(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.load_pkl_btn = ttk.Button(master, text="Load Track")
        self.load_pkl_btn.pack(side=tk.LEFT)
        self.pkl_path_label = ttk.Label(master, text="No trk loaded")
        self.pkl_path_label.pack(side=tk.LEFT)
    
    def _load_pkl(self):
        init_dir = os.path.abspath(os.path.dirname(__file__))
        pkl_path = tk.filedialog.askopenfilename(initialdir=init_dir, title="Select pkl file", filetypes=[("pkl files", "*.pkl")])
        if pkl_path:
            self.pkl_path = pkl_path
            self.pkl_path_label["text"] = pkl_path
        else:
            self.pkl_path = None
            self.pkl_path_label["text"] = "No trk loaded"

    def set_command(self, cmd):
        self.load_pkl_btn["command"] = lambda: [self._load_pkl(), cmd()]


class MemberKeypointComboboxes(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.member_combo = ttk.Combobox(master, state='readonly', width=12)
        self.member_combo.pack(side=tk.LEFT, padx=5)
        self.member_combo.bind("<<ComboboxSelected>>", self._on_selected)
        self.keypoint_combo = ttk.Combobox(master, state='readonly', width=10)
        self.keypoint_combo.pack(side=tk.LEFT, padx=5)

    def set_df(self, src_df):
        self.src_df = src_df
        combo_df = self.src_df

        # memberとkeypointのインデックス値を文字列に変換
        idx = combo_df.index
        combo_df.index = self.src_df.index.set_levels([idx.levels[0], idx.levels[1].astype(str), idx.levels[2].astype(str)])

        self.member_combo["values"] = combo_df.index.get_level_values("member").unique().tolist()
        self.member_combo.current(0)
        init_member = self.member_combo.get()
        self.keypoint_combo["values"] = combo_df.loc[pd.IndexSlice[:, init_member, :], :].index.get_level_values("keypoint").unique().tolist()

    def _on_selected(self, event):
        current_member = self.member_combo.get()
        # keypointの一覧を取得してコンボボックスにセット
        idx = pd.IndexSlice[:, current_member, :]
        keypoints = self.src_df.loc[idx, :].index.get_level_values("keypoint").unique().tolist()
        self.keypoint_combo["values"] = keypoints
        self.keypoint_combo.current(0)

    def get_selected(self):
        member = self.member_combo.get()
        keypoint = self.keypoint_combo.get()
        return member, keypoint


class ProcOptions(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
 
        dt_span_label = ttk.Label(master, text="diff period:")
        dt_span_label.pack(side=tk.LEFT)
        self.dt_span_entry = ttk.Entry(master, width=5, validate="key", validatecommand=(self.register(self._validate), "%P"))
        self.dt_span_entry.insert(tk.END, '10')
        self.dt_span_entry.pack(side=tk.LEFT, padx=(0, 5))

        thinning_label = ttk.Label(master, text="thinning:")
        thinning_label.pack(side=tk.LEFT)
        self.thinning_entry = ttk.Entry(master, width=5, validate="key", validatecommand=(self.register(self._validate), "%P"))
        self.thinning_entry.insert(tk.END, '0')
        self.thinning_entry.pack(side=tk.LEFT, padx=(0, 5))

    def get_dt_span(self):
        return self.dt_span_entry.get()
    
    def get_thinning(self):
        return self.thinning_entry.get()

    def _validate(self, text):
        return text.isdigit()
