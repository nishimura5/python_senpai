import os

import cv2


class RoiCap(cv2.VideoCapture):
    def __init__(self, video_path):
        if os.path.exists(video_path) is False:
            raise FileNotFoundError(f"video_path:{video_path}")
        # cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY
        # を指定するとdecodeがGPUになる
        super().__init__(
            video_path,
            apiPreference=cv2.CAP_ANY,
            params=[cv2.CAP_PROP_HW_ACCELERATION, cv2.VIDEO_ACCELERATION_ANY])
 
        self.width = int(self.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.left_top_point = (0, 0)
        self.right_bottom_point = (self.width, self.height)
        self.roi_width = self.right_bottom_point[0] - self.left_top_point[0]
        self.roi_height = self.right_bottom_point[1] - self.left_top_point[1]

    def set_roi(self, left_top_point, right_bottom_point):
        self.left_top_point = left_top_point
        self.right_bottom_point = right_bottom_point
        self.roi_width = right_bottom_point[0] - left_top_point[0]
        self.roi_height = right_bottom_point[1] - left_top_point[1]

    def get_roi_frame(self):
        '''
        read()と互換
        '''
        ok, frame = self.read()
        if ok is True:
            frame = frame[self.left_top_point[1]:self.right_bottom_point[1], self.left_top_point[0]:self.right_bottom_point[0]]
        return ok, frame

    def click_roi(self):
        '''
        imshow()を使ったGUIでROIを指定
        '''
        ret, frame = self.read()
        src_img = frame.copy()
        cv2.namedWindow("frame", cv2.WINDOW_NORMAL)
        cv2.imshow("frame", src_img)
        cv2.setMouseCallback("frame", self.mouse_callback)

        left_top_circle_pos = (0, 0)
        right_bottom_circle_pos = (self.width, self.height)

        self.left_top_point = left_top_circle_pos
        self.right_bottom_point = right_bottom_circle_pos

        while True:
            cv2.imshow("frame", src_img)
            if self.left_top_point != left_top_circle_pos or self.right_bottom_point != right_bottom_circle_pos:
                src_img = frame.copy()
                cv2.rectangle(src_img, self.left_top_point, self.right_bottom_point, (0, 255, 0), 2)
                left_top_circle_pos = self.left_top_point
                right_bottom_circle_pos = self.right_bottom_point

            # xを押すとキャンセル、スペースを押すと確定
            key = cv2.waitKey(1) & 0xFF
            if key == ord('x'):
                self.left_top_point = (0, 0)
                self.right_bottom_point = (self.width, self.height)
                break
            if key == ord(' '):
                break
        cv2.destroyAllWindows()
        self.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.set_roi(self.left_top_point, self.right_bottom_point)

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.left_top_point = (x, y)
        if event == cv2.EVENT_RBUTTONDOWN:
            self.right_bottom_point = (x, y)