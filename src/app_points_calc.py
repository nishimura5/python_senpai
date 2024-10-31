import os
import sys
import tkinter as tk
from tkinter import ttk

import pandas as pd

from behavior_senpai import df_attrs, file_inout, keypoints_proc
from gui_parts import CalcCaseEntry, IntEntry, TempFile
from gui_points_calc import Tree
from line_plotter import LinePlotter


class App(ttk.Frame):
    """Application for calculating vectors."""

    def __init__(self, master, args):
        super().__init__(master)
        master.title("Points Calculation")
        master.geometry("1200x700")
        self.pack(padx=10, pady=10)
        self.bind("<Map>", lambda event: self._load(event, args))

        temp = TempFile()
        width, height, dpi = temp.get_window_size()
        self.lineplot = LinePlotter(fig_size=(width / dpi, height / dpi), dpi=dpi)

        setting_frame = ttk.Frame(self)
        setting_frame.pack(fill=tk.X, expand=True)

        import_frame = ttk.Frame(setting_frame)
        import_frame.pack(padx=10, pady=5, expand=True, anchor=tk.W)
        import_btn = ttk.Button(import_frame, text="Import another feature file", command=self.import_feat)
        import_btn.pack()

        draw_frame = ttk.Frame(setting_frame)
        draw_frame.pack(padx=10, pady=5, expand=True, anchor=tk.W)
        add_btn = ttk.Button(draw_frame, text="Add calc", command=self.add_row)
        add_btn.pack(padx=(0, 60), side=tk.LEFT)

        self.calc_case_entry = CalcCaseEntry(draw_frame, temp.data["calc_case"])
        self.calc_case_entry.pack(side=tk.LEFT, padx=5)

        self.thinning_entry = IntEntry(draw_frame, label="Thinning:", default=temp.data["thinning"])
        self.thinning_entry.pack_horizontal(padx=5)

        draw_btn = ttk.Button(draw_frame, text="Draw", command=self.draw)
        draw_btn.pack(side=tk.LEFT)
        self.export_btn = ttk.Button(draw_frame, text="Export", command=self.export, state="disabled")
        self.export_btn.pack(side=tk.LEFT, padx=5)

        tree_canvas_frame = ttk.Frame(self)
        tree_canvas_frame.pack(padx=10, pady=5, fill=tk.X, expand=True)

        cols = [
            {"name": "calc", "width": 300},
            {"name": "member", "width": 200},
            {"name": "A", "width": 50},
            {"name": "B", "width": 50},
            {"name": "C", "width": 50},
        ]
        self.tree = Tree(tree_canvas_frame, cols, height=12)
        self.tree.pack(side=tk.LEFT)
        self.tree.add_menu("Edit", self.tree.edit_calc)
        self.tree.add_row_copy(column=1)
        self.tree.add_menu("Remove", self.tree.delete_selected)

        self.canvas = tk.Canvas(tree_canvas_frame, width=600)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        plot_frame = ttk.Frame(self)
        plot_frame.pack(pady=5)
        self.lineplot.pack(plot_frame)
        self.lineplot.set_single_ax(bottom=0.12)

        self.lineplot.set_img_canvas(self.canvas)

    def _load(self, event, args):
        src_df = args["src_df"].copy()
        self.calc_dir = os.path.join(os.path.dirname(args["pkl_dir"]), "calc")
        self.tar_df = src_df[~src_df.index.duplicated(keep="last")]

        idx = self.tar_df.index
        self.tar_df.index = self.tar_df.index.set_levels([idx.levels[0], idx.levels[1].astype(str), idx.levels[2].astype(int)])

        self.lineplot.set_trk_df(self.tar_df)
        self.lineplot.set_vcap(args["cap"])
        self.track_name = args["trk_pkl_name"]
        self.src_attrs = src_df.attrs

        # Update GUI
        self.tree.set_members(self.tar_df.index.levels[1].unique().tolist())
        self.tree.set_df(self.tar_df)

    def add_row(self):
        self.tree.add_calc()

    def import_feat(self):
        """Open a file dialog to select a feature file.
        Import the contents of the attrs.
        """
        calc_case = self.calc_case_entry.get_calc_case()
        pl = file_inout.PickleLoader(self.calc_dir, pkl_type="feature")
        pl.join_calc_case(calc_case)
        is_file_selected = pl.show_open_dialog()
        if is_file_selected is False:
            return
        in_trk_df = pl.load_pkl()
        in_trk_attrs = df_attrs.DfAttrs(in_trk_df)
        in_trk_attrs.load_proc_history()
        if in_trk_attrs.validate_model(self.src_attrs) is False:
            return
        if in_trk_attrs.validate_newest_history_proc("points") is False:
            return
        for row in in_trk_attrs.get_source_cols():
            row[1] = self.tree.get_members()[0]
            self.tree.insert(row)

    def draw(self):
        self.lineplot.clear()
        self.feat_df = pd.DataFrame()
        self.source_cols = self.tree.get_all()

        # thinning for plotting
        thinning = self.thinning_entry.get()
        self.thinning_entry.save_to_temp("thinning")
        members = list(set([str(x[1]) for x in self.source_cols]))
        for member in members:
            member_df = self.tar_df.loc[pd.IndexSlice[:, member], :].drop("timestamp", axis=1)
            member_feat_df = pd.DataFrame()

            for calc, m, point_a, point_b, point_c in self.source_cols:
                if member != str(m):
                    continue
                code = self.tree.get_name_and_code(calc)
                point_a, point_b = int(point_a), int(point_b)
                if code == "norm":
                    plot_df = keypoints_proc.calc_norm(member_df, point_a, point_b)
                elif code == "sin_cos":
                    plot_df = keypoints_proc.calc_sin_cos(member_df, point_a, point_b, int(point_c))
                elif code == "component":
                    plot_df = keypoints_proc.calc_xy_component(member_df, point_a, point_b)
                elif code == "cross":
                    plot_df = keypoints_proc.calc_cross_product(member_df, point_a, point_b, int(point_c))
                elif code == "dot":
                    plot_df = keypoints_proc.calc_dot_product(member_df, point_a, point_b, int(point_c))
                elif code == "plus":
                    plot_df = keypoints_proc.calc_plus(member_df, point_a, point_b, int(point_c))
                elif code == "norms":
                    plot_df = keypoints_proc.calc_norms(member_df, point_a, point_b, int(point_c))
                elif code == "direction":
                    plot_df = keypoints_proc.calc_direction(member_df, point_a, point_b)

                col_names = plot_df.columns.tolist()
                # concat right
                member_feat_df = pd.concat([member_feat_df, plot_df], axis=1)

                plot_df["timestamp"] = self.tar_df.loc[pd.IndexSlice[:, :, point_a], :].droplevel(2)["timestamp"]
                thinned_df = keypoints_proc.thinning(plot_df, thinning)
                self.lineplot.set_plot(thinned_df, member, col_names)
            # concat bottom
            self.feat_df = pd.concat([self.feat_df, member_feat_df], axis=0)

        self.lineplot.set_legend_of_plot()
        self.lineplot.draw()
        self.lineplot.set_members_to_draw(members)
        self.export_btn["state"] = "normal"

    def export(self):
        """Export the calculated data to a file."""
        if len(self.feat_df) == 0:
            print("No data to export.")
            return
        self.feat_df = self.feat_df.sort_index()
        members = self.feat_df.index.get_level_values(1).unique()
        file_name = os.path.splitext(self.track_name)[0]
        first_keypoint_id = self.tar_df.index.get_level_values(2).values[0]
        timestamp_df = self.tar_df.loc[pd.IndexSlice[:, members, first_keypoint_id], :].droplevel(2)["timestamp"]
        timestamp_df = timestamp_df[~timestamp_df.index.duplicated(keep="last")]
        self.feat_df = self.feat_df[~self.feat_df.index.duplicated(keep="last")]
        export_df = pd.concat([self.feat_df, timestamp_df], axis=1)
        export_df = export_df.dropna(how="all")
        export_df.attrs = self.src_attrs
        calc_case = self.calc_case_entry.get_calc_case()
        dst_path = os.path.join(self.calc_dir, calc_case, file_name + "_pts.feat.pkl")
        history_dict = df_attrs.make_history_dict("points", self.source_cols, {}, self.track_name)
        file_inout.save_pkl(dst_path, export_df, proc_history=history_dict)

    def _find_data_dir(self):
        if getattr(sys, "frozen", False):
            # The application is frozen
            datadir = os.path.dirname(sys.executable)
        else:
            # The application is not frozen
            # Change this bit to match where you store your data files:
            datadir = os.path.dirname(__file__)
        return datadir

    def close(self):
        self.lineplot.close()
