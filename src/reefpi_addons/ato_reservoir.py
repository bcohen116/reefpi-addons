"""
    Automation script to handle conditional sensor readings.
    Will send an API request to run a macro that will
    send email alert and disable the pump until user refills the water reservoir
"""
import time
import json
import os
import requests
from loguru import logger
from datetime import datetime
import RPi.GPIO as GPIO

RESERVOIR_ATO_PIN = 23

# setup using the reef pi interface, ID grabbed manually through API requests
DISABLE_ATO_MACRO_ID = 2
ENABLE_ATO_MACRO_ID = 3
WATER_CHANGE_ID = 3


class ATO:
    def _login(self):
        session = requests.Session()
        session.post("http://localhost/auth/signin", data=json.dumps({"user": self.user, "password": self.pwd}))
        return session

    def setup(self):
        login_file = open(os.path.expanduser('~') + "/Documents/login.json")
        login_config = json.load(login_file)  # must manually create this file
        self.user = login_config["username"]
        self.pwd = login_config["pwd"]
        logger.info("Initializing ATO sensors...")
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RESERVOIR_ATO_PIN, GPIO.IN)
        logger.info("Setup ATO sensors")

    def detection_loop(self):
        # loop sensor reading forever
        self.last_state = None
        while True:
            session = self._login()

            # setup equipment for an unused digital output pin, use state to sense when macro was used
            r = session.get("http://localhost/api/equipment/{id}".format(id=WATER_CHANGE_ID))
            if r.status_code != 200:
                logger.error("Error communicating with equipment API")
                water_change_in_progress = False
            else:
                equipment = json.loads(r.text)
                water_change_in_progress = equipment["on"]

            pin_reading = GPIO.input(RESERVOIR_ATO_PIN)
            if pin_reading == 0 and self.last_state != 0 and not water_change_in_progress:
                self.disable_ato_callback()
            elif pin_reading == 1 and self.last_state != 1 and not water_change_in_progress:
                self.enable_ato_callback()
            if water_change_in_progress:
                # need to do this to allow detection when water change is complete
                self.last_state = None
            else:
                self.last_state = pin_reading
            time.sleep(5)  # check sensor every this amount of seconds

    def disable_ato_callback(self):
        logger.info("water level empty, disabling ATO")
        session = self._login()

        r = session.post("http://localhost/api/macros/{id}/run".format(id=DISABLE_ATO_MACRO_ID))
        if r.status_code != 200:
            logger.error("Error communicating with macro API")
        else:
            logger.info("Sent Macro Request")

    def enable_ato_callback(self):
        logger.info("water refilled, enabling ATO")
        session = self._login()

        r = session.post("http://localhost/api/macros/{id}/run".format(id=ENABLE_ATO_MACRO_ID))
        if r.status_code != 200:
            logger.error("Error communicating with macro API")
        else:
            logger.info("Sent Macro Request")


def main():
    ato = ATO()
    ato.setup()
    ato.detection_loop()


if __name__ == "__main__":
    main()
