#!/usr/bin/python3
# Script de monitoramento do Raspberry Pi e Tailscale com envio condicional via MQTT

import os
import time
import json
import socket
import subprocess
from datetime import datetime, timedelta

# ===================== CONFIGURAÇÕES =====================

# Altere para as informações corretas do seu broker MQTT (Home Assistant)
MQTT_BROKER = "xxxxx"
MQTT_PORT = 1883
MQTT_USER = "xxxx"
MQTT_PASSWORD = "xxxxx"
MQTT_TOPIC = "raspberry/monitor/state"

# ===================== FUNÇÕES AUXILIARES =====================

# Publica payload via MQTT utilizando socket puro (sem dependências externas)
def publish_mqtt(topic, payload):
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((MQTT_BROKER, MQTT_PORT))
        client_id = f"raspberry_pi_{os.uname().nodename}"

        # Constrói pacote CONNECT
        connect_packet = bytearray([0x10])
        payload_connect = bytearray()
        payload_connect.extend(b"\x00\x04MQTT\x04\xC2\x00\x3C")
        payload_connect.extend(len(client_id).to_bytes(2, 'big'))
        payload_connect.extend(client_id.encode())
        payload_connect.extend(len(MQTT_USER).to_bytes(2, 'big'))
        payload_connect.extend(MQTT_USER.encode())
        payload_connect.extend(len(MQTT_PASSWORD).to_bytes(2, 'big'))
        payload_connect.extend(MQTT_PASSWORD.encode())

        # Calcula Remaining Length do pacote CONNECT
        remaining = len(payload_connect)
        while remaining > 0:
            byte = remaining % 128
            remaining //= 128
            connect_packet.append(byte | 0x80 if remaining > 0 else byte)
        connect_packet.extend(payload_connect)

        # Envia CONNECT e ignora CONNACK
        client.send(connect_packet)
        client.recv(4)

        # Constrói pacote PUBLISH
        publish_packet = bytearray([0x30])
        topic_bytes = topic.encode()
        payload_bytes = payload.encode()
        publish_payload = bytearray()
        publish_payload.extend(len(topic_bytes).to_bytes(2, 'big'))
        publish_payload.extend(topic_bytes)
        publish_payload.extend(payload_bytes)

        # Calcula Remaining Length do pacote PUBLISH
        remaining = len(publish_payload)
        while remaining > 0:
            byte = remaining % 128
            remaining //= 128
            publish_packet.append(byte | 0x80 if remaining > 0 else byte)
        publish_packet.extend(publish_payload)

        # Envia o pacote e fecha conexão
        client.send(publish_packet)
        client.close()
        return True
    except Exception as e:
        print(f"Erro ao publicar via MQTT: {e}")
        return False

# Coleta temperatura da CPU
def get_cpu_temperature():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            return round(float(f.read()) / 1000.0, 1)
    except Exception as e:
        print(f"Erro ao obter temperatura: {e}")
        return 0

# Coleta uso da CPU em %
def get_cpu_usage():
    try:
        cmd = "top -bn1 | grep 'Cpu(s)' | awk '{print 100 - $8}'"
        return round(float(subprocess.check_output(cmd, shell=True)), 1)
    except Exception as e:
        print(f"Erro ao obter uso da CPU: {e}")
        return 0

# Coleta informações de memória (RAM)
def get_memory_info():
    try:
        with open('/proc/meminfo') as f:
            lines = f.readlines()
        mem = {line.split(":")[0]: int(line.split()[1]) for line in lines if ":" in line}
        total = mem["MemTotal"]
        available = mem["MemAvailable"]
        used = total - available
        return {
            "total_mb": round(total / 1024, 1),
            "available_mb": round(available / 1024, 1),
            "used_mb": round(used / 1024, 1),
            "percent": round(used * 100 / total, 1)
        }
    except:
        return {}

# Coleta uso de disco na partição raiz
def get_disk_usage():
    try:
        parts = subprocess.check_output("df -h /", shell=True).decode().split('\n')[1].split()
        return {"total": parts[1], "used": parts[2], "available": parts[3], "percent": parts[4]}
    except:
        return {}

# Obtém a data e hora do último boot do sistema
def get_last_boot_time():
    try:
        uptime_seconds = float(open('/proc/uptime').readline().split()[0])
        return (datetime.now() - timedelta(seconds=uptime_seconds)).replace(microsecond=0).isoformat()
    except:
        return ""

