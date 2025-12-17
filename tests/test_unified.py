#!/usr/bin/env python3
"""
Test Unifie - Simulation Async de Robots EV3
VA55 - UTBM

Usage:
    python test_unified.py --mode FIFO
    python test_unified.py --mode FEU --robots 4 --wait 2
"""

import asyncio
import argparse
import json
import time
import random
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

import paho.mqtt.client as mqtt

# =============================================================================
# CONFIGURATION
# =============================================================================

BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC_STATUS = "intersection/status"
TOPIC_COMMAND = "intersection/command"

# Couleurs ANSI
class C:
    RST = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAG = "\033[95m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"

# =============================================================================
# ROBOT SIMULE
# =============================================================================

@dataclass
class SimRobot:
    robot_id: str
    voie: str
    client: mqtt.Client
    speed: float = 1.0
    wait_time: float = 0.0  # Temps d'attente supplementaire
    
    waiting: bool = False
    got_go: bool = False
    finished: bool = False
    success: bool = False
    
    def _color(self):
        return C.CYAN if self.voie == "A" else C.YELLOW
    
    def log(self, emoji, msg, bold=False):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        style = C.BOLD if bold else ""
        print(C.GRAY + "[" + ts + "]" + C.RST + " " + 
              self._color() + style + self.robot_id + C.RST + " " + 
              emoji + " " + msg)
    
    def publish(self, etape, action):
        msg = {"id": self.robot_id, "voie": self.voie, "etape": etape, "action": action}
        self.client.publish(TOPIC_STATUS, json.dumps(msg), qos=1)
        self.log("📤", "etape=" + str(etape) + " action=" + action)
    
    def on_cmd(self, action):
        if action == "GO":
            self.log("🟢", "GO", bold=True)
            self.waiting = False
            self.got_go = True
        elif action == "STOP":
            self.log("🛑", "STOP")
    
    async def delay(self, base):
        d = (base / self.speed) * random.uniform(0.9, 1.1)
        await asyncio.sleep(d)
    
    async def run(self, base_delay=0.5, timeout=15.0):
        self.log("🚗", "Demarrage")
        
        # Attente initiale configurable
        if self.wait_time > 0:
            self.log("⏳", "Attente " + str(self.wait_time) + "s avant depart")
            await asyncio.sleep(self.wait_time)
        
        # RED #1 - Zone stockage
        await self.delay(base_delay)
        self.log("🔴", "RED #1 -> Zone stockage")
        self.publish(1, "run")
        await self.delay(base_delay * 0.5)
        
        # RED #2 - Ligne arret
        await self.delay(base_delay)
        self.log("🔴", "RED #2 -> Ligne arret")
        self.waiting = True
        self.got_go = False
        self.publish(2, "stop")
        self.log("⏳", "Attente autorisation...")
        
        # Attente GO
        start = time.time()
        while self.waiting:
            if (time.time() - start) > timeout:
                self.log("⚠️", "TIMEOUT!", bold=True)
                self.finished = True
                return False
            await asyncio.sleep(0.05)
        
        # Traversee
        self.log("🚗", "Traverse intersection")
        self.publish(2, "run")
        await self.delay(base_delay)
        
        # RED #3 - Sortie
        self.log("🔴", "RED #3 -> Sortie")
        self.publish(3, "run")
        self.log("✅", "Termine!", bold=True)
        
        self.finished = True
        self.success = True
        return True


# =============================================================================
# TEST RUNNER
# =============================================================================

