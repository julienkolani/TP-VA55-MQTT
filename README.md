# 🚦 VA55 - Contrôle d'Intersection Coopératif
## UTBM - Master VASA - TP MQTT

Système de gestion d'intersection pour robots EV3 Mindstorms utilisant MQTT et Node-RED avec 3 algorithmes de contrôle : **FEU**, **FIFO**, et **PELOTON**.

---

## 📋 Table des Matières

- [Architecture](#-architecture)
- [Lancement Rapide](#-lancement-rapide)
- [Structure du Projet](#-structure-du-projet)
- [Algorithmes](#-algorithmes)
- [Documentation Détaillée](#-documentation-détaillée)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SYSTÈME VA55                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌──────────────┐       ┌──────────────┐      ┌──────────────┐│
│   │   Robot EV3  │ MQTT  │   Mosquitto  │ MQTT │   Node-RED   ││
│   │   (Pybricks) │◄─────►│    Broker    │◄────►│  Controller  ││
│   │     ×N       │       │   :1883      │      │    :1880     ││
│   └──────────────┘       └──────────────┘      └──────────────┘│
│         │                                             │         │
│         │                                             │         │
│         ▼                                             ▼         │
│   ┌──────────────┐                          ┌────────────────┐ │
│   │   Piste      │                          │   Dashboard    │ │
│   │   en 8       │                          │   Web UI       │ │
│   │              │                          │ localhost:1880 │ │
│   └──────────────┘                          └────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Flux de Communication

```
Robot ──► intersection/status ──► Node-RED
               │
               └──► Traitement algorithme (FEU/FIFO/PELOTON)
                           │
Node-RED ◄── intersection/command ◄──┘
   │
   └──► Robot (GO/STOP)
```

---

## 🚀 Lancement Rapide

### Prérequis

- **Docker** & **Docker Compose**
- **Python 3.8+** avec `paho-mqtt`
- **Pybricks** (pour le code EV3)

### 1. Démarrer les Services

```bash
cd TP_MQTT

# Lancer les conteneurs
docker compose up -d

# Vérifier le statut
docker compose ps
```

### 2. Accéder au Dashboard

Ouvrez http://localhost:1880/ui et sélectionnez le mode souhaité.

### 3. Lancer un Test

```bash
cd tests

# Test mode FIFO
python test_unified.py --mode FIFO

# Test mode FEU
python test_unified.py --mode FEU

# Test mode PELOTON
python test_unified.py --mode PELOTON
```

### 4. Arrêter

```bash
docker compose down
```

---

## 📂 Structure du Projet

```
TP_MQTT/
├── 📄 docker-compose.yml     # Configuration Docker
├── 📄 README.md              # ← Vous êtes ici
├── 📄 protocol.md            # Protocole MQTT détaillé
│
├── 📁 code_ev3/              # Code robot EV3
│   ├── main.py               # Logique principale
│   ├── config.py             # Configuration
│   └── README.md             # Documentation EV3
│
├── 📁 nodered/               # Configuration Node-RED
│   ├── flows.json            # Flows et logique
│   └── README.md             # Documentation Node-RED
│
├── 📁 mosquitto/             # Configuration MQTT
│   ├── mosquitto.conf        # Config broker
│   └── README.md             # Documentation Mosquitto
│
└── 📁 tests/                 # Tests de simulation
    ├── test_unified.py       # Simulateur de robots
    └── README.md             # Documentation tests
```

---

## 🔄 Algorithmes

### 🚦 1. FEU (Feu Tricolore)

Alternance temporelle automatique des feux.

| Phase | Feu A | Feu B | Durée |
|-------|-------|-------|-------|
| 0 | 🟢 VERT | 🔴 ROUGE | 10s |
| 1 | 🔴 ROUGE | 🔴 ROUGE | 3s |
| 2 | 🔴 ROUGE | 🟢 VERT | 10s |
| 3 | 🔴 ROUGE | 🔴 ROUGE | 3s |

**Principe:** Les robots de la voie verte passent, les autres attendent.

---

### 📋 2. FIFO (Premier Arrivé, Premier Servi)

File d'attente avec pré-réservation.

```
┌─────────────────────────────────────────────┐
│              SÉQUENCE FIFO                   │
├─────────────────────────────────────────────┤
│                                              │
│  etape=1 ──► Ajout queue ──► GO si premier  │
│                                              │
│  etape=2 ──► Sécurité ──► GO si autorisé    │
│                                              │
│  etape=3 ──► Retire queue ──► GO au suivant │
│                                              │
└─────────────────────────────────────────────┘
```

**Principe:** Le premier robot arrivé passe en premier. Pré-réservation possible dès l'étape 1.

---

### 🚗 3. PELOTON (Priorité par Distance)

Inférence de distance et priorité au leader.

```
┌─────────────────────────────────────────────┐
│            SÉQUENCE PELOTON                  │
├─────────────────────────────────────────────┤
│                                              │
│  1. Inférence de distance                   │
│     • obstacle → queue + 35cm               │
│     • marker_entry → 100 (loin)             │
│     • etape=2 → 0 (à la ligne)              │
│                                              │
│  2. Tri par distance croissante             │
│                                              │
│  3. GO au leader si distance=0 et LIBRE     │
│                                              │
└─────────────────────────────────────────────┘
```

**Principe:** Le robot le plus proche de l'intersection passe en priorité.

---

## 📚 Documentation Détaillée

| Document | Contenu |
|----------|---------|
| [📄 protocol.md](./protocol.md) | Protocole MQTT complet, formats des messages, séquences |
| [🤖 code_ev3/README.md](./code_ev3/README.md) | Configuration EV3, logique 3 étapes, PID, déploiement |
| [🎛️ nodered/README.md](./nodered/README.md) | Flows, état global, logique des 3 modes, personnalisation |
| [🦟 mosquitto/README.md](./mosquitto/README.md) | Configuration broker, tests CLI, monitoring |
| [🧪 tests/README.md](./tests/README.md) | Arguments, interprétation logs, extension des tests |

---

## 🔧 Configuration Rapide

### Robot EV3 (`code_ev3/config.py`)

```python
BROKER_IP = "192.168.1.100"  # ⚠️ À modifier
ROBOT_ID = "R1"              # Nom unique
VOIE = "A"                   # "A" ou "B"
```

### Node-RED

Le mode est sélectionné via le **Dashboard** (http://localhost:1880/ui).

---

## 🧪 Tests

```bash
# Test FIFO - 4 robots, décalage 2s
python tests/test_unified.py --mode FIFO

# Test FEU - 6 robots, décalage 3s
python tests/test_unified.py --mode FEU --robots 6 --stagger 3

# Test séquentiel (debug)
python tests/test_unified.py --mode PELOTON --sequential
```

### Résultat Attendu

```
════════════════════════════════════════════════════════════
  RÉSULTATS: 4/4
════════════════════════════════════════════════════════════

  ✅ R1_A
  ✅ R2_A
  ✅ R1_B
  ✅ R2_B
```

---

## 🐛 Dépannage

| Problème | Solution |
|----------|----------|
| Broker ne démarre pas | `docker compose logs mosquitto` |
| Dashboard inaccessible | `docker compose restart nodered` |
| Robot ne reçoit pas GO | Vérifier le mode dans le dashboard |
| Timeout sur les tests | Augmenter `--stagger` et `--timeout` |

---

## 👥 Auteurs

**VA55 - UTBM**  
Master VASA - Véhicules Autonomes et Systèmes Avancés

---

## 📜 Licence

Projet éducatif - UTBM 2025
