# 🤖 Code EV3 - Robot Mindstorms
## VA55 - UTBM

Ce répertoire contient le code Python pour les robots EV3 Mindstorms utilisant Pybricks.

---

## 📁 Structure

```
code_ev3/
├── main.py      # Programme principal du robot
├── config.py    # Configuration centralisée
└── README.md    # Cette documentation
```

---

## ⚙️ Configuration (`config.py`)

### Connexion MQTT

```python
BROKER_IP = "192.168.1.100"    # ⚠️ IP du PC avec Docker
BROKER_PORT = 1883
TOPIC_STATUS = "intersection/status"
TOPIC_COMMAND = "intersection/command"
```

> **Important:** Modifiez `BROKER_IP` selon votre réseau local.

### Identification

```python
ROBOT_ID = "R1"    # Nom unique (R1, R2, EV3_01, etc.)
VOIE = "A"         # Voie assignée: "A" ou "B"
```

### Capteurs

```python
WHITE_REFLECTION = 60      # Réflexion sur blanc
BLACK_REFLECTION = 10      # Réflexion sur noir
MIDDLE_REFLECTION = 40     # Point milieu pour le suivi de ligne
```

> **Calibration:** Placez le capteur sur le blanc/noir pour lire les valeurs et ajustez.

### PID - Suivi de Ligne

```python
KP = 1.2              # Gain proportionnel
KI = 0.1              # Gain intégral
KD = 0.001            # Gain dérivé
COMMAND_FACTOR = 0.5  # Atténuation de la commande
MAX_SUM_ERROR = 500   # Anti-windup
```

| Paramètre | Effet si trop grand | Effet si trop petit |
|-----------|--------------------|--------------------|
| `KP` | Oscillations | Réaction lente |
| `KI` | Dépassement | Erreur résiduelle |
| `KD` | Sensibilité au bruit | Pas de stabilisation |

### Navigation

```python
BASE_SPEED = 100      # Vitesse en mm/s
LOOP_INTERVAL = 50    # Période de la boucle en ms
```

### Mode Peloton

```python
OBSTACLE_STOP_DISTANCE = 120   # Distance d'arrêt derrière un robot (mm)
```

---

## 🔄 Logique du Robot (`main.py`)

### Cycle de Fonctionnement

Le robot détecte **3 lignes rouges** et réagit à chacune :

```
START ──► [Suivi ligne] ──► LIGNE 1 ──► [Suivi ligne] ──► LIGNE 2 ──► [Attente GO] ──► LIGNE 3 ──► [Cycle terminé]
                               │                               │                           │
                               ▼                               ▼                           ▼
                          etape=1                         etape=2                     etape=3
                     marker_entry                    marker_stop                  marker_exit
```

### Détection de Ligne

```python
if color == Color.RED:
    compteur_lignes += 1
    # Traitement selon compteur_lignes
```

### Communication MQTT

#### Envoi de statut

```python
def publish(etape, cause, dist_us=9999):
    msg = json.dumps({
        "id": ROBOT_ID,
        "voie": VOIE,
        "etape": etape,
        "cause": cause,
        "dist_us": dist_us
    })
    client.publish(TOPIC_STATUS, msg)
```

#### Réception de commande

```python
def on_message(topic, msg):
    data = json.loads(msg)
    if data.get("target_id") == ROBOT_ID:
        if data.get("action") == "GO":
            permis_recu = True
```

### Attente du GO

```python
# À la ligne 2
if not permis_recu:
    publish(2, "marker_stop")
    while not permis_recu:
        mqtt.check()  # Vérifie les messages
        wait(50)
else:
    publish(2, "pass_through")  # Déjà autorisé
```

---

## 🚀 Déploiement

### 1. Préparer le Hub EV3

1. Installer Pybricks sur le hub
2. Connecter le hub au réseau WiFi

### 2. Transférer le code

```bash
# Via VS Code avec extension Pybricks
# Ou copie manuelle sur la carte SD
```

### 3. Configurer

Éditez `config.py` :
```python
BROKER_IP = "VOTRE_IP"
ROBOT_ID = "R1"  # Unique pour chaque robot
VOIE = "A"       # ou "B"
```

### 4. Lancer

Exécutez `main.py` sur le hub.

---

## 🔧 Dépannage

### Le robot ne se connecte pas au broker

1. Vérifiez que le broker est accessible: `ping BROKER_IP`
2. Vérifiez que le port 1883 est ouvert
3. Testez avec: `mosquitto_sub -h BROKER_IP -t '#'`

### Le robot oscille sur la ligne

Réduisez `KP` ou augmentez `KD` dans `config.py`.

### Le robot ne détecte pas les lignes rouges

1. Vérifiez l'éclairage ambiant
2. Recalibrez `WHITE_REFLECTION` et `BLACK_REFLECTION`
3. Ajustez la vitesse (`BASE_SPEED`)

### Le robot ne reçoit pas le GO

1. Vérifiez le mode dans Node-RED (dashboard)
2. Vérifiez que `ROBOT_ID` correspond
3. Regardez les logs Node-RED

---

## 📝 Exemple de Log

```
[14:30:01] Démarrage R1 sur voie A
[14:30:05] LIGNE 1 détectée - Entrée zone
[14:30:05] MQTT: etape=1 cause=marker_entry
[14:30:08] LIGNE 2 détectée - Arrêt
[14:30:08] MQTT: etape=2 cause=marker_stop
[14:30:08] Attente GO...
[14:30:09] GO REÇU!
[14:30:09] Traversée zone de conflit
[14:30:11] LIGNE 3 détectée - Sortie
[14:30:11] MQTT: etape=3 cause=marker_exit
[14:30:11] Cycle terminé
```

---

*Documentation EV3 - VA55 UTBM*
