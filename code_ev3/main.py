#!/usr/bin/env pybricks-micropython
"""
Robot EV3 - Intersection Cooperative VA55
UTBM - Master VASA

Utilise l'auto-detection des ports pour moteurs et capteurs.
Tous les parametres sont dans config.py.
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
    MIDDLE_REFLECTION, COLOR_DEBOUNCE_MS,
    KP, KI, KD, COMMAND_FACTOR, MAX_SUM_ERROR,
    BASE_SPEED, LOOP_INTERVAL,
    OBSTACLE_STOP_DISTANCE, OBSTACLE_SLOW_DISTANCE, OBSTACLE_SLOW_FACTOR,
    DEBUG_INTERVAL
)

# MQTT (optionnel)
try:
    from umqtt.robust import MQTTClient
    MQTT_AVAILABLE = True
except ImportError:
    MQTT_AVAILABLE = False
    print("[WARN] umqtt non disponible")

# =============================================================================
# AUTO-DETECTION DES PORTS
# =============================================================================

SENSOR_PORTS = [Port.S1, Port.S2, Port.S3, Port.S4]
MOTOR_PORTS = [Port.A, Port.B, Port.C, Port.D]


def auto_detect_color_sensor():
    """Detecte automatiquement le capteur couleur."""
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
    """Detecte automatiquement le capteur ultrason."""
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
    """Detecte automatiquement les moteurs."""
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
# CLASSE LOGGER
# =============================================================================

class RobotLogger:
    """Logging avec timestamps et emojis ASCII."""
    
    def __init__(self, robot_id):
        self.robot_id = robot_id
        self.sw = StopWatch()
        self.sw.reset()
    
    def _zfill(self, val, width):
        """Zero-fill compatible with MicroPython."""
        s = str(val)
        while len(s) < width:
            s = "0" + s
        return s
    
    def _ts(self):
        ms = self.sw.time()
        m = ms // 60000
        s = (ms // 1000) % 60
        r = ms % 1000
        return str(m) + ":" + self._zfill(s, 2) + "." + self._zfill(r, 3)
    
    def log(self, tag, msg):
        print("[" + self._ts() + "] " + self.robot_id + " " + tag + " " + msg)
    
    def red(self, zone):
        self.log("[RED]", "Detecte -> " + zone)
    
    def send(self, etape, action):
        self.log("[>>>]", "etape=" + str(etape) + " action=" + action)
    
    def recv(self, action):
        tag = "[GO!]" if action == "GO" else "[STP]" if action == "STOP" else "[<<<]"
        self.log(tag, "Recu: " + action)
    
    def wait_auth(self):
        self.log("[...]", "Attente autorisation")
    
    def ok(self, msg=""):
        self.log("[OK!]", msg if msg else "OK")
    
    def warn(self, msg):
        self.log("[!!!]", msg)
    
    def pid(self, refl, err, cmd, spd):
        self.log("[PID]", "r=" + str(refl) + " e=" + str(int(err)) + " c=" + str(int(cmd)) + " s=" + str(int(spd)))


# =============================================================================
# CLASSE PID
# =============================================================================

class PIDController:
    """Controleur PID pour suivi de ligne."""
    
    def __init__(self, kp, ki, kd, target, dt_ms, cmd_factor=1.0, max_sum=1000):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.target = target
        self.dt = dt_ms / 1000.0
        self.cmd_factor = cmd_factor
        self.max_sum = max_sum
        self.sum_err = 0
        self.last_err = 0
    
    def compute(self, val):
        """Calcule la commande de rotation."""
        err = val - self.target
        
        # Integral + anti-windup
        self.sum_err += err
        if self.sum_err > self.max_sum:
            self.sum_err = self.max_sum
        elif self.sum_err < -self.max_sum:
            self.sum_err = -self.max_sum
        
        # Derivee
        deriv = (err - self.last_err) / self.dt
        
        # PID
        cmd = self.kp * err + self.ki * self.sum_err + self.kd * deriv
        cmd = cmd * self.cmd_factor
        
        self.last_err = err
        return cmd
    
    def get_error(self):
        return self.last_err


# =============================================================================
# CLASSE MQTT
# =============================================================================

class SimpleMQTT:
    """Client MQTT simplifie."""
    
    def __init__(self, robot_id, voie, broker, port, topic_st, topic_cmd, log):
        self.robot_id = robot_id
        self.voie = voie
        self.topic_st = topic_st
        self.topic_cmd = topic_cmd
        self.log = log
        self.client = None
        self.connected = False
        self.last_cmd = None
        
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
                log.warn("MQTT: " + str(e))
    
    def _on_msg(self, topic, msg):
        try:
            p = msg.decode()
            if '"target_id"' in p and '"action"' in p:
                # Parse target_id
                i = p.find('"target_id"') + 13
                j = p.find('"', i + 1)
                tid = p[i:j]
                # Parse action
                i = p.find('"action"') + 10
                j = p.find('"', i + 1)
                act = p[i:j]
                if tid == self.robot_id or tid == "ALL":
                    self.last_cmd = act
                    self.log.recv(act)
        except:
            pass
    
    def publish(self, etape, action):
        if not self.connected:
            return
        msg = '{"id":"' + self.robot_id + '","voie":"' + self.voie + '","etape":' + str(etape) + ',"action":"' + action + '"}'
        try:
            self.client.publish(self.topic_st, msg)
            self.log.send(etape, action)
        except:
            pass
    
    def check(self):
        if self.connected:
            try:
                self.client.check_msg()
            except:
                pass
    
    def get_cmd(self):
        c = self.last_cmd
        self.last_cmd = None
        return c
    
    def close(self):
        if self.connected:
            try:
                self.client.disconnect()
            except:
                pass


# =============================================================================
# PROGRAMME PRINCIPAL
# =============================================================================

def main():
    ev3 = EV3Brick()
    ev3.speaker.beep()
    
    log = RobotLogger(ROBOT_ID)
    log.log("[SYS]", "Demarrage " + ROBOT_ID + " voie " + VOIE)
    
    # Auto-detection
    log.log("[SYS]", "Detection des ports...")
    color_sensor, _ = auto_detect_color_sensor()
    ultrasonic, _ = auto_detect_ultrasonic()
    left_motor, right_motor, _, _ = auto_detect_motors()
    
    # DriveBase
    robot = DriveBase(left_motor, right_motor, WHEEL_DIAMETER, AXLE_TRACK)
    
    # PID
    pid = PIDController(KP, KI, KD, MIDDLE_REFLECTION, LOOP_INTERVAL, COMMAND_FACTOR, MAX_SUM_ERROR)
    
    # MQTT
    mqtt = SimpleMQTT(ROBOT_ID, VOIE, BROKER_IP, BROKER_PORT, TOPIC_STATUS, TOPIC_COMMAND, log)
    
    # Etat
    sw = StopWatch()
    sw.reset()
    etape = 0
    wait_go = False
    got_go = False
    running = True
    dbg_cnt = 0
    last_color = None
    last_color_time = 0
    
    log.log("[SYS]", "Pret!")
    
    while running:
        t = sw.time()
        
        # Capteurs
        refl = color_sensor.reflection()
        dist = ultrasonic.distance() if ultrasonic else 9999
        color = color_sensor.color()
        
        # Detection transition couleur (debounce)
        if color != last_color and (t - last_color_time) > COLOR_DEBOUNCE_MS:
            if color == Color.RED:
                if etape == 0:
                    etape = 1
                    log.red("Zone stockage")
                    mqtt.publish(1, "run")
                elif etape == 1:
                    etape = 2
                    wait_go = True
                    got_go = False
                    log.red("Ligne arret")
                    mqtt.publish(2, "stop")
                    log.wait_auth()
                elif etape == 2 and got_go:
                    etape = 3
                    log.red("Sortie")
                    mqtt.publish(3, "run")
                    log.ok("Intersection traversee!")
                    etape = 0
                    got_go = False
            last_color = color
            last_color_time = t
        
        # MQTT
        mqtt.check()
        cmd = mqtt.get_cmd()
        if cmd == "GO":
            wait_go = False
            got_go = True
        elif cmd == "STOP":
            wait_go = True
        
        # PID
        turn = pid.compute(refl)
        
        # Vitesse
        if wait_go:
            spd = 0
        elif dist <= OBSTACLE_STOP_DISTANCE:
            spd = 0
        else:
            spd = int(BASE_SPEED)
        
        # Moteurs
        robot.drive(spd, turn)
        
        # Debug
        dbg_cnt += LOOP_INTERVAL
        if dbg_cnt >= DEBUG_INTERVAL:
            dbg_cnt = 0
            log.pid(refl, pid.get_error(), turn, spd)
        
        # Arret
        if Button.CENTER in ev3.buttons.pressed():
            running = False
            log.log("[SYS]", "Arret utilisateur")
        
        wait(LOOP_INTERVAL)
    
    robot.stop()
    mqtt.close()
    log.log("[SYS]", "Fin")
    ev3.speaker.beep()


if __name__ == "__main__":
    main()
