# 🦟 Mosquitto - Broker MQTT
## VA55 - UTBM

Ce répertoire contient la configuration du broker MQTT Mosquitto.

---

## 📁 Structure

```
mosquitto/
├── mosquitto.conf    # Configuration du broker
├── data/             # Données persistantes
├── log/              # Logs
└── README.md         # Cette documentation
```

---

## ⚙️ Configuration (`mosquitto.conf`)

### Configuration Standard

```conf
# Écouter sur toutes les interfaces
listener 1883

# Pas d'authentification (développement)
allow_anonymous true

# Persistance des messages
persistence true
persistence_location /mosquitto/data/

# Logs
log_dest file /mosquitto/log/mosquitto.log
log_type all
```

### Configuration Sécurisée (Production)

```conf
# Écouter sur le port standard
listener 1883

# Authentification par mot de passe
allow_anonymous false
password_file /mosquitto/config/passwd

# TLS (optionnel)
# listener 8883
# cafile /mosquitto/config/ca.crt
# certfile /mosquitto/config/server.crt
# keyfile /mosquitto/config/server.key
```

---

## 🚀 Lancement

### Via Docker Compose (Recommandé)

```bash
# Depuis la racine du projet
docker compose up -d mosquitto

# Vérifier le statut
docker compose ps mosquitto

# Voir les logs
docker compose logs -f mosquitto
```

### Via Docker Seul

```bash
docker run -d \
  --name mosquitto \
  -p 1883:1883 \
  -v $(pwd)/mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf \
  eclipse-mosquitto
```

---

## 🧪 Tests

### Vérifier que le broker est actif

```bash
mosquitto_sub -h localhost -p 1883 -t '$SYS/#' -C 1
```

### Écouter tous les messages

```bash
mosquitto_sub -h localhost -p 1883 -t '#' -v
```

### Publier un message de test

```bash
mosquitto_pub -h localhost -p 1883 -t 'test/topic' -m 'Hello MQTT'
```

### Simuler un robot

```bash
# Message de statut
mosquitto_pub -h localhost -p 1883 -t 'intersection/status' \
  -m '{"id":"R1","voie":"A","etape":1,"cause":"marker_entry"}'
```

---

## 📊 Monitoring

### Topics Système

| Topic | Description |
|-------|-------------|
| `$SYS/broker/version` | Version de Mosquitto |
| `$SYS/broker/clients/connected` | Nombre de clients |
| `$SYS/broker/messages/received` | Messages reçus |
| `$SYS/broker/messages/sent` | Messages envoyés |

### Consulter les stats

```bash
mosquitto_sub -h localhost -t '$SYS/#' -v
```

---

## 🔧 Dépannage

### Le broker ne démarre pas

```bash
# Vérifier les logs
docker compose logs mosquitto

# Vérifier la configuration
docker exec mosquitto mosquitto -c /mosquitto/config/mosquitto.conf -t
```

### Port déjà utilisé

```bash
# Trouver le processus
lsof -i :1883

# Tuer le processus (si nécessaire)
kill -9 <PID>
```

### Les clients ne se connectent pas

1. Vérifiez `allow_anonymous true` dans la config
2. Vérifiez que le firewall autorise le port 1883
3. Testez avec: `telnet localhost 1883`

---

## 📡 Ports

| Port | Protocole | Description |
|------|-----------|-------------|
| 1883 | MQTT | Connexion standard |
| 9001 | WebSocket | Connexion web (si configuré) |
| 8883 | MQTT+TLS | Connexion sécurisée (si configuré) |

---

*Documentation Mosquitto - VA55 UTBM*
