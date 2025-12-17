# Protocole MQTT - Intersection Coopérative
## VA55 - UTBM

Ce document définit le protocole de communication MQTT pour le système d'intersection coopérative multi-mode.

---

## 📡 Topics

| Topic | Direction | Description |
|-------|-----------|-------------|
| `intersection/status` | Robot → Contrôleur | Statut du robot (événementiel) |
| `intersection/command` | Contrôleur → Robot | Commandes au robot |

---

## 📨 Format des Messages

### Message Status (Robot → Contrôleur)

```json
{
  "id": "EV3_01",
  "voie": "A",
  "etape": 2,
  "action": "stop"
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `id` | string | Identifiant unique du robot |
| `voie` | string | Piste (A ou B) |
| `etape` | int | 0=Loin, 1=Entrée zone, 2=Ligne arrêt, 3=Sortie |
| `action` | string | "run" ou "stop" |

### Message Command (Contrôleur → Robot)

```json
{
  "target_id": "EV3_01",
  "action": "GO"
}
```

| Champ | Type | Description |
|-------|------|-------------|
| `target_id` | string | Robot cible (ou "ALL") |
| `action` | string | GO, STOP, ADVANCE |

---

## ⚡ Envoi Événementiel (4 Moments Clés)

Le robot n'envoie **PAS** de données en continu. Il envoie uniquement lors de ces 4 événements:

| # | Moment | Étape | Action | Signification |
|---|--------|-------|--------|---------------|
| 1 | 1er RED détecté | 1 | run | "J'arrive dans la zone" |
| 2 | 2ème RED détecté | 2 | stop | "Je suis à la ligne, j'attends" |
| 3 | Après réception GO | 2 | run | "Je traverse" |
| 4 | 3ème RED détecté | 3 | run | "J'ai quitté l'intersection" |

---

## 🎛️ Les 3 Modes du Contrôleur

Le mode est configuré dans Node-RED, **pas** dans le robot.

### Mode 1: FEU (Feu Tricolore)

```
Robot envoie etape=2 action=stop
  → Contrôleur vérifie feu[voie]
  → Si VERT: envoie GO
  → Si ROUGE: attend
```

**Changement de feu:** Manuel via dashboard (bouton Toggle)

### Mode 2: FIFO (Premier Arrivé Premier Servi)

```
Robot envoie etape=2 action=stop
  → Si intersection LIBRE: GO + verrouille
  → Si intersection OCCUPÉ: STOP + ajoute à queue

Robot envoie etape=3
  → Libère intersection
  → Envoie GO au premier de la queue
```

### Mode 3: PELOTON (Gestion des Slots)

```
Robot envoie etape=1 (entrée zone)
  → Si slot2 occupé: STOP (reste en slot1)
  → Si slot2 libre: continue

Robot envoie etape=2 (ligne arrêt)
  → Occupe slot2
  → Si intersection LIBRE: GO
  → Sinon: STOP

Robot envoie etape=3 (sortie)
  → Libère slot2
  → Envoie ADVANCE au robot en slot1
  → Envoie GO au prochain
```

---

## 🔌 Architecture Réseau

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Host (PC)                        │
│  ┌─────────────────┐    ┌─────────────────────────────────┐│
│  │   Mosquitto     │◄───│       Node-RED                  ││
│  │   Port 1883     │    │       Port 1880                 ││
│  └────────▲────────┘    └─────────────────────────────────┘│
│           │                                                 │
└───────────┼─────────────────────────────────────────────────┘
            │
   ┌────────┴────────┐
   │  Réseau WiFi    │
   └────────┬────────┘
            │
    ┌───────┴───────┐
    │   EV3 Robot   │
    │  (Client MQTT)│
    └───────────────┘
```

---

## 🧪 Test avec Mosquitto CLI

```bash
# Terminal 1: Écouter tous les messages
mosquitto_sub -h localhost -p 1883 -t '#' -v

# Terminal 2: Simuler robot arrive en zone
mosquitto_pub -h localhost -p 1883 -t 'intersection/status' \
  -m '{"id":"EV3_01","voie":"A","etape":1,"action":"run"}'

# Simuler robot à la ligne d'arrêt
mosquitto_pub -h localhost -p 1883 -t 'intersection/status' \
  -m '{"id":"EV3_01","voie":"A","etape":2,"action":"stop"}'

# Simuler robot sort
mosquitto_pub -h localhost -p 1883 -t 'intersection/status' \
  -m '{"id":"EV3_01","voie":"A","etape":3,"action":"run"}'
```

---

*Version: 2.0 - Multi-Mode*
*Dernière mise à jour: 2025-12-16*
