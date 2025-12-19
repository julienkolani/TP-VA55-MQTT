# 📡 Protocole MQTT - Intersection Coopérative
## VA55 - UTBM

Ce document définit le protocole de communication MQTT unifié pour le système d'intersection coopérative.

---

## 🔗 Topics

| Topic | Direction | QoS | Description |
|-------|-----------|-----|-------------|
| `intersection/status` | Robot → Contrôleur | 1 | État et événements du robot |
| `intersection/command` | Contrôleur → Robot | 1 | Commandes pour le robot |

---

## 📨 Format des Messages

### 1. Message Status (Robot → Contrôleur)

Envoyé par le robot à chaque événement clé.

```json
{
  "id": "R1",
  "voie": "A",
  "etape": 2,
  "cause": "marker_stop",
  "dist_us": 9999
}
```

#### Champs

| Champ | Type | Obligatoire | Description |
|-------|------|-------------|-------------|
| `id` | string | ✅ | Identifiant unique du robot (ex: "R1", "EV3_01") |
| `voie` | string | ✅ | Voie du robot: `"A"` ou `"B"` |
| `etape` | int | ✅ | Étape actuelle: 1, 2, ou 3 |
| `cause` | string | ✅ | Raison de l'événement (voir tableau ci-dessous) |
| `dist_us` | int | ❌ | Distance ultrason en mm (défaut: 9999) |

#### Valeurs de `etape`

| Étape | Position | Description |
|-------|----------|-------------|
| **1** | Ligne 1 | Entrée dans la zone de stockage |
| **2** | Ligne 2 | Arrivée à la ligne d'arrêt (avant conflit) |
| **3** | Ligne 3 | Sortie de la zone de conflit |

#### Valeurs de `cause`

| Cause | Étape | Description |
|-------|-------|-------------|
| `marker_entry` | 1 | Robot a détecté la ligne d'entrée |
| `obstacle` | 1 | Robot bloqué par un obstacle (mode PELOTON) |
| `marker_stop` | 2 | Robot s'arrête à la ligne (attend GO) |
| `pass_through` | 2 | Robot passe sans s'arrêter (GO déjà reçu) |
| `marker_exit` | 3 | Robot a quitté la zone de conflit |

---

### 2. Message Command (Contrôleur → Robot)

Envoyé par Node-RED pour contrôler un robot.

```json
{
  "target_id": "R1",
  "action": "GO"
}
```

#### Champs

| Champ | Type | Description |
|-------|------|-------------|
| `target_id` | string | ID du robot cible, ou `"ALL"` pour tous |
| `action` | string | Action à effectuer |

#### Actions Disponibles

| Action | Description |
|--------|-------------|
| `GO` | Autorisation de traverser la zone de conflit |
| `STOP` | Ordre d'arrêt immédiat |
| `RESET` | Réinitialisation du robot (annule le permis) |

---

## ⚡ Séquence Événementielle

Le robot envoie des messages **uniquement** lors d'événements spécifiques, pas en continu.

### Diagramme de Séquence

```
Robot                    Broker                   Node-RED
  │                        │                         │
  │  ─── Détection Ligne 1 ───                       │
  ├──────────────────────► │ ────────────────────────►
  │  {etape:1, cause:      │  Traitement             │
  │   marker_entry}        │                         │
  │                        │ ◄────────────────────────┤
  │ ◄──────────────────────┤  {action: GO}           │ (si FIFO libre)
  │                        │                         │
  │  ─── Détection Ligne 2 ───                       │
  ├──────────────────────► │ ────────────────────────►
  │  {etape:2, cause:      │  Traitement             │
  │   marker_stop}         │                         │
  │                        │ ◄────────────────────────┤
  │ ◄──────────────────────┤  {action: GO}           │ (si autorisé)
  │                        │                         │
  │  ─── Traverse zone ─── │                         │
  │                        │                         │
  │  ─── Détection Ligne 3 ───                       │
  ├──────────────────────► │ ────────────────────────►
  │  {etape:3, cause:      │  Libère intersection    │
  │   marker_exit}         │  → GO au suivant        │
  │                        │                         │
```

---

## 🎛️ Comportement par Mode

### Mode FEU (Feu Tricolore)