class TestRunner:
    def __init__(self, mode, num_robots=8, wait_per_robot=0.0):
        self.mode = mode
        self.num_robots = num_robots
        self.wait_per_robot = wait_per_robot
        
        self.client = mqtt.Client(
            client_id="test_" + str(int(time.time())),
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        self.robots = {}
        self.connected = False
        
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
    
    def _on_connect(self, client, userdata, flags, rc, props=None):
        if rc == 0:
            print(C.GREEN + "[MQTT] Connecte" + C.RST)
            client.subscribe(TOPIC_COMMAND, qos=1)
            self.connected = True
    
    def _on_message(self, client, userdata, msg):
        try:
            p = json.loads(msg.payload.decode())
            tid = p.get("target_id")
            act = p.get("action")
            if tid in self.robots:
                self.robots[tid].on_cmd(act)
            elif tid == "ALL":
                for r in self.robots.values():
                    r.on_cmd(act)
        except:
            pass
    
    def _header(self, text):
        print("\n" + C.MAG + "=" * 60)
        print("  " + text)
        print("=" * 60 + C.RST + "\n")
    
    async def run(self, base_delay=0.5, stagger=0.5, timeout=15.0):
        self._header("TEST MODE: " + self.mode)
        print("  Broker: " + BROKER_HOST + ":" + str(BROKER_PORT))
        print("  Robots: " + str(self.num_robots))
        print("  Wait/robot: " + str(self.wait_per_robot) + "s")
        print()
        
        # Connexion
        try:
            self.client.connect(BROKER_HOST, BROKER_PORT, 60)
            self.client.loop_start()
        except Exception as e:
            print(C.RED + "Erreur connexion: " + str(e) + C.RST)
            return False
        
        for _ in range(50):
            if self.connected:
                break
            await asyncio.sleep(0.1)
        
        if not self.connected:
            print(C.RED + "Timeout connexion MQTT" + C.RST)
            return False
        
        # Creer robots
        half = self.num_robots // 2
        configs = []
        for i in range(half):
            configs.append(("EV3_" + str(i+1).zfill(2), "A", random.uniform(0.7, 1.3)))
        for i in range(half):
            configs.append(("EV3_" + str(half+i+1).zfill(2), "B", random.uniform(0.7, 1.3)))
        
        for rid, voie, spd in configs:
            self.robots[rid] = SimRobot(rid, voie, self.client, spd, self.wait_per_robot)
        
        print("Robots:")
        for rid, voie, spd in configs:
            bar = "🟢" if spd > 1.0 else "🟡" if spd > 0.85 else "🔴"
            print("  " + bar + " " + rid + " (Voie " + voie + ") " + str(round(spd, 2)) + "x")
        print()
        
        self._header("SIMULATION")
        
        # Lancer robots
        tasks = []
        for i, (rid, _, _) in enumerate(configs):
            robot = self.robots[rid]
            
            async def run_robot(r, delay):
                await asyncio.sleep(delay)
                await r.run(base_delay, timeout)
            
            tasks.append(run_robot(robot, i * stagger))
        
        await asyncio.gather(*tasks)
        
        self.client.loop_stop()
        self.client.disconnect()
        
        # Resultats
        self._header("RESULTATS")
        ok = sum(1 for r in self.robots.values() if r.success)
        ko = sum(1 for r in self.robots.values() if not r.success)
        
        print("  ✅ Reussis:  " + str(ok) + "/" + str(self.num_robots))
        print("  ⚠️ Timeouts: " + str(ko) + "/" + str(self.num_robots))
        print()
        
        if ko == 0:
            print(C.GREEN + C.BOLD + "  ✅ TEST REUSSI" + C.RST)
        else:
            print(C.RED + C.BOLD + "  ❌ TEST ECHOUE" + C.RST)
        print()
        
        return ko == 0


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Test intersection VA55")
    parser.add_argument("--mode", choices=["FEU", "FIFO"], default="FIFO")
    parser.add_argument("--robots", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--delay", type=float, default=0.5, help="Delai base entre actions")
    parser.add_argument("--stagger", type=float, default=0.5, help="Decalage entre robots")
    parser.add_argument("--wait", type=float, default=0.0, help="Attente avant depart (pour voir dashboard)")
    
    args = parser.parse_args()
    
    print("\n" + C.CYAN + "#" * 60)
    print("#  TEST UNIFIE VA55")
    print("#  Mode: " + args.mode)
    print("#" * 60 + C.RST)
    
    print("\n" + C.YELLOW + "IMPORTANT:" + C.RST)
    print("  1. docker compose up -d")
    print("  2. Selectionnez mode " + args.mode + " dans http://localhost:1880/ui")
    print()
    
    runner = TestRunner(args.mode, args.robots, args.wait)
    success = asyncio.run(runner.run(args.delay, args.stagger, args.timeout))
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
