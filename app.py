from cgitb import text
from faulthandler import disable
from tkinter import * 
# from tkinter.ttk import *
from tkinter import messagebox

import cv2
import time
import PIL
from PIL import Image, ImageTk

from pc_run import *


class App:
    def __init__(self, window, window_title,pc_instance=None, fpsLimit = 30):

        self.window = window
        self.window.title(window_title)
        self.window.resizable(False, False)
        self.window.iconbitmap('.\\images\\raspberry_pi_icon.ico')
        self.window.geometry("950x650+500+100")

        self.PC_MAIN = pc_instance
        self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.open('images\\Video-Camera-Icon.jpg').resize((640, 480)))
        self.raspberry_ip = StringVar()
        self.ip_label = Label(self.window,
                        text="IP Address:",
                        font=("Helvetica", 25, 'bold'))

        self.ip_entry = Entry(self.window, width=18, background="blue", foreground="white", textvariable=self.raspberry_ip,  justify=CENTER, font = ('courier', 25, 'bold'))
        self.ip_entry.insert(END, '192.168.0.172')
        self.ip_entry.focus()
        
        self.connect_button = Button(self.window,
                                    text=" Connect  ",
                                    font=("Helvetica", 20, 'bold'),
                                    background="red",
                                    foreground="white",
                                    border=5,
                                    command=self.connectClicked)

        self.canvas = Canvas(window, width = 630, height = 430, highlightthickness=9, highlightbackground="blue")
        
        self.DistanceLabel = Label(self.window,
                                   text="Distance: 0 cm",
                                   font=("Helvetica", 18, 'bold'),
                                   bg="white")
        self.TemparatureLabel = Label(self.window,
                                      text="Temparature: 0 *C",
                                      font=("Helvetica", 18, 'bold'),
                                      bg="white")
        # self.LedLabel = Label(self.window,
        #                       text="Light: OFF",
        #                       font=("Helvetica", 18, 'bold'))
        self.MotorLabel = Label(self.window,
                                text="Motor: 0",
                                font=("Helvetica", 18, 'bold'))
        
        self.ip_label.grid(row=0, column=0, padx=70, pady=13)
        self.ip_entry.grid(row=0, column=1, columnspan=3)
        self.connect_button.grid(row=0, column=4, padx=30, pady=10)
        
        self.canvas.grid(row=1, column=0, columnspan=6, padx=100)
        
        self.DistanceLabel.grid(row=2, column=0, columnspan=2, pady=10)
        self.TemparatureLabel.grid(row=2, column=2, columnspan=2, pady=10)
        # self.LedLabel.grid(row=2, column=3, pady=10)
        self.MotorLabel.grid(row=2, column=4, columnspan=2, pady=10)

        self.delay = 1
        self.updateStatus()
        self.updateVideo()

        self.window.mainloop()
        
        # self.PC_MAIN.stop()

    def connectClicked(self):
        # messagebox.showinfo('information',str((self.raspberry_ip.get())))
        ip_address = str(self.ip_entry.get())
        if self.PC_MAIN.Socket.connected:
            self.PC_MAIN.Socket.disconnect()
        else:
            self.PC_MAIN.Socket.connect(ip_address)

    def updateStatus(self):
        # status = lambda x: "ON" if x else "OFF"
    
        if self.PC_MAIN.Socket.connected:
            self.connect_button.configure(text="Disconnect", background='red')
            self.canvas.configure(highlightbackground='green')

            self.DistanceLabel.configure(text = "Distance: {:0.2f}cm".format(self.PC_MAIN.STATUS['DISTANCE']))
            if self.PC_MAIN.STATUS['DISTANCE'] >= 100:
                self.DistanceLabel.configure(bg="white")
            elif self.PC_MAIN.STATUS['DISTANCE'] < 50:
                self.DistanceLabel.configure(bg="red")
            elif self.PC_MAIN.STATUS['DISTANCE'] < 100:
                self.DistanceLabel.configure(bg="yellow")
            
            self.TemparatureLabel.configure(text = "Temparature: {:} *C".format(self.PC_MAIN.STATUS['TEMP']))
            if self.PC_MAIN.STATUS['TEMP'] >= 100:
                self.TemparatureLabel.configure(bg="red")
            else:
                self.TemparatureLabel.configure(bg="white")

            self.MotorLabel.configure(text = "Motor: {:}".format(self.PC_MAIN.STATUS['ANGLE']))
        else:
            self.connect_button.configure(text="Connect", background='green')
            self.canvas.configure(highlightbackground='red')
        
        self.window.after(self.delay, self.updateStatus)

    def updateVideo(self):
        # try:
        if self.PC_MAIN.Socket.connected:
            if not self.PC_MAIN.resultQueue.empty():
                img = PIL.Image.fromarray(self.PC_MAIN.resultQueue.get()).resize((640, 480))
                self.photo = PIL.ImageTk.PhotoImage(image=img)
            # else:
            #     if not self.PC_MAIN.inputQueue.empty():
            #         self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.fromarray(self.PC_MAIN.inputQueue.get()).resize((630, 480)))
        else:
            self.photo = PIL.ImageTk.PhotoImage(image = PIL.Image.open('images\\Video-Camera-Icon.jpg').resize((630, 480)))
        
        self.canvas.create_image(0, 0, image = self.photo, anchor = NW)
        self.window.after(self.delay, self.updateVideo)


if __name__=='__main__':
    pc = PC_Main()
    pc.start()
    App(Tk(), "Raspberry Application",pc ,10)
    # pc.stop() 