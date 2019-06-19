# coding=utf-8
'''
:func 获取屏幕截图并提交到远程服务器.由远程服务器将图片序列保存为视频
:author: MrLi
:date: 

'''
import sys
import os
import codecs
import json

import numpy as np
import time
import matplotlib.pyplot as plt
import cv2
import traceback
import threading
import requests
import base64
import pickle

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from concurrent import futures

import os, win32gui, win32ui, win32con, win32api
import re
screenshot_lock = threading.Lock()
root_ = 'F:\\datacenter\\prac_screen'


class ScreenShot_Fast(object):
    def __init__(self, hwnd):
        self.hwnd = hwnd
    
    def __enter__(self):
        hwnd = self.hwnd
        self.wdc = win32gui.GetWindowDC(0)
        self.dcobj = win32ui.CreateDCFromHandle(self.wdc)
        # 截取全屏
        MoniterDev = win32api.EnumDisplayMonitors()
        MoniterDev = MoniterDev[0][2]
        x_glob, y_glob, w_glob, h_glob = MoniterDev[0] + 1, MoniterDev[1] + 1, MoniterDev[2] - 1, MoniterDev[3] - 1
        
        # 截取指定hwnd窗口
        if hwnd != 0:
            MoniterDev = win32gui.GetWindowRect(hwnd)
        # print(MoniterDev)
        x, y, w, h = MoniterDev[0] + 1, MoniterDev[1] + 1, MoniterDev[2] - 1, MoniterDev[3] - 1
        
        self.x_glob = x_glob
        self.y_glob = y_glob
        self.w_glob = w_glob
        self.h_glob = h_glob
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.cdc = self.dcobj.CreateCompatibleDC()
        self.dataBitMap = win32ui.CreateBitmap()
        self.dataBitMap.CreateCompatibleBitmap(self.dcobj, self.w_glob, self.h_glob)
        self.cdc.SelectObject(self.dataBitMap)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.dcobj.DeleteDC()
        self.cdc.DeleteDC()
        win32gui.DeleteObject(self.dataBitMap.GetHandle())
        win32gui.ReleaseDC(self.hwnd, self.wdc)
    
    def process(self, i):
        """
        从设备中拷贝图片并导出
        :return:
        """
        screenshot_lock.acquire()
        self.cdc.BitBlt((self.x_glob, self.y_glob), (self.w_glob, self.h_glob), self.dcobj, (0, 0),
                        win32con.SRCCOPY)
        im = self.dataBitMap.GetBitmapBits(True)
        screenshot_lock.release()
        # print(i)
        return im, i
    
    def coverfrom(self, im, _cursor, i):
        """
        根据内存中的bitmap读取,转为numpy的array结构
        :param im:
        :return:
        """

        img = np.fromstring(im, dtype=np.uint8).reshape(self.h_glob, self.w_glob, 4)
        img = img[self.y:self.y + self.h, self.x:self.x + self.w, :]
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
        x, y = win32api.GetCursorPos()
        h, w, _ = _cursor.shape
        if y + h >= self.h:
            h = self.h - y - 1
        if x + w >= self.w:
            w = self.w - x - 1
        try:
            cursor = _cursor[:h, :w]
            img[y:y + h, x:x + w] = img[y:y + h, x:x + w] + cursor / 2
        except Exception as e:
            pass
            # print(e)
        cv2.imwrite('/'.join([root_, name, '{i}.jpg'.format(i=i)]), img)
        # print(i)


