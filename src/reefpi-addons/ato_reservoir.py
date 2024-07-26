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
        login_config = json.loads("/root/config/login.json")  # must manually create this file
        self.user = login_config["username"]
        self.pwd = login_config["pwd"]
        logger.info("Initializing ATO sensors...")
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RESERVOIR_ATO_PIN, GPIO.IN)

        # want to detect when reservoir is empty, so set callback on falling edge
        GPIO.add_event_detect(RESERVOIR_ATO_PIN, GPIO.FALLING, callback=self.disable_ato_callback, bouncetime=200)

        # when water is refilled, allow ATO usage again
        GPIO.add_event_detect(RESERVOIR_ATO_PIN, GPIO.RISING, callback=self.enable_ato_callback, bouncetime=200)
        logger.info("Setup ATO sensors")

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


if __name__ == "__main__":
    ato = ATO()
    ato.setup()
