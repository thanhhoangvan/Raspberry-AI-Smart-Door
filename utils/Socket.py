import io
from pydoc import cli
import sys
import json
import time
import struct
import socket
from threading import Thread
from cv2 import add

import numpy as np
import cv2

if sys.platform == 'linux':
    from picamera.array import PiRGBArray
    from picamera import PiCamera


PORT = {
    'status': 5000,
    'video': 5050,
}


class SocketRaspberry:
    def __init__(self):
        self.RASP_IP = "0.0.0.0"
        self.PC_IP = "192.168.0.136"
        self.statusPORT = 5555
        self.videoPORT = 9999
        
        self.connected = False
        self.videoConnected = False
        self.running = False
        self.status = {'DISTANCE': 0.0, 'TEMP': 0.0, 'ANGLE': 0.0, 'LIGHT_1': 0, 'LIGHT_2': 0}
        self.CurrentObjectDetection = []
        self.SocketProcess = None

        self.statusSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.videoSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.syncStatusThread    = Thread(target=self.syncStatus, daemon=True)
        self.StreamThread        = Thread(target=self.sendVideoStream, daemon=True)

    def start(self):
        print("Start Raspberry Socket")
        self.running = True
        # self.statusSocket.bind((self.RASP_IP, self.statusPORT))
        # self.statusSocket.listen(1)
        
        self.StreamThread.start()
        self.syncStatusThread.start()
    
    def stop(self):
        self.connected = False
        self.running = False
        time.sleep(1)

        self.syncStatusThread.join()
        self.statusSocket.close()
        
        self.StreamThread.join()
        self.videoSocket.close()

    def sendVideoStream(self):
        client_socket = socket.socket()

        camera = PiCamera()
        camera.vflip = True
        camera.resolution = (1280, 720)
        camera.framerate = 30
        camera.start_preview()
        time.sleep(2)
        print("Camera started")
        while self.running:
            if not self.connected:
                if self.videoConnected:
                    client_socket.close()
                    self.videoSocket.close()
                time.sleep(0.1)
                continue
            if not self.videoConnected:
                print("Try start video socket")
                try:
                    client_socket = socket.socket()
                    client_socket.connect((self.PC_IP, self.videoPORT))
                    connection = client_socket.makefile('wb')
                    print('Connected stream socket')
                    
                    self.videoConnected = True
                    print("Video socket started")
                except:
                    time.sleep(0.5)
                    continue

            try:
                stream = io.BytesIO()
                for foo in camera.capture_continuous(stream, 'jpeg'):
                    if not self.running:
                        break
                    
                    connection.write(struct.pack('<L', stream.tell()))
                    connection.flush()
                    stream.seek(0)
                    connection.write(stream.read())
                    stream.seek(0)
                    stream.truncate()
                
                connection.write(struct.pack('<L', 0))

            except socket.error:
                print("Video Stream socket error, disconnected and closed!")
                self.videoConnected = False
                client_socket.close()
                # connection.close()
                # self.videoSocket.close()
        
        camera.stop_preview()
        camera.close()

    def syncStatus(self):
        while self.running:
            if not self.connected:
                try:
                    self.statusSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.statusSocket.bind((self.RASP_IP, self.statusPORT))
                    self.statusSocket.listen(1)
                    
                    print("Waiting for connect...")
                    clientsocket, address = self.statusSocket.accept()
                    self.PC_IP = address[0]
                    print("Connect to", address)
                    self.connected = True
                finally:
                    time.sleep(0.5)
                continue

            try:
                clientsocket.send( bytes(json.dumps(self.status), "UTF-8"))
            
                self.CurrentObjectDetection = json.loads(clientsocket.recv(1024).decode( "UTF-8" ))
                # print(self.CurrentObjectDetection)
            except socket.error:
                print("Disconnected to SyncStatus Socket")
                self.connected = False
                clientsocket.close()
                self.statusSocket.close()
        
            time.sleep(0.1) 
        clientsocket.close()


class SocketPC:
    def __init__(self, mpQueue=None):
        self.RASP_IP = ""
        self.PC_IP = self.getMyIP()
        self.statusPORT = 5555
        self.videoPORT = 9999
        
        self.connected = False
        self.videoConnected = False
        self.videoQueue = mpQueue
        self.VideoConnection = None
        self.status = {'DISTANCE': 0.0, 'TEMP': 0.0, 'ANGLE': 0.0, 'LIGHT_1': 0, 'LIGHT_2': 0}
        self.CurrentObjects = []

        self.statusSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.videoSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # self.videoSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.receiveStatusThread = Thread(target=self.receiveStatus, daemon=True)
        self.receiveCameraThread = Thread(target=self.receiveVideoStream, args=((self.videoQueue,)), daemon=True)
        self.running = False

    def start(self):
        self.running = True
        self.connected = False

        self.receiveStatusThread.start()
        self.receiveCameraThread.start()
        print("All thread started")

    def connect(self, rasp_ip=""):
        print("Connecting to", rasp_ip)
        self.connected = False
        self.RASP_IP = rasp_ip
        self.running = True

        print("Waiting for connect socket...")
        self.statusSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.statusSocket.connect((self.RASP_IP, self.statusPORT))
        print("Connected to", rasp_ip)

        self.connected = True

    def disconnect(self):
        self.connected = False
        self.statusSocket.close()
        self.videoSocket.close()
        print("Disconnected")

    def getMyIP(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        myIP = s.getsockname()[0]
        s.close()
        return myIP
    
    def stop(self):
        self.running = False
        self.disconnect()
        time.sleep(1)

        self.receiveStatusThread.join()
        self.receiveCameraThread.join()

    def receiveVideoStream(self, mp_queue):
        while self.running:
            if not self.connected:
                time.sleep(0.5)
                continue
            
            if not self.videoConnected:
                try:
                    self.videoSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.videoSocket.bind((self.PC_IP, self.videoPORT))
                    self.videoSocket.listen(0)
                    print(("Try to connect video Socket..."))
                    connect, address = self.videoSocket.accept()
                    self.VideoConnection = connect.makefile('rb')
                    print('Connected receive stream video socket at IP:', address[0])
                    
                    self.videoConnected = True
                except:
                    continue
            
            img = None
            while True:
                if not self.running or not self.connected:
                    time.sleep(0.1)
                    self.videoSocket.close()
                    connect.close()
                    print("Stop receive frame captured")
                    break

                try:
                    data = self.VideoConnection.read(struct.calcsize('<L'))
                except:
                    self.videoConnected = False
                    connect.close()
                    self.videoSocket.close()
                    print("Error when try to receive frame captured")
                    break
                    
                image_len = struct.unpack('<L', data)[0]
                if not image_len:
                    continue
                image_stream = io.BytesIO()
                image_stream.write(self.VideoConnection.read(image_len))
                image_stream.seek(0)

                file_bytes = np.asarray(bytearray(image_stream.read()), dtype=np.uint8)
                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                if not mp_queue.full():
                    mp_queue.put(img)

    def receiveStatus(self):
        while self.running:
            if not self.connected:
                time.sleep(0.5)
                continue

            try:  
                self.status = json.loads(self.statusSocket.recv( 1024 ).decode( "UTF-8" ))
                self.statusSocket.send( bytes(json.dumps(self.CurrentObjects), "UTF-8" ) )  
                # print("send ", self.CurrentObjects)                
            except socket.error: 
                self.connected = False  
                

if __name__=='__main__':
    pass