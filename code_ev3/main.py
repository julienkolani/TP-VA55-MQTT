#!/usr/bin/env pybricks-micropython
"""
Robot EV3 - Intersection Cooperative VA55 (Consensus 3 Marqueurs)
UTBM - Master VASA

Logique : Robot "Ignorant" avec sequenceur 3 etapes.
"""

from pybricks.hubs import EV3Brick
from pybricks.ev3devices import Motor, ColorSensor, UltrasonicSensor
from pybricks.parameters import Port, Button, Color
from pybricks.tools import wait, StopWatch
from pybricks.robotics import DriveBase
import time

# Configuration centralisee
from config import (
    BROKER_IP, BROKER_PORT, TOPIC_STATUS, TOPIC_COMMAND,
    ROBOT_ID, VOIE,
    WHEEL_DIAMETER, AXLE_TRACK,
    MIDDLE_REFLECTION,
    KP, KI, KD, COMMAND_FACTOR, MAX_SUM_ERROR,
    BASE_SPEED, LOOP_INTERVAL,
    OBSTACLE_STOP_DISTANCE, DEBUG_INTERVAL
)

# MQTT (optionnel)
try:
    from umqtt.robust import MQTTClient
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("[WARN] umqtt non disponible")

# =============================================================================
# AUTO-DETECTION DES PORTS (INCHANGE)
# =============================================================================

SENSOR_PORTS = [Port.S1, Port.S2, Port.S3, Port.S4]
MOTOR_PORTS = [Port.A, Port.B, Port.C, Port.D]

def auto_detect_color_sensor():
    for port in SENSOR_PORTS:
        try:
            sensor = ColorSensor(port)
            _ = sensor.reflection()
            print("[AUTO] Capteur Couleur sur", port)
            return sensor, port
        except:
            continue
    raise Exception("Pas de capteur couleur!")

def auto_detect_ultrasonic():
    for port in SENSOR_PORTS:
        try:
            sensor = UltrasonicSensor(port)
            _ = sensor.distance()
            print("[AUTO] Capteur Ultrason sur", port)
            return sensor, port
        except:
            continue
    print("[AUTO] Pas de capteur ultrason")
    return None, None

def auto_detect_motors():
    found = []
    for port in MOTOR_PORTS:
        try:
            motor = Motor(port)
            found.append((motor, port))
            print("[AUTO] Moteur sur", port)
        except:
            continue
    if len(found) < 2:
        raise Exception("Moins de 2 moteurs!")
    return found[0][0], found[1][0], found[0][1], found[1][1]

# =============================================================================
# CLASSE LOGGER (MISE A JOUR POUR LE NOUVEAU PROTOCOLE)
# =============================================================================

