import os
import time
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
from threading import Thread
from multiprocessing import Queue, Process, Lock, Value

import cv2
import numpy as np
import tensorflow as tf

from yolov3_tf2.models import YoloV3
from yolov3_tf2.utils import draw_outputs
from yolov3_tf2.dataset import transform_images

from utils.Socket import SocketPC


num_classes=80
clear = lambda: os.system('cls')


class YOLO:
    def __init__(self, inputQueue, outputQueue, outputQueue2):
        physical_devices = tf.config.experimental.list_physical_devices('GPU')
        
        for physical_device in physical_devices:
            tf.config.experimental.set_memory_growth(physical_device, True)
        
        self.Model = None
        self.class_names = None
        self.inputQueue = inputQueue
        self.outputQueue = outputQueue
        self.outputQueue2 = outputQueue2
        
        self.running = True
        self.yoloProcess = Process(target=self.predicting, args=(self.inputQueue, self.outputQueue, self.outputQueue2, self.running))
        self.yoloProcess.start()


    def stop(self):
        self.running = False
        time.sleep(0.5)
        
        while not self.inputQueue.empty():
            try:
                self.inputQueue.get()
            except:
                pass

        while not self.outputQueue.empty():
            try:
                self.outputQueue.get()
            except:
                pass
        self.yoloProcess.join()

    def predicting(self, inputQueue, outputQueue, outputQueue2, mp_running):
        print('init model')
        self.Model = YoloV3(classes=80)
        print('loading weights')
        self.Model.load_weights(f'.\checkpoints\yolov3.tf')
        print('model created')
        self.class_names = [c.strip() for c in open(f'.\data\coco.names').readlines()]

        while mp_running:
            if not inputQueue.empty():
                img = inputQueue.get()
                
                if not outputQueue2.full():
                    outputQueue2.put(img)

                input_image = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                input_image = tf.expand_dims(input_image, 0)
                input_image = transform_images(input_image, 416)

                boxes, scores, classes, nums = self.Model.predict(input_image, verbose=0)

                # img = draw_outputs(img, (boxes, scores, classes, nums), self.class_names)
                listObjects = [self.class_names[i] for i in np.unique(np.array(classes[0]))]

                if not outputQueue.full():
                    outputQueue.put({"objects": listObjects,
                                     "boxes": boxes,
                                     "scores": scores,
                                     "classes": classes,
                                     "nums": nums,
                                     "class_names": self.class_names})
        status.value = 0

class PC_Main:
    def __init__(self):
        # self.Raps_IP = ""
        # self.PC_IP = socket.gethostbyname(socket.gethostname())
        self.Rasp_PORT = 5000

        self.STATUS = {'DISTANCE': 0.0, 'TEMP': 0, 'ANGLE': 0}
    
        self.inputQueue = Queue(maxsize=10000)
        self.outputQueue = Queue(maxsize=10000)
        self.outputQueue2 = Queue(maxsize=10000)
        self.resultQueue = Queue(maxsize=10000)
        self.listObj = []

        self.Model = None
        self.menuThread = None
        self.camViewThread = None
        self.Socket = None
        self.running = False

    def start(self):
        if self.running:
            print("It still running!")
        else:
            # self.Raps_IP = input("Input the Raspberry's IP Address: ")
            # self.Raps_IP = ip_address
            self.Socket = SocketPC(self.inputQueue)
            self.running = True
            self.Socket.start()

            self.Model = YOLO(self.inputQueue, self.outputQueue, self.outputQueue2)
            
            self.camViewThread = Thread(target=self.camView, args=(self.inputQueue, self.outputQueue, self.outputQueue2, self.resultQueue), daemon=True)
            self.camViewThread.start()

            # self.menuThread = Thread(target=self.menu, daemon=True)
            # self.menuThread.start()

    def stop(self):
        self.running = False
        time.sleep(0.2)
        self.Model.stop()
        self.model_status = False
        self.Socket.stop()
        # self.menuThread.join()
        self.camViewThread.join()

    def camView(self, input_queue, output_queue, output_queue2, result_queue):
        print("Camera processing runing")
        result = {}
        img = None
        image_result = None
        flag_time = time.time()
        while self.running:
            self.STATUS = self.Socket.status
            self.Socket.CurrentObjects = self.listObj

            if time.time() - flag_time > 2.5:
                result = {} 
            
            if not output_queue2.empty():
                img = output_queue2.get()

            if not output_queue.empty():
                flag_time = time.time()
                result = output_queue.get()
                self.listObj = result['objects']

            if len(result) > 0 and img is not None:
                image_result = draw_outputs(img, (result['boxes'], result['scores'], result['classes'], result['nums']), result['class_names'])
            else:
                image_result = img
            
            if not result_queue.full() and image_result is not None:
                result_queue.put(image_result)
                time.sleep(1/30)

        while not result_queue.empty():
            result_queue.get()

if __name__=='__main__':
    # main = PC_Main()
    # main.start()
    # try:
    #     while main.running:
    #         time.sleep(10)
    # except KeyboardInterrupt:
    #     main.stop()
    pass