# Obtém o IP local do dispositivo na rede
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return ""

# Verifica se o Tailscale está rodando e qual IP está atribuído
def get_tailscale_status():
    try:
        running = int(subprocess.check_output("pgrep -c tailscale", shell=True).decode().strip())
        ip = subprocess.check_output("ip a show tailscale0 | grep 'inet ' | awk '{print $2}' | cut -d/ -f1", shell=True).decode().strip()
        return {"connected": running > 0, "ip": ip}
    except:
        return {"connected": False, "ip": ""}

# Retorna todos os peers do Tailscale, incluindo offline
def get_tailscale_peers():
    try:
        output = subprocess.check_output("tailscale status", shell=True, text=True)
        lines = output.strip().split('\n')
        peers, local_ip = [], get_tailscale_status()["ip"]

        for line in lines:
            if not line.startswith("100."): continue
            parts = line.split()
            if len(parts) < 3: continue
            ip, hostname, platform = parts[:3]
            if ip == local_ip: continue
            status = "offline" if "offline" in line else ("idle" if "idle" in line else "online")
            peers.append({"ip": ip, "hostname": hostname, "platform": platform, "status": status})
        return peers
    except Exception as e:
        print(f"Erro ao obter peers do Tailscale: {e}")
        return []

# Função que detecta mudanças significativas no status dos clientes
def houve_mudanca_status(novo, antigo):
    # Trata 'online' e 'idle' como equivalentes ('online')
    def normalizar(status):
        return "online" if status in ["online", "idle"] else "offline"

    if len(novo) != len(antigo):
        return True

    for c_novo in novo:
        correspondente = next((c for c in antigo if c["ip"] == c_novo["ip"]), None)
        if not correspondente:
            return True
        if normalizar(c_novo["status"]) != normalizar(correspondente["status"]):
            return True

    return False

# ===================== LOOP PRINCIPAL =====================

def main():
    print("📡 Iniciando monitoramento do Raspberry Pi + Tailscale...")
    ultimo_envio = time.time()
    ultimo_status_vpn = True
    ultimo_clientes = []
    intervalo_envio = 300  # segundos
    intervalo_verificacao = 10  # segundos

    while True:
        try:
            agora = time.time()
            # Coleta dados de sistema e Tailscale
            tailscale = get_tailscale_status()
            tailscale_clientes = get_tailscale_peers()

            # Mantém todos para verificação interna
            status_atual = [{"ip": c["ip"], "hostname": c["hostname"], "status": c["status"]} for c in tailscale_clientes]

            # Filtra clientes para enviar apenas os online/idle no payload
            clientes_visiveis = [c for c in tailscale_clientes if c["status"] in ["online", "idle"]]

            # Monta o payload JSON para envio
            payload = {
                "timestamp": datetime.now().isoformat(),
                "hostname": os.uname().nodename,
                "last_boot": get_last_boot_time(),
                "ip_local": get_local_ip(),
                "cpu": {
                    "temperature": get_cpu_temperature(),
                    "percent": get_cpu_usage()
                },
                "memory": get_memory_info(),
                "disk": get_disk_usage(),
                "tailscale": tailscale,
                "tailscale_clientes": clientes_visiveis
            }

            # Converte para string JSON
            payload_str = json.dumps(payload)

            # Verifica se é hora de enviar
            deve_enviar = False
            if agora - ultimo_envio >= intervalo_envio:
                print("⏰ Envio periódico")
                deve_enviar = True
            elif ultimo_status_vpn and not tailscale["connected"]:
                print("🚨 VPN ficou OFFLINE")
                deve_enviar = True
            elif houve_mudanca_status(status_atual, ultimo_clientes):
                print("🔄 Mudança no status dos clientes")
                deve_enviar = True

            # Envia MQTT se necessário
            if deve_enviar:
                success = publish_mqtt(MQTT_TOPIC, payload_str)
                if success:
                    print(f"✅ Dados enviados com sucesso.")
                    ultimo_envio = agora
                    ultimo_status_vpn = tailscale["connected"]
                    ultimo_clientes = status_atual.copy()
                else:
                    print("❌ Falha ao publicar via MQTT.")

            # Aguarda próximo ciclo
            time.sleep(intervalo_verificacao)

        except KeyboardInterrupt:
            print("🛑 Monitoramento interrompido pelo usuário.")
            break
        except Exception as e:
            print(f"⚠️ Erro no loop principal: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
