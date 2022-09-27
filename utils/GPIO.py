import time
import pigpio
from threading import Thread
from multiprocessing import Process, Value, Queue, Lock

import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)


class ServoControl:
    def __init__(self, servoPIN):
        self.servo_pin = servoPIN
        
        print("Initialized servo connect on GPIO {} pin".format(self.servo_pin))
        self.pwm = pigpio.pi() 
        self.pwm.set_mode(self.servo_pin, pigpio.OUTPUT)
        self.pwm.set_PWM_frequency(self.servo_pin, 50)

    def setAngle(self, angle):
        duty = int(angle*2000/180) + 500

        self.pwm.set_servo_pulsewidth(self.servo_pin, duty)
        time.sleep(1)

    def release(self):
        self.pwm.set_PWM_dutycycle(self.servo_pin, 0)
        self.pwm.set_PWM_frequency(self.servo_pin, 0)


class Thermocouple:
    def __init__(self, sc, sck, so, unit):
        self.sc = sc
        self.sck= sck
        self.so = so
        self.unit = unit # 0-raw, 1-C, 2-F
        
        GPIO.setup(self.sc, GPIO.OUT, initial = GPIO.HIGH)
        GPIO.setup(self.sck, GPIO.OUT, initial = GPIO.LOW)
        GPIO.setup(self.so, GPIO.IN)

    def read_temp(self):
        GPIO.output(self.sc, GPIO.LOW)
        time.sleep(0.002)
        GPIO.output(self.sc, GPIO.HIGH)
        time.sleep(0.22)

        GPIO.output(self.sc, GPIO.LOW)
        GPIO.output(self.sck, GPIO.HIGH)
        time.sleep(0.001)
        GPIO.output(self.sck, GPIO.LOW)
        Value = 0
        for i in range(11, -1, -1):
            GPIO.output(self.sck, GPIO.HIGH)
            Value = Value + (GPIO.input(self.so) * (2 ** i))
            GPIO.output(self.sck, GPIO.LOW)

        GPIO.output(self.sck, GPIO.HIGH)
        error_tc = GPIO.input(self.so)
        GPIO.output(self.sck, GPIO.LOW)

        for i in range(2):
            GPIO.output(self.sck, GPIO.HIGH)
            time.sleep(0.001)
            GPIO.output(self.sck, GPIO.LOW)

        GPIO.output(self.sc, GPIO.HIGH)

        if self.unit == 0:
            temp = Value
        if self.unit == 1:
            temp = Value * 0.25
        if self.unit == 2:
            temp = Value * 0.25 * 9.0 / 5.0 + 32.0

        if error_tc != 0:
            return -self.sc
        else:
            return temp


