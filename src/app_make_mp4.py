import os
import tkinter as tk
from tkinter import ttk

import pandas as pd
import cv2

from gui_parts import TempFile
import yolo_drawer
import mediapipe_drawer
from python_senpai import keypoints_proc


class App(ttk.Frame):
    def __init__(self, master, args):
        super().__init__(master)
        master.title("Make MP4")
        self.pack(padx=10, pady=10)

        proc_frame = ttk.Frame(self)
        proc_frame.pack(pady=5)
        # allのチェックボックス
        self.draw_all_chk_val = tk.BooleanVar()
        self.draw_all_chk_val.set(False)
        all_check = ttk.Checkbutton(proc_frame, text="draw all", variable=self.draw_all_chk_val)
        all_check.pack(side=tk.LEFT)

        self.member_combo = ttk.Combobox(proc_frame, state='readonly', width=12)
        self.member_combo.pack(side=tk.LEFT, padx=5)

        draw_btn = ttk.Button(proc_frame, text="Export", command=self.export)
        draw_btn.pack(side=tk.LEFT)

        plot_frame = ttk.Frame(self)
        plot_frame.pack(pady=5)

        self.out = cv2.VideoWriter()
        self.reload(args)

    def reload(self, args):
        self.src_df = args['src_df']
        self.cap = args['cap']
        self.src_attrs = args['src_attrs']
        self.time_min, self.time_max = args['time_span_msec']

        # UIの更新
        self.member_combo["values"] = self.src_df.index.get_level_values("member").unique().tolist()
        self.member_combo.current(0)

        if "roi_left_top" in self.src_attrs:
            zero_point = self.src_attrs['roi_left_top']
        else:
            zero_point = (0, 0)
        self.src_df = keypoints_proc.zero_point_to_nan(self.src_df, zero_point)
        print('reload() done.')

    def export(self):
        current_member = self.member_combo.get()

        # timestampの範囲を抽出
        tar_df = keypoints_proc.filter_by_timerange(self.src_df, self.time_min, self.time_max)
        # memberとkeypointのインデックス値を文字列に変換
        idx = tar_df.index
        tar_df.index = tar_df.index.set_levels([idx.levels[0], idx.levels[1].astype(str), idx.levels[2].astype(str)])

        if self.cap.isOpened() is True:
            fps = self.cap.get(cv2.CAP_PROP_FPS)
            self.cap.set(cv2.CAP_PROP_POS_MSEC, self.time_min)
        else:
            fps = 30

        tmp = TempFile()
        scale = tmp.get_mp4_setting()

        # VideoWriter
        file_name = os.path.splitext(self.src_attrs['video_name'])[0]
        if self.draw_all_chk_val.get() is True:
            suffix = "all"
        else:
            suffix = f"{current_member}"
        dst_dir = os.path.join(self.pkl_dir, os.pardir, 'mp4')
        os.makedirs(dst_dir, exist_ok=True)
        out_file_path = os.path.join(dst_dir, f'{file_name}_{suffix}.mp4')
        fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
        size = self.src_attrs['frame_size']
        size = (int(size[0] * scale), int(size[1] * scale))
        self.out.open(out_file_path, fourcc, fps, size, params=[cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY])

        if self.src_attrs['model'] == "YOLOv8 x-pose-p6":
            anno = yolo_drawer.Annotate()
        elif self.src_attrs['model'] == "MediaPipe Holistic":
            anno = mediapipe_drawer.Annotate()

        out_df = tar_df
        max_frame_num = out_df.index.unique(level='frame').max() + 1
        min_frame_num = out_df.index.unique(level='frame').min()
        out_indexes = out_df.sort_index().index
        frames = out_indexes.get_level_values('frame').unique()
        for i in range(min_frame_num, max_frame_num):
            frame = self.cap.read_anyway()
            frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
            anno.set_img(frame)
            if i in frames:
                frame_df = out_df.loc[pd.IndexSlice[i, :, :], :]
                indexes = frame_df.sort_index().index
                # draw_allなら全員の姿勢を描画
                if self.draw_all_chk_val.get() is True:
                    for member in indexes.get_level_values('member').unique():
                        dst_img = self._draw(out_df, i, member, indexes, anno, scale)
                # out_dfにi, current_memberの組み合わせがない場合はスキップ
                else:
                    dst_img = self._draw(out_df, i, current_member, indexes, anno, scale)
            else:
                dst_img = frame
            cv2.imshow("dst", dst_img)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('x'):
                break
            self.out.write(dst_img)
        cv2.destroyAllWindows()
        self.out.release()

    def _draw(self, out_df, frame_num, member, all_indexes, anno, scale):
        if (frame_num, member) not in all_indexes.droplevel(2):
            return anno.dst_img
        keypoints = out_df.loc[pd.IndexSlice[frame_num, member, :], :] * scale
        kps = keypoints.to_numpy()
        anno.set_pose(kps)
        anno.set_track(member)
        dst_img = anno.draw()
        return dst_img


def quit(root):
    root.quit()
    root.destroy()


def main():
    root = tk.Tk()
    app = App(root)
    root.protocol("WM_DELETE_WINDOW", lambda: quit(root))
    app.mainloop()


if __name__ == "__main__":
    main()
