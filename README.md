# TP MQTT - Intersection Coopérative EV3
## VA55 - UTBM

Système de gestion d'intersection pour robots EV3 via MQTT avec 3 modes de fonctionnement.

---

## 🚀 Démarrage Rapide

### 1. Lancer l'infrastructure

```bash
# Démarrer Mosquitto + Node-RED
docker compose up -d

# Vérifier que tout fonctionne
docker compose ps
```

### 2. Accéder aux interfaces

| Service | URL | Description |
|---------|-----|-------------|
| Node-RED | http://localhost:1880 | Éditeur de flows |
| Dashboard | http://localhost:1880/ui | Interface de contrôle |
| MQTT | localhost:1883 | Broker Mosquitto |

### 3. Importer les flows Node-RED

1. Ouvrir http://localhost:1880
2. Menu → Import → Sélectionner `nodered/flows.json`
3. Deploy

### 4. Configurer le robot EV3

Éditer `code_ev3/config.py`:
```python
BROKER_IP = "192.168.X.X"  # IP de votre PC
ROBOT_ID = "EV3_01"        # ID unique
VOIE = "A"                 # A ou B
```

### 5. Lancer le robot

Transférer le dossier `code_ev3/` sur l'EV3 et exécuter `main.py`.

---

## 📁 Structure du Projet

```
TP_MQTT/
├── docker-compose.yml    # Infrastructure Docker
├── mosquitto/
│   └── mosquitto.conf    # Config broker MQTT
├── nodered/
│   └── flows.json        # Flows Node-RED multi-mode
├── code_ev3/
│   ├── main.py           # Programme principal EV3
│   ├── config.py         # Configuration (IP, ID, voie)
│   ├── sensors.py        # Capteurs + auto-calibration
│   └── mqtt_client.py    # Client MQTT simplifié
├── tests/
│   └── test_8_robots.py  # Test automatisé 8 robots
├── protocol.md           # Documentation protocole
└── README.md             # Ce fichier
```

---

## 🎛️ Les 3 Modes

### Mode 1: FEU 🚦
Feu tricolore temporel. Les robots attendent que le feu de leur voie soit vert.

### Mode 2: FIFO 📋
Premier arrivé, premier servi. File d'attente automatique.

### Mode 3: PELOTON 🚗
Gestion par slots. Formation de peloton avec espacement.

**Changement de mode:** Via le dropdown dans le Dashboard Node-RED.

---

## 🧪 Tests

### Test manuel avec Mosquitto

```bash
# Écouter les messages
mosquitto_sub -h localhost -t '#' -v

# Simuler un robot
mosquitto_pub -h localhost -t 'intersection/status' \
  -m '{"id":"EV3_01","voie":"A","etape":2,"action":"stop"}'
```

### Test automatisé (8 robots)

```bash
cd tests/
pip install paho-mqtt colorama
python test_8_robots.py --mode FIFO
```

---

## 📡 Format Message

### Robot → Contrôleur
```json
{"id": "EV3_01", "voie": "A", "etape": 2, "action": "stop"}
```

### Contrôleur → Robot
```json
{"target_id": "EV3_01", "action": "GO"}
```

---

## 🔧 Dépannage

### Docker ne démarre pas
```bash
docker compose down
docker compose up -d --build
```

### EV3 ne se connecte pas
1. Vérifier l'IP dans `config.py`
2. Vérifier que Mosquitto écoute sur 0.0.0.0 (pas 127.0.0.1)
3. Test: `mosquitto_pub -h <IP_PC> -p 1883 -t test -m hello`

### Node-RED ne reçoit pas les messages
1. Vérifier que le broker est "mosquitto" (pas "localhost") dans flows.json
2. Redéployer les flows

---

## 📚 Documentation

- [protocol.md](protocol.md) - Protocole MQTT détaillé
- [VA55_2025_TP_MQTT.pdf](VA55_2025_TP_MQTT.pdf) - Sujet du TP

---

*VA55 - UTBM - 2025*
# TP-VA55-MQTT