def take_screenshot_fast(hwnd):
    wdc = win32gui.GetWindowDC(0)
    dcobj = win32ui.CreateDCFromHandle(wdc)
    cdc = dcobj.CreateCompatibleDC()
    dataBitMap = win32ui.CreateBitmap()
    # 截取全屏
    MoniterDev = win32api.EnumDisplayMonitors()
    MoniterDev = MoniterDev[0][2]
    x_glob, y_glob, w_glob, h_glob = MoniterDev[0] + 1, MoniterDev[1] + 1, MoniterDev[2] - 1, MoniterDev[3] - 1
    
    # 截取指定hwnd窗口
    if hwnd != 0:
        MoniterDev = win32gui.GetWindowRect(hwnd)
    # print(MoniterDev)
    x, y, w, h = MoniterDev[0] + 1, MoniterDev[1] + 1, MoniterDev[2] - 1, MoniterDev[3] - 1
    
    dataBitMap.CreateCompatibleBitmap(dcobj, w_glob, h_glob)
    cdc.SelectObject(dataBitMap)
    cdc.BitBlt((x_glob, y_glob), (w_glob, h_glob), dcobj, (0, 0),
               win32con.SRCCOPY)
    
    im = dataBitMap.GetBitmapBits(True)
    
    img = np.fromstring(im, dtype=np.uint8).reshape(h_glob, w_glob, 4)
    img = img[y:y + h, x:x + w, :]
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    # cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    dcobj.DeleteDC()
    cdc.DeleteDC()
    win32gui.ReleaseDC(hwnd, wdc)
    win32gui.DeleteObject(dataBitMap.GetHandle())
    return img, (x, y, w, h)


def main(max_count, fps, name='default', is_screenshot=True, is_covertvideo=True):
    _cursor = cv2.imread('cursor.png', cv2.IMREAD_COLOR)
    _cursor = np.array(_cursor)
    if not os.path.exists('/'.join([root_, name])):
        os.mkdir('/'.join([root_, name]))
    with ScreenShot_Fast(0) as screenshot:
        if is_screenshot:
            print('开始截取屏幕.....预计用时: ', max_count/30, 's')
            b = time.time()
            with futures.ThreadPoolExecutor(max_workers=5) as executor:
    
                for i in range(max_count):
                    im, i = screenshot.process(i)
                    executor.submit(screenshot.coverfrom, im, _cursor, i)
            print('完成屏幕截取.....实际用时: ', time.time()-b, 's')
            
        if is_covertvideo:
            print('开始生产视频')
            b = time.time()
            video_outstream = cv2.VideoWriter('/'.join([root_, '{name}.mp4'.format(name=name)]),
                                              cv2.VideoWriter_fourcc(*'mp4v'),
                                              fps,
                                              (screenshot.w, screenshot.h))
            filelist = sorted(os.listdir('/'.join([root_, name])),
                              key=lambda item: int(re.findall('\d+', item)[0]))
            for f in filelist:
                img = cv2.imread('/'.join([root_, name, f]))
                img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
                video_outstream.write(img)
                # print(f)
            # def loadimg(path, i):
            #     return cv2.imread(path), i
            # temp_img = dict()
            # with futures.ThreadPoolExecutor(max_workers=40) as exe:
            #     future_items = [exe.submit(loadimg, '/'.join([name, f]), i)
            #                     for i, f in enumerate(filelist)]
            #     for j, f in enumerate(futures.as_completed(future_items)):
            #         try:
            #             img, i = f.result()
            #             temp_img[i] = img
            #             print(i)
            #         except Exception as e:
            #             pass
            # for i, img in temp_img.items():
            #     video_outstream.write(img)
            video_outstream.release()
            print('视频生成完成...', time.time()-b, 's')
    print('finish')


if __name__ == '__main__':
    print(sys.argv)
    if len(sys.argv) < 5:
        print('参数不够')
    
    max_count = int(sys.argv[1])  # 18000
    fps = int(sys.argv[2])  # 30
    name = sys.argv[3]  # 'test'
    is_screenshot = sys.argv[4] == 'True'  # True
    is_covertvideo = sys.argv[5] == 'True'  # True
    b = time.time()
    main(max_count=max_count,
         fps=fps,name=name,
         is_screenshot=is_screenshot,
         is_covertvideo=is_covertvideo)
    print('time spend: ', time.time()-b)