```
┌─────────────────────────────────────────────────────────┐
│                    LOGIQUE FEU                           │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Timer 1s] → Incrémente compteur                        │
│            → Si durée atteinte: change phase             │
│            → Si nouvelle phase VERT: GO aux robots       │
│               en attente sur cette voie                  │
│                                                          │
│  [etape=2] → Vérifie feu de la voie                     │
│           → Si VERT: GO immédiat                        │
│           → Si ROUGE: ajoute à file_attente (pas de GO) │
│                                                          │
│  [etape=3] → Ignoré (la sécurité est gérée par le      │
│              Rouge Intégral entre phases)                │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Phases:**
| Phase | Durée | Feu A | Feu B |
|-------|-------|-------|-------|
| 0 | 10s | 🟢 VERT | 🔴 ROUGE |
| 1 | 3s | 🔴 ROUGE | 🔴 ROUGE |
| 2 | 10s | 🔴 ROUGE | 🟢 VERT |
| 3 | 3s | 🔴 ROUGE | 🔴 ROUGE |

---

### Mode FIFO (Premier Arrivé, Premier Servi)

```
┌─────────────────────────────────────────────────────────┐
│                    LOGIQUE FIFO                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [etape=1] → Ajoute robot à la queue                    │
│           → Si LIBRE et premier: GO (pré-réservation)   │
│           → intersection = OCCUPE                        │
│                                                          │
│  [etape=2] → Vérifie queue et intersection              │
│           → Si LIBRE et premier: GO                     │
│           → Sinon: pas de réponse (robot attend)        │
│                                                          │
│  [etape=3] → Retire robot de la queue                   │
│           → intersection = LIBRE                         │
│           → Si queue non vide: GO au premier            │
│           → intersection = OCCUPE                        │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Pré-réservation:** Le robot peut recevoir GO dès l'étape 1, lui permettant un PASS-THROUGH à l'étape 2.

---

### Mode PELOTON (Inférence de Distance)

```
┌─────────────────────────────────────────────────────────┐
│                   LOGIQUE PELOTON                        │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  PHASE 1: INFÉRENCE DE DISTANCE                         │
│  ────────────────────────────────────────────────────── │
│  [etape=1, cause=obstacle]                              │
│     → distance = queue_voie + 35cm                      │
│                                                          │
│  [etape=1, cause=marker_entry]                          │
│     → distance = 100 (robot seul, loin)                 │
│                                                          │
│  [etape=2]                                              │
│     → distance = 0 (à la ligne d'arrêt)                 │
│     → reset queue_voie                                   │
│                                                          │
│  PHASE 2: TRI                                           │
│  ────────────────────────────────────────────────────── │
│  Trier tous les robots par distance croissante          │
│  Leader = robot avec distance la plus petite            │
│                                                          │
│  PHASE 3: DÉCISION                                      │
│  ────────────────────────────────────────────────────── │
│  Si LIBRE et leader.distance == 0:                      │
│     → GO au leader                                       │
│     → intersection = OCCUPE                              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 🧪 Tests Manuels

### Écouter tous les messages

```bash
mosquitto_sub -h localhost -p 1883 -t '#' -v
```

### Simuler un cycle complet

```bash
# Étape 1: Entrée
mosquitto_pub -h localhost -p 1883 -t 'intersection/status' \
  -m '{"id":"R1","voie":"A","etape":1,"cause":"marker_entry","dist_us":9999}'

# Attendre le GO...

# Étape 2: Ligne d'arrêt
mosquitto_pub -h localhost -p 1883 -t 'intersection/status' \
  -m '{"id":"R1","voie":"A","etape":2,"cause":"marker_stop","dist_us":9999}'

# Attendre le GO...

# Étape 3: Sortie
mosquitto_pub -h localhost -p 1883 -t 'intersection/status' \
  -m '{"id":"R1","voie":"A","etape":3,"cause":"marker_exit","dist_us":9999}'
```

### Envoyer une commande manuellement

```bash
mosquitto_pub -h localhost -p 1883 -t 'intersection/command' \
  -m '{"target_id":"R1","action":"GO"}'
```

---

## 🔌 Configuration Réseau

| Service | Hôte | Port | Protocole |
|---------|------|------|-----------|
| Broker MQTT | localhost | 1883 | TCP |
| WebSocket MQTT | localhost | 9001 | WS |
| Node-RED | localhost | 1880 | HTTP |
| Dashboard | localhost | 1880/ui | HTTP |

---

*Version: 3.0 - Protocole Unifié*  
*Dernière mise à jour: 2025-12-19*
