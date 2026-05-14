#!/usr/bin/env python3

import socket
import time

HOST = "192.168.1.254"
PORT = 4001
TIMEOUT = 3.0

def send(cmd):

    try:

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        s.settimeout(TIMEOUT)

        s.connect((HOST, PORT))

        full = cmd + "\n"

        print(f"SENDING: {full.strip()}")

        s.sendall(full.encode("ascii"))

        time.sleep(0.4)

        try:

            response = s.recv(4096)

            if response:

                print("RESPONSE:", response.decode(errors="ignore"))

        except:

            pass

        s.close()

    except Exception as e:

        print("ERROR:", e)


def activity_hifi_rose():

    send("INPUT SET BAL1")
    time.sleep(0.5)

    send("VOLUME SET 18")
    time.sleep(0.5)

    send("MUTE OFF")


def activity_roon_bacch():

    send("INPUT SET BAL2")
    time.sleep(0.5)

    send("VOLUME SET 18")
    time.sleep(0.5)

    send("MUTE OFF")


def activity_roku_apple():

    send("INPUT SET BAL3")
    time.sleep(0.5)

    send("VOLUME SET 18")
    time.sleep(0.5)

    send("MUTE OFF")


if __name__ == "__main__":

    print("\nAVAILABLE ACTIVITIES:\n")

    print("1 = HiFi Rose")
    print("2 = Roon/BACCH")
    print("3 = Roku-Apple\n")

    choice = input("Select Activity: ").strip()

    if choice == "1":

        activity_hifi_rose()

    elif choice == "2":

        activity_roon_bacch()

    elif choice == "3":

        activity_roku_apple()

    else:

        print("Invalid choice")

