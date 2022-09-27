import time
from multiprocessing import Process, Queue

import cv2
from picamera.array import PiRGBArray
from picamera import PiCamera

import math
import socket
import pickle
import numpy as np


class CameraCapture:
    def __init__(self, FPS=15, OutputQueue=None):
        self.camera = None
        self.fps = FPS
        self.rawCapture = None
        self.outputQueue = OutputQueue
        
        self.CaputreProcess = None
        self.running = False

    def start(self):
        self.running = True
        self.CaputreProcess = Process(target=self.capturing, args=(self.fps, self.outputQueue))
        self.CaputreProcess.start()

    def stop(self):
        self.running = False
        time.sleep(0.5)

        while not self.outputQueue.empty():
            self.outputQueue.get()

        self.CaputreProcess.join()

    def capturing(self, FPS, mp_queue):
        camera = PiCamera()
        rawCapture = PiRGBArray(camera)
        camera.resolution = (1280, 720)
        camera.framerate = FPS
        time.sleep(0.1)

        while self.running:
            camera.capture(rawCapture, format="bgr")
            image = rawCapture.array

            if not mp_queue.full():
                mp_queue.put(image)
            
            time.sleep(1/FPS)


if __name__=='__main__':
    mp_queue = Queue(maxsize=100)
    cam = CameraCapture(OutputQueue=mp_queue)
    cam.start()
    max_length = 1048576
    host = "192.168.0.136"
    port = 5000
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    while True:
        try:
            if not mp_queue.empty():
                frame = mp_queue.get()
                retval, buffer = cv2.imencode(".jpg", frame)

                if retval:
                    buffer = buffer.tobytes()
                    buffer_size = len(buffer)

                    num_of_packs = 1
                    if buffer_size > max_length:
                        num_of_packs = math.ceil(buffer_size/max_length)

                    frame_info = {"packs":num_of_packs}
                    sock.sendto(pickle.dumps(frame_info), (host, port))
                    
                    left = 0
                    right = max_length

                    for i in range(num_of_packs):
                        data = buffer[left:right]
                        left = right
                        right += max_length
                        sock.sendto(data, (host, port))
        except KeyboardInterrupt:
            break
    time.sleep(0.5)
    cam.stop()