class DistanceSensor:
    def __init__(self, trigger, echo):
        self.PIN_TRIGGER = trigger
        self.PIN_ECHO = echo

        GPIO.setup(self.PIN_TRIGGER, GPIO.OUT)
        GPIO.setup(self.PIN_ECHO, GPIO.IN)
        GPIO.output(self.PIN_TRIGGER, GPIO.LOW)
        time.sleep(0.5)

    def readDistance(self):
        while True:
            GPIO.output(self.PIN_TRIGGER, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(self.PIN_TRIGGER, GPIO.LOW)
            
            distance = 150 # default max
            try:
                start_time = time.time()
                while GPIO.input(self.PIN_ECHO)==0:
                        pulse_start_time = time.time()
                        if time.time() - start_time > 0.01:
                            raise Exception('Error when calcualting distance')
                while GPIO.input(self.PIN_ECHO)==1:
                        pulse_end_time = time.time()
                        if time.time() - start_time > 0.01:
                            raise Exception('Error when calcualting distance')

                pulse_duration = pulse_end_time - pulse_start_time
                distance = round(pulse_duration * 17150, 2)
                time.sleep(0.001)
            except:
                pass
            return distance


class LED:
    def __init__(self, ledPIN) -> None:
        self.LED_PIN = ledPIN
        GPIO.setup(self.LED_PIN, GPIO.OUT)
    
    def turnOn(self):
        GPIO.output(self.LED_PIN, GPIO.HIGH)
    
    def turnOff(self):
        GPIO.output(self.LED_PIN, GPIO.LOW)


class GPIO_Controler:
    def __init__(self, hcsr04PINs={'trig':0, 'echo':0}, max6676PINs={}, ledPIN=[], servoPIN=None):
        self.Distance = DistanceSensor(trigger=hcsr04PINs['trig'],echo=hcsr04PINs['echo'])
        self.TempatureSensor = Thermocouple(max6676PINs['SC'],
                                            max6676PINs['SCK'],
                                            max6676PINs['SO'],
                                            max6676PINs['Units'])
        self.LED1 = LED(ledPIN[0])
        self.LED2 = LED(ledPIN[1])
        
        self.Servo = ServoControl(servoPIN)

        self.CotrolerProcess = None
        self.running = False

        self.TEMPARATURE = Value("i", 0)
        self.ANGLE = Value("i", 0)
        self.ledStatus1 = Value("i", 0)
        self.ledStatus2 = Value("i", 0)
        self.DISTANCE = Value("d", 0)

    def start(self):
        self.running = True
        self.CotrolerProcess = Process(target=self.controling,
                                       args=(self.running,
                                             self.TempatureSensor,
                                             self.Distance,
                                             self.Servo,
                                             self.LED1,
                                             self.LED2,
                                             self.TEMPARATURE,
                                             self.DISTANCE,
                                             self.ledStatus1,
                                             self.ledStatus2,
                                             self.ANGLE),
                                       daemon=True)
        self.CotrolerProcess.start()
        print("All GPIO Deviecs Started")

    def stop(self):
        self.running = False
        self.CotrolerProcess.join()
        self.Servo.release()
        GPIO.cleanup()
        print("All GPIO Deviecs Stopped")

    def getStatus(self):
        return {
                'DISTANCE' : self.DISTANCE.value,
                'TEMP' :     self.TEMPARATURE.value,
                'ANGLE' :    self.ANGLE.value,
                'LIGHT_1' :    self.ledStatus1.value,
                'LIGHT_2' :    self.ledStatus2.value,
            }

    def controling(self, mp_running, TempatureSensor, Distance, Servo, LED1, LED2, TEMPARATURE, DISTANCE, ledStatus1, LedStatus2, ANGLE):
        oldAngle = ANGLE.value
        oldLed1 = ledStatus1.value
        oldLed2 = LedStatus2.value

        while mp_running:
            if oldAngle != ANGLE.value:
                oldAngle = ANGLE.value
                Servo.setAngle(ANGLE.value)

            if oldLed1 != ledStatus1.value:
                oldLed1 = ledStatus1.value
                if ledStatus1.value == 0:
                    LED1.turnOff()
                else:
                    LED1.turnOn()
            
            if oldLed2 != LedStatus2.value:
                oldLed2 = LedStatus2.value
                if LedStatus2.value == 0:
                    LED2.turnOff()
                else:
                    LED2.turnOn()

            DISTANCE.value = Distance.readDistance()

            TEMPARATURE.value = int(TempatureSensor.read_temp())

            time.sleep(0.01)


if __name__=='__main__':
    # distanceConfig = {'trig': 25, 'echo': 24}
    # ledPIN1 = 13 # Pin of warning light
    # ledPIN2 = 1 # Pin of warning light
    # servoPIN = 20 # Data pin of Servo
    # max6676Config = {
    #     'SO':   22, # Data pin
    #     'SCK':   17, # Clock pin
    #     'SC':   27, # Chip Select
    #     'Units': 1, # 1-C, 2-F
    # }

    # gpio = GPIO_Controler(hcsr04PINs = distanceConfig,
    #                       max6676PINs = max6676Config,
    #                       ledPIN = [ledPIN1, ledPIN2],
    #                       servoPIN = servoPIN)
    # gpio.start()
    # time.sleep(2)
    
    # try:
    #     while True:
    #         print("| Distance: {:10.2f} | Temp: {:10} | Light: {:10} | Angle: {:10} |".format(gpio.DISTANCE.value, gpio.TEMPARATURE.value, gpio.ledStatus.value, gpio.ANGLE.value))
    #         if gpio.ledStatus.value == 1:
    #             gpio.ledStatus.value = 0
    #         else:
    #             gpio.ledStatus.value = 1
    #         if gpio.ANGLE.value == 0:
    #             gpio.ANGLE.value = 180
    #         else:
    #             gpio.ANGLE.value = 0
    #         time.sleep(3)
    # except KeyboardInterrupt:
    #     gpio.stop()
    pass