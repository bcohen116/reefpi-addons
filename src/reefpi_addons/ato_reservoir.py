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
            pin_reading = GPIO.input(RESERVOIR_ATO_PIN)
            if pin_reading is False and self.last_state is not False:
                self.disable_ato_callback()
            elif pin_reading is True and self.last_state is not True:
                self.enable_ato_callback()
            self.last_state = pin_reading
            time.sleep(5)  # check sensor every this amount of seconds

    def disable_ato_callback(self):
        logger.info("water level empty, disabling ATO")
        session = self._login()

        r = session.get("http://localhost/api/macros/{id}/run".format(id=DISABLE_ATO_MACRO_ID))
        if r.status_code != 200:
            logger.error("Error communicating with macro API")
        else:
            logger.info("Sent Macro Request")

    def enable_ato_callback(self):
        logger.info("water refilled, enabling ATO")
        session = self._login()

        r = session.get("http://localhost/api/macros/{id}/run".format(id=ENABLE_ATO_MACRO_ID))
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
