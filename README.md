<a href="https://www.raspberrypi.com/" target="_blank">
  <img src="https://img.shields.io/badge/Raspberry%20Pi-C51A4A?style=for-the-badge&logo=raspberrypi&logoColor=white" alt="Raspberry Pi" />
</a>
<a href="https://www.home-assistant.io/" target="_blank">
  <img src="https://img.shields.io/badge/Home%20Assistant-41BDF5?style=for-the-badge&logo=home-assistant&logoColor=white" alt="Home Assistant Badge" />
</a>
<a href="https://mqtt.org/" target="_blank">
  <img src="https://img.shields.io/badge/MQTT-660066?style=for-the-badge&logo=mqtt&logoColor=white" alt="MQTT Badge" />
</a>
<a href="https://www.python.org/" target="_blank">
    <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
</a>

# Raspberry Pi Monitor via MQTT (Zero Dependência Externa)
<div align="center">
  <img src="https://github.com/user-attachments/assets/f98bf0f6-978c-4b6e-b3a2-f6e2b0cdfe6f" width="400"/>
</div>
<br>
Script simples em Python 3 para monitoramento de um Raspberry Pi via <b>MQTT</b> , ideal para integração com o <b>Home Assistant</b> . Utiliza apenas bibliotecas nativas do Python e sockets diretos (sem mosquitto-clients, paho, etc).


---

## ✅ Pontos fortes

- **Zero dependência de `apt`** – Não usa `mosquitto-clients`, apenas bibliotecas nativas do Python.
- **Script único e leve** – Ideal para sistemas embarcados e headless
- Monitoramento VPN incluído – Pensado especialmente para meu caso de uso, em que o Raspberry Pi atua como uma ponte de acesso remoto utilizando Tailscale. O status da VPN é verificado a cada ciclo de envio, informando se está conectado e qual IP foi atribuído pela rede privada do Tailscale.
- **MQTT puro** – Implementação do protocolo MQTT diretamente via sockets TCP (sem paho ou similares).
- **Comunicação assíncrona** – O RPi envia periodicamente, sem precisar ser consultado.
- **Reutilizável e extensível** – Fácil adicionar novas métricas (disco, carga etc.).

## 📌 Funcionalidades
- Monitoramento completo do Raspberry Pi:
  - Temperatura da CPU
  - Uso de CPU (%)
  - Uso de memória (MB e %)
  - Tempo desde o último boot
  - IP local da rede
- Monitoramento da VPN Tailscale:
  - Verifica se o Tailscale está ativo
  - Retorna o IP virtual atribuído (tailscale0)
---

📡Os dados são enviados a cada 1 minuto (Parametrizável) no formato JSON para um tópico MQTT definido pelo usuário.
Tópico padrão:
```python
MQTT_TOPIC = "raspberry/monitor/state"
```
Exemplo de payload:
```json
{
  "timestamp": "2025-05-23T15:42:10",
  "hostname": "raspberrypi",
  "last_boot": "2025-05-23T08:37:51",
  "ip_local": "111.111.1.22",
  "cpu": {
    "temperature": 54.3,
    "percent": 12.7
  },
  "memory": {
    "total_mb": 483.2,
    "available_mb": 237.5,
    "used_mb": 245.7,
    "percent": 50.8
  },
  "tailscale": {
    "connected": true,
    "ip": "112.541.300.1"
  }
}
```
## 🛠️ Configuração
### 1. Ajuste as variáveis no script
Edite as seguintes variáveis no `monitor_simples.py`:

```python
MQTT_BROKER = "IP_DO_SEU_HOME_ASSISTANT"  # Substitua pelo IP do seu Home Assistant
MQTT_USER = "SEU_USUARIO"                 # Substitua pelo seu usuário MQTT
MQTT_PASSWORD = "SUA_SENHA"               # Substitua pela sua senha MQTT
```
### 2. Crie o script de monitoramento
```git
nano ~/monitor_simples.py
```
Utilize o script [monitor_simples.py](https://github.com/thsrv/rpi-monitor-mqtt/blob/main/monitor_simples.py) deste repositório copiando seu conteúdo completo.
Depois, torne-o executável:
```git
chmod +x ~/monitor_simples.py
```
Execute com:
```git
python3 ~/monitor_simples.py
```
### 3. Executar como serviço (opcional, recomendado)
Crie o serviço:
```git
sudo nano /etc/systemd/system/monitor_simples.service
```
Cole o conteúdo abaixo:
```ini
[Unit]
Description=Monitoramento simples MQTT para Home Assistant
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/SEU_USUARIO_RPI/monitor_simples.py
Restart=always
User=SEU_USUARIO_RPI

[Install]
WantedBy=multi-user.target
```
> ⚠️ Não se esqueça de substituir `SEU_USUARIO_RPI` pelo nome do seu usuário no Raspberry Pi.

Ative o serviço:
```git
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable monitor_simples.service
sudo systemctl start monitor_simples.service
```
Verifique se está rodando:
```git
sudo systemctl status monitor_simples.service
```

### 4. Configuração no Home Assistant
No seu `configuration.yaml`, adicione:
```yaml
mqtt:
  sensor:
    - name: "Raspberry Pi CPU Temperature"
      state_topic: "raspberry/monitor/state"
      unit_of_measurement: "°C"
      value_template: "{{ value_json.cpu.temperature }}"
      icon: "mdi:thermometer"

    - name: "Raspberry Pi CPU Usage"
      state_topic: "raspberry/monitor/state"
      unit_of_measurement: "%"
      value_template: "{{ value_json.cpu.percent }}"
      icon: "mdi:cpu-64-bit"

    - name: "Raspberry Pi Memory Usage"
      state_topic: "raspberry/monitor/state"
      unit_of_measurement: "%"
      value_template: "{{ value_json.memory.percent }}"
      icon: "mdi:memory"

    - name: "Raspberry Pi Tailscale Status"
      state_topic: "raspberry/monitor/state"
      value_template: "{% if value_json.tailscale.connected %}Connected{% else %}Disconnected{% endif %}"
      icon: "mdi:vpn"
```

## 📝 Observações
- Compatível com hardware antigo e leve.
- Ideal para RPi com pouca RAM e rede limitada (sem overhead de SSH remoto).

## 👤 Autor
[**Thiago Saraiva**](https://github.com/thsrv)<br>
Este projeto foi criado para uso pessoal em um ambiente Home Lab com Raspberry Pi, especialmente para monitoramento via MQTT integrado ao Home Assistant.
Está disponível publicamente para quem quiser usar, adaptar ou expandir conforme suas necessidades.
💡 Sugestões, melhorias e contribuições são muito bem-vindas!

## 📜 Licença
MIT. Use à vontade.
