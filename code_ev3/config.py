#!/usr/bin/env pybricks-micropython
"""
Configuration Robot EV3 - VA55 UTBM
"""

# =============================================================================
# RESEAU MQTT
# =============================================================================

BROKER_IP = "192.168.0.103"   # A METTRE A JOUR AVEC TON IP NODE-RED
BROKER_PORT = 1883
TOPIC_STATUS = "intersection/status"    # Robot -> Controleur
TOPIC_COMMAND = "intersection/command"  # Controleur -> Robot

# =============================================================================
# IDENTIFICATION ROBOT
# =============================================================================

ROBOT_ID = "R1"      # R1, R2, etc.
VOIE = "A"           # A ou B

# =============================================================================
# PHYSIQUE
# =============================================================================

WHEEL_DIAMETER = 55.5  # mm
AXLE_TRACK = 104       # mm

# =============================================================================
# CAPTEURS
# =============================================================================

WHITE_REFLECTION = 60
BLACK_REFLECTION = 10
MIDDLE_REFLECTION = 40  # Ajuster selon luminosite
COLOR_DEBOUNCE_MS = 200 # Plus utilise, remplace par logique sur_ligne

# =============================================================================
# PID
# =============================================================================

KP = 1.2
KI = 0.1
KD = 0.001
COMMAND_FACTOR = 0.5
MAX_SUM_ERROR = 500

# =============================================================================
# NAVIGATION
# =============================================================================

BASE_SPEED = 100      # mm/s (Vitesse moderee pour bien lire les lignes)
LOOP_INTERVAL = 50   # ms

# Distance a laquelle on considere qu'on colle le robot de devant (Peloton)
OBSTACLE_STOP_DISTANCE = 120   # mm (12cm)

DEBUG_INTERVAL = 1000
