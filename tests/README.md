# 🧪 Tests - Simulation de Robots EV3
## VA55 - UTBM

Ce répertoire contient les scripts de test et de simulation pour valider le comportement du système.

---

## 📁 Structure

```
tests/
├── test_unified.py    # Simulateur principal
└── README.md          # Cette documentation
```

---

## 🚀 Utilisation Rapide

```bash
# Test mode FIFO (par défaut)
python test_unified.py --mode FIFO

# Test mode FEU
python test_unified.py --mode FEU

# Test mode PELOTON
python test_unified.py --mode PELOTON
```

---

## 📋 Arguments

| Argument | Défaut | Description |
|----------|--------|-------------|
| `--mode` | `FIFO` | Algorithme: `FIFO`, `FEU`, `PELOTON` |
| `--robots` | `4` | Nombre de robots à simuler |
| `--stagger` | `2.0` | Décalage entre les départs (secondes) |
| `--sequential` | `false` | Mode séquentiel (1 robot à la fois) |
| `--timeout` | `30.0` | Timeout par robot (secondes) |

### Exemples

```bash
# 6 robots avec décalage de 3 secondes
python test_unified.py --mode FIFO --robots 6 --stagger 3

# Mode séquentiel (debug)
python test_unified.py --mode FEU --sequential

# Timeout court
python test_unified.py --mode PELOTON --timeout 15

# 8 robots sur PELOTON
python test_unified.py --mode PELOTON --robots 8 --stagger 2.5
```

---

## 🔄 Fonctionnement

### Simulation d'un Robot

Chaque robot simulé (`SimpleRobot`) reproduit le comportement exact d'un EV3 :

```
┌─────────────────────────────────────────────────────────────┐
│                    CYCLE DU ROBOT SIMULÉ                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Délai initial (start_delay)                             │
│  2. Avance vers LIGNE 1 (1.0s)                              │
│  3. Publie: etape=1, cause=marker_entry                     │
│  4. Avance vers LIGNE 2 (1.5s)                              │
│  5. Si GO déjà reçu:                                        │
│        → Publie: etape=2, cause=pass_through                │
│     Sinon:                                                   │
│        → Publie: etape=2, cause=marker_stop                 │
│        → ATTENTE DU GO (boucle bloquante)                   │
│  6. Traverse zone de conflit (1.0s)                         │
│  7. Publie: etape=3, cause=marker_exit                      │
│  8. Terminé!                                                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Communication MQTT

- **Publication:** `intersection/status` (format JSON identique au robot réel)
- **Subscription:** `intersection/command` (écoute les GO/STOP)

---

## 📊 Interprétation des Logs

### Légende des Symboles

| Symbole | Signification |
|---------|---------------|
| 🚗 | Robot en mouvement |
| ⏳ | Attente (délai ou GO) |
| 🔴 | Détection de ligne |
| 📤 | Envoi MQTT |
| 🟢 | GO reçu |
| ⚡ | Pass-through |
| 🛑 | Arrêt |
| ✅ | Terminé avec succès |
| ❌ | Timeout/Échec |

### Exemple de Log

```
[14:41:28.156] R1_A 🚗 DÉPART
[14:41:29.157] R1_A 🔴 LIGNE 1 → Entrée zone
[14:41:29.157] R1_A 📤 Envoi: etape=1 cause=marker_entry
[BROKER→] R1_A: GO                         ← Commande du contrôleur
[14:41:29.200] R1_A 🟢 GO REÇU!
[14:41:31.158] R1_A 🔴 LIGNE 2 → Arrêt
[14:41:31.158] R1_A ⚡ PASS-THROUGH (pré-autorisé)  ← N'attend pas
[14:41:31.159] R1_A 📤 Envoi: etape=2 cause=pass_through
[14:41:32.161] R1_A 🔴 LIGNE 3 → Sortie
[14:41:32.162] R1_A 📤 Envoi: etape=3 cause=marker_exit
[14:41:32.162] R1_A ✅ TERMINÉ
```

### Log du Broker

Les messages `[BROKER→]` montrent les commandes envoyées par Node-RED :

```
[BROKER→] R1_A: GO     ← Node-RED autorise R1_A
[BROKER→] R2_A: GO     ← Node-RED autorise R2_A (après que R1_A soit sorti)
```

---

## 🎯 Validation des Algorithmes

### Test FIFO

✅ **Critères de succès:**
- Les robots passent dans l'ordre d'arrivée
- Un seul robot dans la zone de conflit à la fois
- Pré-réservation fonctionne (PASS-THROUGH)

### Test FEU

✅ **Critères de succès:**
- Les robots de la voie VERTE passent
- Les robots de la voie ROUGE attendent
- Le changement de phase débloque les robots en attente

### Test PELOTON

✅ **Critères de succès:**
- Le leader (plus proche) passe en premier
- Les robots maintiennent les distances
- La priorité est recalculée dynamiquement

---

## 🛠️ Extension

### Ajouter un Nouveau Scénario

```python
# Dans test_unified.py

class TestRunner:
    async def run_custom_scenario(self):
        """Scénario personnalisé"""
        # Créer robots avec timings spécifiques
        r1 = SimpleRobot("R1", "A", self.client)
        r2 = SimpleRobot("R2", "B", self.client)
        
        # Lancer en parallèle avec délais
        await asyncio.gather(
            r1.run(delay_before=0),
            r2.run(delay_before=5)  # R2 part 5s après
        )
```

### Modifier le Comportement Robot

```python
class SimpleRobot:
    async def run(self, delay_before=0, timeout=30):
        # Ajouter une logique personnalisée
        # Ex: arrêt aléatoire, vitesse variable, etc.
        pass
```

### Ajouter des Métriques

```python
# Mesurer le temps de passage
class SimpleRobot:
    def __init__(self, ...):
        self.time_entry = None
        self.time_exit = None
    
    async def run(self, ...):
        # À l'entrée
        self.time_entry = time.time()
        # ...
        # À la sortie
        self.time_exit = time.time()
        print(f"Temps de passage: {self.time_exit - self.time_entry:.2f}s")
```

---

## 🔧 Dépannage

### Timeout sur tous les robots

1. Vérifiez que Node-RED est en cours d'exécution
2. Vérifiez que le bon mode est sélectionné
3. Vérifiez la connexion MQTT: `mosquitto_sub -h localhost -t '#'`

### Les robots ne reçoivent pas GO

1. Regardez les logs Node-RED
2. Vérifiez le format des messages avec: `mosquitto_sub -t 'intersection/#' -v`

### Erreur de connexion MQTT

```bash
# Vérifier que Mosquitto est actif
docker compose ps mosquitto

# Vérifier que le port est accessible
nc -zv localhost 1883
```

---

## 📦 Dépendances

```bash
pip install paho-mqtt
```

---

*Documentation Tests - VA55 UTBM*
