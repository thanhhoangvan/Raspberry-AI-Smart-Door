#!/usr/bin/python3
import os
clear = lambda: os.system('clear')
import time
from utils.Socket import SocketRaspberry
from utils.GPIO import GPIO_Controler

# Config PINs
ledPIN1 = 26 # Pin of distance light
ledPIN2 = 19 # Pin of temparature light
servoPIN = 20 # Data pin of Servo

distanceConfig = {
    'trig': 25,
    'echo':    24,
}

max6676Config = {
    'SO':   22, # Data pin
    'SCK':   17, # Clock pin
    'SC':   27, # Chip Select
    'Units': 1, # 1-C, 2-F
}

D1_Threshold = 100 # 1m = 100cm
D2_Threshold = 50 # 0.5m = 50cm
TEMP_Threshold = 100 # warning temparature
CLOSE_ANGLE = 0
OPEN_ANGLE = 180

objects_accept = ['person', 'bicycle', 'car', 'motorbike', 'bus', 'truck', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe']
def checkObj(listObjs=[]):
    for obj in listObjs:
        if obj in objects_accept:
            return True
    return False

class Rasp_Main:
    def __init__(self):
        # self.Rasp_IP = "192.168.0.172"
        # self.PC_IP = "192.168.0.136"
        self.gpio =  GPIO_Controler(hcsr04PINs = distanceConfig,
                                    max6676PINs = max6676Config,
                                    ledPIN = [ledPIN1, ledPIN2],
                                    servoPIN = servoPIN)
        self.Socket = SocketRaspberry()

        self.flag_time = time.time()

    def start(self):
        self.gpio.start()
        self.Socket.start()
    
    # def show(self):
    #     print("Object:", self.Socket.CurrentObjectDetection)
    #     print("DISTANCE: {} - TEMP: {} - ANGLE: {}".format(self.gpio.DISTANCE.value, self.gpio.TEMPARATURE.value, self.gpio.ANGLE.value))

    def control(self):
        # time.sleep(10)
        try:
            while True:
                self.Socket.status = self.gpio.getStatus()
                light1 = 0
                light2 = 1

                if self.gpio.TEMPARATURE.value >= TEMP_Threshold:
                    light1 = 1
                    light2 = 0
                else:
                    light1 = 0
                    light2 = 1

                if checkObj(self.Socket.CurrentObjectDetection):
                    # if (self.gpio.DISTANCE.value >= 100):
                        # pass
                    if (D2_Threshold < self.gpio.DISTANCE.value < D1_Threshold):
                        light1 = 1
                    elif (self.gpio.DISTANCE.value <= D2_Threshold):
                        if not light1:
                            light1 = 0
                        if light2:
                            light2 = 0
                        
                        self.flag_time = time.time()
                        if self.gpio.ANGLE.value == CLOSE_ANGLE:
                            self.gpio.ANGLE.value = OPEN_ANGLE
                
                    
                self.gpio.ledStatus1.value = light1
                self.gpio.ledStatus2.value = light2
                if time.time() - self.flag_time > 3 and self.gpio.ANGLE.value == OPEN_ANGLE:
                    self.gpio.ANGLE.value = CLOSE_ANGLE
                
                # self.show()
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            pass

    def stop(self):
        self.gpio.stop()
        self.Socket.stop()


if __name__=='__main__':
    rsp = Rasp_Main()
    rsp.start()
    rsp.control()
    rsp.stop()
