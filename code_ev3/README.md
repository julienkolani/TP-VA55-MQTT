# Code EV3 - Robot Intersection MQTT

## Fichiers

| Fichier | Description |
|---------|-------------|
| `main.py` | Programme principal (boucle événementielle) |
| `config.py` | Configuration réseau et robot |
| `sensors.py` | Gestion capteurs avec auto-calibration |
| `mqtt_client.py` | Client MQTT simplifié |

## Configuration

Éditer `config.py`:

```python
# Réseau
BROKER_IP = "192.168.0.100"  # IP du PC avec Docker
BROKER_PORT = 1883

# Robot
ROBOT_ID = "EV3_01"          # ID unique
VOIE = "A"                   # Voie A ou B
```

## Installation sur EV3

1. Connecter l'EV3 en USB ou WiFi
2. Copier tout le dossier `code_ev3/` vers `/home/robot/`
3. Lancer via VS Code EV3 Extension ou SSH

## Auto-Calibration des Ports

Les ports des capteurs et moteurs sont détectés automatiquement au démarrage.
Aucune configuration manuelle nécessaire !

## Logging Console

Le programme affiche en temps réel:
- Timestamp de chaque événement
- Valeurs des capteurs (couleur, réflexion, distance)
- Transitions de zone (transitions couleur)
- Messages MQTT envoyés/reçus

Exemple:
```
[00:00:00] === DEMARRAGE ===
[00:00:01] Capteurs: Color=BLACK Refl=45 Dist=250mm
[00:00:02] *** TRANSITION: BLACK -> RED ***
[00:00:02] >>> ETAPE 1: Entree zone de stockage
[00:00:02] [MQTT] >>> Envoi: etape=1 action=run
```

## Comportement

1. **Détection 1er RED** → Envoie `etape=1`
2. **Détection 2ème RED** → Envoie `etape=2`, attend GO
3. **Réception GO** → Démarre, envoie `etape=2 action=run`
4. **Détection 3ème RED** → Envoie `etape=3`, reset

## Commandes Supportées

| Commande | Description |
|----------|-------------|
| `GO` | Autorise le passage |
| `STOP` | Reste en attente |
| `ADVANCE` | Avance vers slot 2 (mode Peloton) |
