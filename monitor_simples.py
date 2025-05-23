#!/usr/bin/python3
# Script de monitoramento simples sem dependências externas

import os
import time
import json
import socket
import subprocess
from datetime import datetime

# Configurações - ALTERE ESTAS INFORMAÇÕES
MQTT_BROKER = "IP_DO_SEU_HOME_ASSISTANT"  # Substitua pelo IP do seu Home Assistant
MQTT_PORT = 1883
MQTT_USER = "SEU_USUARIO"                 # Substitua pelo seu usuário MQTT
MQTT_PASSWORD = "SUA_SENHA"               # Substitua pela sua senha MQTT
MQTT_TOPIC = "raspberry/monitor/state"

# Função para enviar dados via socket (MQTT básico)
def publish_mqtt(topic, payload):
    try:
        # Conectar ao broker MQTT
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((MQTT_BROKER, MQTT_PORT))
        
        # Construir pacote MQTT Connect
        client_id = f"raspberry_pi_{os.uname().nodename}"
        connect_packet = bytearray([0x10])  # CONNECT
        
        # Payload do CONNECT
        payload_connect = bytearray()
        payload_connect.extend(b"\x00\x04MQTT\x04\xC2\x00\x3C")
        
        # Client ID
        payload_connect.extend(len(client_id).to_bytes(2, 'big'))
        payload_connect.extend(client_id.encode())
        
        # Username
        payload_connect.extend(len(MQTT_USER).to_bytes(2, 'big'))
        payload_connect.extend(MQTT_USER.encode())
        
        # Password
        payload_connect.extend(len(MQTT_PASSWORD).to_bytes(2, 'big'))
        payload_connect.extend(MQTT_PASSWORD.encode())
        
        # Remaining Length
        remaining_length = len(payload_connect)
        while remaining_length > 0:
            byte = remaining_length % 128
            remaining_length = remaining_length // 128
            if remaining_length > 0:
                byte |= 0x80
            connect_packet.append(byte)
        
        # Adicionar payload
        connect_packet.extend(payload_connect)
        
        # Enviar pacote CONNECT
        client.send(connect_packet)
        
        # Receber CONNACK (ignorando o conteúdo)
        client.recv(4)
        
        # Construir pacote PUBLISH
        publish_packet = bytearray([0x30])  # PUBLISH
        
        # Topic
        topic_bytes = topic.encode()
        topic_len = len(topic_bytes)
        
        # Payload
        payload_bytes = payload.encode()
        payload_len = len(payload_bytes)
        
        # Payload do PUBLISH
        payload_publish = bytearray()
        payload_publish.extend(topic_len.to_bytes(2, 'big'))
        payload_publish.extend(topic_bytes)
        payload_publish.extend(payload_bytes)
        
        # Remaining Length
        remaining_length = len(payload_publish)
        while remaining_length > 0:
            byte = remaining_length % 128
            remaining_length = remaining_length // 128
            if remaining_length > 0:
                byte |= 0x80
            publish_packet.append(byte)
        
        # Adicionar payload
        publish_packet.extend(payload_publish)
        
        # Enviar pacote PUBLISH
        client.send(publish_packet)
        
        # Fechar conexão
        client.close()
        return True
    except Exception as e:
        print(f"Erro ao publicar via MQTT: {e}")
        return False

# Função para obter temperatura da CPU
def get_cpu_temperature():
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read().strip()) / 1000.0
        return round(temp, 1)
    except Exception as e:
        print(f"Erro ao obter temperatura: {e}")
        return 0

# Função para obter uso da CPU
def get_cpu_usage():
    try:
        cmd = "top -bn1 | grep 'Cpu(s)' | sed 's/.*, *\\([0-9.]*\\)%* id.*/\\1/' | awk '{print 100 - $1}'"
        cpu_percent = float(subprocess.check_output(cmd, shell=True).decode().strip())
        return round(cpu_percent, 1)
    except Exception as e:
        print(f"Erro ao obter uso da CPU: {e}")
        return 0

# Função para obter informações de memória
def get_memory_info():
    try:
        with open('/proc/meminfo', 'r') as f:
            mem_info = f.readlines()
        
        mem_total = 0
        mem_available = 0
        
        for line in mem_info:
            if 'MemTotal' in line:
                mem_total = int(line.split()[1])
            elif 'MemAvailable' in line:
                mem_available = int(line.split()[1])
        
        # Converter para MB
        mem_total_mb = round(mem_total / 1024, 1)
        mem_available_mb = round(mem_available / 1024, 1)
        mem_used_mb = round((mem_total - mem_available) / 1024, 1)
        mem_percent = round((mem_total - mem_available) * 100 / mem_total, 1)
        
        return {
            "total_mb": mem_total_mb,
            "available_mb": mem_available_mb,
            "used_mb": mem_used_mb,
            "percent": mem_percent
        }
    except Exception as e:
        print(f"Erro ao obter informações de memória: {e}")
        return {"total_mb": 0, "available_mb": 0, "used_mb": 0, "percent": 0}
      
# Função para obter o horário do último boot
def get_last_boot_time():
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        boot_time = datetime.now() - timedelta(seconds=uptime_seconds)
        return boot_time.replace(microsecond=0).isoformat()
    except Exception as e:
        print(f"Erro ao obter o último boot: {e}")
        return ""

# Função para buscar o IP local
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception as e:
        print(f"Erro ao obter IP local: {e}")
        return ""

# Função para verificar status do Tailscale
def get_tailscale_status():
    try:
        # Verificar se o processo tailscale está rodando
        cmd = "ps aux | grep tailscale | grep -v grep | wc -l"
        process_count = int(subprocess.check_output(cmd, shell=True).decode().strip())
        
        # Obter IP do Tailscale (se disponível)
        ip = ""
        try:
            cmd = "ip addr show tailscale0 2>/dev/null | grep 'inet ' | awk '{print $2}' | cut -d/ -f1"
            ip = subprocess.check_output(cmd, shell=True).decode().strip()
        except:
            pass
        
        return {
            "connected": process_count > 0,
            "ip": ip
        }
    except Exception as e:
        print(f"Erro ao obter status do Tailscale: {e}")
        return {"connected": False, "ip": ""}

# Função principal
def main():
    print("Iniciando monitoramento do Raspberry Pi...")
    
    while True:
        try:
            # Coletar dados
            cpu_temp = get_cpu_temperature()
            cpu_usage = get_cpu_usage()
            memory = get_memory_info()
            tailscale = get_tailscale_status()
            
            # Criar payload JSON
            payload = {
                "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                "hostname": os.uname().nodename,
                "last_boot": get_last_boot_time(),
                "ip_local": get_local_ip(),
                "cpu": {
                    "temperature": cpu_temp,
                    "percent": cpu_usage
                },
                "memory": memory,
                "tailscale": tailscale
            }
            
            # Converter para string JSON
            payload_str = json.dumps(payload)
            
            # Publicar via MQTT
            success = publish_mqtt(MQTT_TOPIC, payload_str)
            
            if success:
                print(f"Dados publicados em {MQTT_TOPIC}")
            else:
                print("Falha ao publicar dados")
            
            # Aguardar 60 segundos
            time.sleep(60)
            
        except KeyboardInterrupt:
            print("Monitoramento interrompido pelo usuário")
            break
        except Exception as e:
            print(f"Erro no loop principal: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
# Fim do script
