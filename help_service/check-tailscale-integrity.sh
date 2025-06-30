#!/usr/bin/python3
import os
import socket
import time
from datetime import datetime

# Configurações MQTT
MQTT_BROKER = "XXXXXXXXXXXXXXXXX"  # Substitua pelo IP do Home Assistant
MQTT_PORT = 1883
MQTT_USER = "XXXXXXXXXXX"                  # Substitua se necessário
MQTT_PASSWORD = "XXXXXXXXXXX"              # Substitua se necessário
MQTT_TOPIC = "raspberry/monitor/binarios"

RESTORE_SCRIPT = "/usr/local/bin/restore-tailscale.sh"
LOG_FILE = "/var/log/verifica_integridade.log"

def log(msg):
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now().isoformat()}] {msg}\n")

def is_elf(filepath):
    try:
        with open(filepath, "rb") as f:
            return f.read(4) == b'\x7fELF'
    except:
        return False

def publish_mqtt(topic, payload):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((MQTT_BROKER, MQTT_PORT))

        client_id = f"integridade_checker_{os.uname().nodename}"
        connect_packet = bytearray([0x10])

        payload_connect = bytearray()
        payload_connect.extend(b"\x00\x04MQTT\x04\xC2\x00\x3C")

        payload_connect.extend(len(client_id).to_bytes(2, 'big'))
        payload_connect.extend(client_id.encode())

        payload_connect.extend(len(MQTT_USER).to_bytes(2, 'big'))
        payload_connect.extend(MQTT_USER.encode())

        payload_connect.extend(len(MQTT_PASSWORD).to_bytes(2, 'big'))
        payload_connect.extend(MQTT_PASSWORD.encode())

        remaining_length = len(payload_connect)
        while remaining_length > 0:
            byte = remaining_length % 128
            remaining_length = remaining_length // 128
            if remaining_length > 0:
                byte |= 0x80
            connect_packet.append(byte)

        connect_packet.extend(payload_connect)
        client.send(connect_packet)
        client.recv(4)

        topic_bytes = topic.encode()
        topic_len = len(topic_bytes)
        payload_bytes = payload.encode()
        payload_len = len(payload_bytes)

        publish_packet = bytearray([0x30])
        payload_publish = bytearray()
        payload_publish.extend(topic_len.to_bytes(2, 'big'))
        payload_publish.extend(topic_bytes)
        payload_publish.extend(payload_bytes)

        remaining_length = len(payload_publish)
        while remaining_length > 0:
            byte = remaining_length % 128
            remaining_length = remaining_length // 128
            if remaining_length > 0:
                byte |= 0x80
            publish_packet.append(byte)

        publish_packet.extend(payload_publish)
        client.send(publish_packet)
        client.close()
        return True
    except Exception as e:
        log(f"Erro ao enviar MQTT: {e}")
        return False

def main():
    bin1 = is_elf("/usr/local/bin/tailscale")
    bin2 = is_elf("/usr/local/bin/tailscaled")

    if bin1 and bin2:
        log("Binários íntegros. Enviando true via MQTT.")
        publish_mqtt(MQTT_TOPIC, "true")
    else:
        log("Binários corrompidos. Restaurando e enviando false via MQTT.")
        os.system(f"bash {RESTORE_SCRIPT}")
        publish_mqtt(MQTT_TOPIC, "false")

if __name__ == "__main__":
    main()