class RobotLogger:
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.sw = StopWatch()
        self.sw.reset()
    
    def _ts(self):
        ms = self.sw.time()
        return "{:02d}:{:02d}.{:03d}".format(ms // 60000, (ms // 1000) % 60, ms % 1000)
    
    def log(self, tag, msg):
        print("[" + self._ts() + "] " + tag + " " + msg)
    
    def event(self, etape, cause):
        self.log("[MQTT >>]", "Etape: " + str(etape) + " | Cause: " + cause)
    
    def recv(self, action):
        tag = "[GO!]" if action == "GO" else "[CMD]"
        self.log(tag, "Recu: " + action)

# =============================================================================
# CLASSE MQTT (MISE A JOUR PAYLOAD UNIVERSEL)
# =============================================================================

class SimpleMQTT:
    def __init__(self, robot_id, voie, broker, port, topic_st, topic_cmd, log):
        self.robot_id = robot_id
        self.voie = voie
        self.topic_st = topic_st
        self.log = log
        self.client = None
        self.connected = False
        self.permis_recu = False # Stocke l'autorisation
        
        if MQTT_AVAILABLE:
            try:
                cid = robot_id + "_" + str(int(time.time()) % 10000)
                self.client = MQTTClient(cid, broker, port=port)
                self.client.set_callback(self._on_msg)
                self.client.connect()
                self.client.subscribe(topic_cmd)
                self.connected = True
                log.log("[NET]", "Connecte " + broker)
            except Exception as e:
                log.log("[ERR]", "MQTT: " + str(e))
    
    def _on_msg(self, topic, msg):
        try:
            p = msg.decode()
            # Parsing manuel rudimentaire pour eviter erreurs JSON
            if '"target_id"' in p and '"action"' in p:
                # Extraction ID cible
                i = p.find('"target_id"') + 13
                j = p.find('"', i + 1)
                tid = p[i:j]
                
                # Extraction Action
                i = p.find('"action"') + 10
                j = p.find('"', i + 1)
                act = p[i:j]
                
                if tid == self.robot_id or tid == "ALL":
                    self.log.recv(act)
                    if act == "GO":
                        self.permis_recu = True
                    elif act == "RESET":
                        self.permis_recu = False
        except:
            pass
    
    def publish(self, etape, cause, dist_us=999):
        """Envoie le format universel JSON"""
        if not self.connected: return
        
        # Construction manuelle du JSON pour performance
        msg = '{"id":"' + self.robot_id + '",' + \
              '"voie":"' + self.voie + '",' + \
              '"etape":' + str(etape) + ',' + \
              '"cause":"' + cause + '",' + \
              '"dist_us":' + str(dist_us) + '}'
        try:
            self.client.publish(self.topic_st, msg)
            self.log.event(etape, cause)
        except:
            pass
    
    def check(self):
        if self.connected:
            try: self.client.check_msg()
            except: pass
    
    def reset_permis(self):
        self.permis_recu = False

    def has_permis(self):
        return self.permis_recu
    
    def close(self):
        if self.connected:
            try: self.client.disconnect()
            except: pass

# =============================================================================
# PID CONTROLLER (INCHANGE)
# =============================================================================

class PIDController:
    def __init__(self, kp, ki, kd, target, dt_ms, cmd_factor=1.0, max_sum=1000):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.target = target
        self.dt = dt_ms / 1000.0
        self.cmd_factor = cmd_factor
        self.max_sum = max_sum
        self.sum_err = 0
        self.last_err = 0
    
    def compute(self, val):
        err = val - self.target
        self.sum_err += err
        if self.sum_err > self.max_sum: self.sum_err = self.max_sum
        elif self.sum_err < -self.max_sum: self.sum_err = -self.max_sum
        deriv = (err - self.last_err) / self.dt
        cmd = (self.kp * err + self.ki * self.sum_err + self.kd * deriv) * self.cmd_factor
        self.last_err = err
        return cmd

# =============================================================================
# PROGRAMME PRINCIPAL
# =============================================================================

def main():
    ev3 = EV3Brick()
    ev3.speaker.beep()
    log = RobotLogger(ROBOT_ID)
    log.log("[INIT]", "Robot Ignorant 3-Etapes demarre")
    
    # 1. Hardware Setup
    color_sensor, _ = auto_detect_color_sensor()
    ultrasonic, _ = auto_detect_ultrasonic()
    left_motor, right_motor, _, _ = auto_detect_motors()
    robot = DriveBase(left_motor, right_motor, WHEEL_DIAMETER, AXLE_TRACK)
    pid = PIDController(KP, KI, KD, MIDDLE_REFLECTION, LOOP_INTERVAL, COMMAND_FACTOR, MAX_SUM_ERROR)
    mqtt = SimpleMQTT(ROBOT_ID, VOIE, BROKER_IP, BROKER_PORT, TOPIC_STATUS, TOPIC_COMMAND, log)
    
    # 2. Variables d'Etat (Sequencement)
    compteur_lignes = 0
    sur_ligne = False # Anti-rebond
    running = True
    
    log.log("[RDY]", "En attente de ligne...")
    
    while running:
        start_time = time.time()
        
        # --- LECTURE CAPTEURS ---
        reflection = color_sensor.reflection()
        color = color_sensor.color()
        # Si pas d'ultrason, on met une grande distance par defaut
        dist_us = ultrasonic.distance() if ultrasonic else 9999
        
        # --- LOGIQUE OBSTACLE (PELOTON) ---
        # Si on est dans la file (apres ligne 1, avant ligne 2) et qu'on colle qqun
        if compteur_lignes == 1 and dist_us < OBSTACLE_STOP_DISTANCE:
            robot.stop()
            log.log("[OBS]", "Obstacle detecte (" + str(dist_us) + "mm)")
            mqtt.publish(1, "obstacle", dist_us)
            
            # Attente active que l'obstacle s'eloigne
            while dist_us < (OBSTACLE_STOP_DISTANCE + 50): # Hysteresis +50mm
                if ultrasonic: dist_us = ultrasonic.distance()
                mqtt.check() # On continue d'ecouter MQTT au cas ou
                wait(100)
            
            log.log("[OBS]", "Voie libre, redemarrage")
            # On laisse le PID reprendre la main ensuite

        # --- LOGIQUE LIGNES (SEQUENCEUR) ---
        # Detection Rouge (Ton scotch orange)
        if color == Color.RED:
            if not sur_ligne:
                sur_ligne = True
                compteur_lignes += 1
                log.log("[DET]", "Ligne detectee -> Compteur = " + str(compteur_lignes))
                
                # --- ETAPE 1 : ENTREE ZONE ---
                if compteur_lignes == 1:
                    ev3.speaker.beep(500, 100)
                    mqtt.publish(1, "marker_entry", dist_us)
                    # On continue de rouler
                    
                # --- ETAPE 2 : LIGNE D'ARRET ---
                elif compteur_lignes == 2:
                    mqtt.check() # Derniere verif avant decision
                    
                    if mqtt.has_permis():
                        # CAS A : PASS-THROUGH (Permis deja la)
                        log.log("[PASS]", "Permis OK -> Passage direct")
                        ev3.speaker.beep(1000, 200)
                        mqtt.publish(2, "pass_through", dist_us)
                        # On ne s'arrete pas
                    else:
                        # CAS B : STOP & WAIT
                        robot.stop()
                        log.log("[STOP]", "Pas de permis -> Arret")
                        mqtt.publish(2, "marker_stop", dist_us)
                        
                        # Boucle bloquante d'attente
                        while not mqtt.has_permis():
                            mqtt.check()
                            wait(50)
                        
                        log.log("[GO]", "Permis recu -> Depart")
                        ev3.speaker.beep(1000, 200)
                        # Le robot redemarrera grace au PID a la prochaine iteration

                # --- ETAPE 3 : SORTIE ---
                elif compteur_lignes == 3:
                    mqtt.publish(3, "marker_exit", dist_us)
                    ev3.speaker.beep(500, 100)
                    log.log("[RST]", "Reset Cycle")
                    compteur_lignes = 0
                    mqtt.reset_permis()
        
        elif color != Color.RED:
             # On a quitte la ligne rouge, on re-arme la detection
             sur_ligne = False
        
        # --- SUIVI DE LIGNE (PID) ---
        # Le PID ne tourne que si on n'est pas bloque dans les boucles while ci-dessus
        turn = pid.compute(reflection)
        robot.drive(BASE_SPEED, turn)
        
        # --- DEBUG & MAINTENANCE ---
        mqtt.check()
        if Button.CENTER in ev3.buttons.pressed():
            running = False
        
        wait(LOOP_INTERVAL)

    # Fin du programme
    robot.stop()
    mqtt.close()
    log.log("[END]", "Programme termine")

if __name__ == "__main__":
    main()
