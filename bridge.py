#!/usr/bin/env python3
import subprocess
import logging
import sys

import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
)

BROKER = "localhost"
PORT = 1883
TOPIC = "shairport-sync/remote"

COMMANDS = {
    "volumeup":   ["amixer", "sset", "PCM", "5%+"],
    "volumedown": ["amixer", "sset", "PCM", "5%-"],
    "mutetoggle": ["amixer", "sset", "PCM", "toggle"],
}

IGNORED = {"playpause", "nextitem", "previtem"}


def on_connect(client, userdata, flags, reason_code, properties):
    logging.info("Connected to MQTT broker, subscribing to %s", TOPIC)
    if reason_code == 0:
        client.subscribe(TOPIC)
    else:
        logging.error("Connection refused, reason code: %s", reason_code)


def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8").strip()

    if payload in COMMANDS:
        cmd = COMMANDS[payload]
        logging.info("Running command for '%s': %s", payload, " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
            )
            logging.info("amixer output: %s", result.stdout.strip())
            if result.returncode != 0:
                logging.warning("amixer stderr: %s", result.stderr.strip())
        except (subprocess.SubprocessError, OSError, subprocess.TimeoutExpired) as exc:
            logging.error("Failed to run amixer for '%s': %s", payload, exc)

    elif payload in IGNORED:
        logging.debug("Ignoring %s (not supported)", payload)

    else:
        logging.warning("Unknown command: %s", payload)


def on_disconnect(client, userdata, flags, reason_code, properties):
    logging.info("Disconnected from MQTT broker (reason_code=%s)", reason_code)


if __name__ == "__main__":
    client = mqtt.Client(callback_api_version=CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_disconnect = on_disconnect

    try:
        client.connect(BROKER, PORT)
        client.loop_forever()
    except KeyboardInterrupt:
        logging.info("Shutting down bridge")
        client.disconnect()
