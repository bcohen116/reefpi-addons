"""
    Handles starting multiple monitoring scripts from one place.
    This should run from a service so everything runs on boot.
"""
import subprocess
import os
import time


def runner():
    # main function
    print("Starting reef pi addon scripts...")
    current_location = os.path.abspath(os.path.dirname(__file__))

    # run ATO reservoir script
    ato_script = os.path.join(current_location, "ato_reservoir.py")
    subprocess.run(["python3", ato_script])

    print("launched processes.")

    while True:
        # sleep so cpu doesn't get maxed and this program stays open
        time.sleep(5)


def main():
    runner()


if __name__ == "__main__":
    main()
