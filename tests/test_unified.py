#!/usr/bin/env python3
"""
Test Simple - Mode Texte Uniquement
VA55 - UTBM

Un robot à la fois, séquence claire, pour vérifier les algorithmes.
"""

import asyncio
import json
import time
import argparse
from datetime import datetime

import paho.mqtt.client as mqtt

BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC_STATUS = "intersection/status"
TOPIC_COMMAND = "intersection/command"

# Couleurs
class C:
    RST = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    GRAY = "\033[90m"
    MAG = "\033[95m"


class SimpleRobot:
    """Robot simple avec comportement EV3 exact"""
    
    def __init__(self, name: str, voie: str, client: mqtt.Client):
        self.name = name
        self.voie = voie
        self.client = client
        self.permis_recu = False
        self.waiting = False
        self.finished = False
        self.success = False
    
    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        color = C.CYAN if self.voie == "A" else C.YELLOW
        print(f"{C.GRAY}[{ts}]{C.RST} {color}{C.BOLD}{self.name}{C.RST} {msg}")
    
    def publish(self, etape: int, cause: str):
        msg = {"id": self.name, "voie": self.voie, "etape": etape, "cause": cause, "dist_us": 9999}
        self.client.publish(TOPIC_STATUS, json.dumps(msg), qos=1)
        self.log(f"📤 Envoi: etape={etape} cause={cause}")
    
    def on_go(self):
        self.log(f"🟢 GO REÇU!")
        self.permis_recu = True
        self.waiting = False
    
    async def run(self, delay_before: float = 0.0, timeout: float = 30.0):
        if delay_before > 0:
            self.log(f"⏳ Attente {delay_before}s avant départ")
            await asyncio.sleep(delay_before)
        
        self.log("🚗 DÉPART")
        start = time.time()
        
        # Avancer vers LIGNE 1
        await asyncio.sleep(1.0)
        self.log("🔴 LIGNE 1 → Entrée zone")
        self.publish(1, "marker_entry")
        await asyncio.sleep(0.5)
        
        # Avancer vers LIGNE 2
        await asyncio.sleep(1.5)
        self.log("🔴 LIGNE 2 → Arrêt")
        
        if self.permis_recu:
            self.log("⚡ PASS-THROUGH (pré-autorisé)")
            self.publish(2, "pass_through")
        else:
            self.publish(2, "marker_stop")
            self.waiting = True
            self.log("🛑 ARRÊT - Attente GO...")
            
            while self.waiting:
                if time.time() - start > timeout:
                    self.log("❌ TIMEOUT!")
                    self.finished = True
                    return False
                await asyncio.sleep(0.1)
            
            self.log("🚗 GO reçu → Traverse")
        
        # Traverser + sortir
        await asyncio.sleep(1.0)
        self.log("🔴 LIGNE 3 → Sortie")
        self.publish(3, "marker_exit")
        
        self.log("✅ TERMINÉ")
        self.finished = True
        self.success = True
        return True


class TestRunner:
    def __init__(self, mode: str, num_robots: int = 4):
        self.mode = mode
        self.num_robots = num_robots
        self.client = mqtt.Client(
            client_id=f"test_{int(time.time())}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        self.robots = {}
        self.connected = False
        
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
    
    def _on_connect(self, client, userdata, flags, rc, props=None):
        if rc == 0:
            print(f"{C.GREEN}[MQTT] Connecté{C.RST}")
            client.subscribe(TOPIC_COMMAND, qos=1)
            self.connected = True
    
    def _on_message(self, client, userdata, msg):
        try:
            p = json.loads(msg.payload.decode())
            tid = p.get("target_id")
            act = p.get("action")
            
            print(f"{C.MAG}[BROKER→] {tid}: {act}{C.RST}")
            
            if tid in self.robots and act == "GO":
                self.robots[tid].on_go()
        except Exception as e:
            print(f"[ERR] {e}")
    
    async def run_sequential(self):
        """Exécute les robots UN PAR UN pour voir clairement"""
        for name, robot in self.robots.items():
            print(f"\n{C.CYAN}{'─'*50}")
            print(f"  Robot {name} - Voie {robot.voie}")
            print(f"{'─'*50}{C.RST}\n")
            
            await robot.run(timeout=15.0)
            await asyncio.sleep(0.5)
    
    async def run_parallel(self, stagger: float = 2.0):
        """Exécute les robots en parallèle avec décalage"""
        tasks = []
        for i, (name, robot) in enumerate(self.robots.items()):
            tasks.append(robot.run(delay_before=i * stagger, timeout=30.0))
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    def run(self, parallel: bool = True, stagger: float = 2.0):
        print(f"\n{C.MAG}{'═'*60}")
        print(f"  TEST MODE: {self.mode}")
        print(f"  Robots: {self.num_robots}")
        print(f"  Mode: {'Parallèle' if parallel else 'Séquentiel'}")
        print(f"{'═'*60}{C.RST}\n")
        
        self.client.connect(BROKER_HOST, BROKER_PORT, 60)
        self.client.loop_start()
        
        for _ in range(30):
            if self.connected:
                break
            time.sleep(0.1)
        
        if not self.connected:
            print(f"{C.RED}Erreur MQTT{C.RST}")
            return False
        
        # Créer robots
        half = self.num_robots // 2
        for i in range(half + self.num_robots % 2):
            name = f"R{i+1}_A"
            self.robots[name] = SimpleRobot(name, "A", self.client)
        for i in range(half):
            name = f"R{i+1}_B"
            self.robots[name] = SimpleRobot(name, "B", self.client)
        
        print("Robots:")
        for name, r in self.robots.items():
            color = C.CYAN if r.voie == "A" else C.YELLOW
            print(f"  {color}● {name}{C.RST} (Voie {r.voie})")
        print()
        
        print(f"{C.YELLOW}⚠️  Mode {self.mode} doit être sélectionné dans Node-RED!{C.RST}\n")
        
        # Exécution
        if parallel:
            asyncio.run(self.run_parallel(stagger))
        else:
            asyncio.run(self.run_sequential())
        
        self.client.loop_stop()
        self.client.disconnect()
        
        # Résultats
        ok = sum(1 for r in self.robots.values() if r.success)
        print(f"\n{C.MAG}{'═'*60}")
        print(f"  RÉSULTATS: {ok}/{self.num_robots}")
        print(f"{'═'*60}{C.RST}\n")
        
        for name, r in self.robots.items():
            status = f"{C.GREEN}✅{C.RST}" if r.success else f"{C.RED}❌{C.RST}"
            color = C.CYAN if r.voie == "A" else C.YELLOW
            print(f"  {status} {color}{name}{C.RST}")
        
        print()
        return ok == self.num_robots


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["FEU", "FIFO", "PELOTON"], default="FIFO")
    parser.add_argument("--robots", type=int, default=4)
    parser.add_argument("--sequential", action="store_true", help="Exécuter un robot à la fois")
    parser.add_argument("--stagger", type=float, default=2.0, help="Décalage entre robots (parallèle)")
    args = parser.parse_args()
    
    print(f"\n{C.CYAN}╔{'═'*58}╗")
    print(f"║{'TEST VA55 - MODE TEXTE':^58}║")
    print(f"╚{'═'*58}╝{C.RST}")
    
    runner = TestRunner(args.mode, args.robots)
    success = runner.run(parallel=not args.sequential, stagger=args.stagger)
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
