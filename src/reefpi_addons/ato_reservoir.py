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
DEBOUNCE_SECONDS = 5  # seconds a reading must remain stable before acting
SENSOR_POLL_SECONDS = 0.1
WATER_CHANGE_POLL_SECONDS = 5


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
        # debounce state
        self.debounce_seconds = DEBOUNCE_SECONDS
        self.last_state = None
        self._pending_state = None
        self._last_change_time = None

    def detection_loop(self):
        water_change_in_progress = False
        next_water_change_check = 0

        while True:
            now = time.monotonic()
            if now >= next_water_change_check:
                session = self._login()
                # setup equipment for an unused digital output pin, use state to sense when macro was used
                r = session.get("http://localhost/api/equipment/{id}".format(id=WATER_CHANGE_ID))
                if r.status_code != 200:
                    logger.error("Error communicating with equipment API")
                    water_change_in_progress = False
                else:
                    equipment = json.loads(r.text)
                    water_change_in_progress = equipment["on"]
                next_water_change_check = time.monotonic() + WATER_CHANGE_POLL_SECONDS

            now = time.monotonic()
            pin_reading = GPIO.input(RESERVOIR_ATO_PIN)

            if water_change_in_progress:
                # reset debounce state during water change so we re-learn state afterwards
                self.last_state = None
                self._pending_state = None
                self._last_change_time = None
            else:
                # initialize stable state on first valid read
                if self.last_state is None:
                    self.last_state = pin_reading
                    self._pending_state = None
                    self._last_change_time = None
                else:
                    if pin_reading != self.last_state:
                        # saw a different reading, start or continue debounce timer
                        if self._pending_state is None or self._pending_state != pin_reading:
                            self._pending_state = pin_reading
                            self._last_change_time = now
                        else:
                            # pending state matches current reading, check if stable long enough
                            if now - self._last_change_time >= self.debounce_seconds:
                                # commit the new stable state and trigger callback
                                self.last_state = self._pending_state
                                self._pending_state = None
                                self._last_change_time = None
                                if self.last_state == 0:
                                    self.disable_ato_callback()
                                elif self.last_state == 1:
                                    self.enable_ato_callback()
                    else:
                        # reading matches stable state, clear any pending change
                        self._pending_state = None
                        self._last_change_time = None

            time.sleep(SENSOR_POLL_SECONDS)

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
