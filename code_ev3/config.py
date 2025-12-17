#!/usr/bin/env pybricks-micropython
"""
Configuration Robot EV3 - VA55 UTBM
"""

# =============================================================================
# RESEAU MQTT
# =============================================================================

BROKER_IP = "192.168.0.103"   # IP du PC avec Docker (Mosquitto)
BROKER_PORT = 1883            # Port MQTT standard
TOPIC_STATUS = "intersection/status"    # Robot -> Controleur
TOPIC_COMMAND = "intersection/command"  # Controleur -> Robot

# =============================================================================
# IDENTIFICATION ROBOT
# =============================================================================

ROBOT_ID = "EV3_01"  # ID unique du robot (changer pour chaque robot)
VOIE = "A"           # Voie d'approche: "A" ou "B"

# =============================================================================
# DIMENSIONS ROBOT
# =============================================================================

WHEEL_DIAMETER = 55.5  # Diametre des roues en mm
AXLE_TRACK = 104       # Distance entre roues en mm

# =============================================================================
# CALIBRATION COULEUR
# =============================================================================

WHITE_REFLECTION = 60   # Reflexion sur blanc (0-100)
BLACK_REFLECTION = 8   # Reflexion sur noir (0-100)
MIDDLE_REFLECTION = 40  # Consigne PID = (blanc+noir)/2
COLOR_DEBOUNCE_MS = 300 # Temps min entre 2 detections couleur

# =============================================================================
# PARAMETRES PID
# =============================================================================

KP = 1.2              # Proportionnel: reaction a l'erreur actuelle
KI = 0.1              # Integral: corrige erreurs persistantes
KD = 0.002            # Derive: amortit les oscillations
COMMAND_FACTOR = 0.75  # Facteur sur commande finale (0.5=plus doux, 2.0=agressif)
MAX_SUM_ERROR = 1000  # Limite anti-windup pour l'integral

# =============================================================================
# VITESSE
# =============================================================================

BASE_SPEED = 80      # Vitesse de croisiere en mm/s
LOOP_INTERVAL = 80    # Periode boucle principale en ms

# =============================================================================
# OBSTACLES
# =============================================================================

OBSTACLE_STOP_DISTANCE = 80   # Distance arret complet en mm
OBSTACLE_SLOW_DISTANCE = 200  # Distance ralentissement en mm
OBSTACLE_SLOW_FACTOR = 0.5    # Facteur vitesse (0.5 = moitie)

# =============================================================================
# DEBUG
# =============================================================================

DEBUG_INTERVAL = 1000  # Affichage PID toutes les X ms
ENABLE_DATALOG = False # Sauvegarde fichier (False = desactive)
