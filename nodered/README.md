# 🎛️ Node-RED - Contrôleur d'Intersection
## VA55 - UTBM

Ce répertoire contient la configuration Node-RED pour le contrôleur d'intersection multi-mode.

---

## 📁 Structure

```
nodered/
├── flows.json    # Configuration des flows Node-RED
├── settings.js   # Paramètres Node-RED (si personnalisé)
└── README.md     # Cette documentation
```

---

## 🚀 Accès

| Service | URL |
|---------|-----|
| **Dashboard** | http://localhost:1880/ui |
| **Éditeur** | http://localhost:1880 |

---

## 🔧 Flows

### Architecture des Nodes

```
┌─────────────────────────────────────────────────────────────────┐
│                         NODE-RED                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                                               │
│  │   MQTT IN    │──┐                                            │
│  │ (status)     │  │      ┌───────────────────────────────┐    │
│  └──────────────┘  ├─────►│                               │    │
│                    │      │   MULTI-MODE CONTROLLER       │    │
│  ┌──────────────┐  │      │                               │    │
│  │   Timer      │──┤      │  ┌─────┐ ┌─────┐ ┌────────┐  │    │
│  │   (1s tick)  │  │      │  │ FEU │ │FIFO │ │PELOTON │  │    │
│  └──────────────┘  │      │  └─────┘ └─────┘ └────────┘  │    │
│                    │      │                               │    │
│  ┌──────────────┐  │      └───────────┬───────────────────┘    │
│  │   Mode       │──┘                  │                         │
│  │   Selector   │                     ▼                         │
│  └──────────────┘   ┌─────────────────┴─────────────────┐      │
│                     │                                    │      │
│                     ▼                                    ▼      │
│              ┌──────────────┐                  ┌──────────────┐ │
│              │   MQTT OUT   │                  │  Dashboard   │ │
│              │  (command)   │                  │   Update     │ │
│              └──────────────┘                  └──────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Nodes Principaux

### 1. MQTT In (`Robot Status`)
- **Topic:** `intersection/status`
- **QoS:** 1
- **Format:** JSON

### 2. Timer (`Tick 1s`)
- Envoi d'un message `tick` chaque seconde
- Utilisé pour le mode FEU (changement de phase)

### 3. Multi-Mode Controller
- **Fonction principale** contenant toute la logique
- Gère l'état global
- Traite les 3 modes

### 4. MQTT Out (`Robot Command`)
- **Topic:** `intersection/command`
- **QoS:** 1

### 5. Dashboard
- Sélecteur de mode
- Affichage de l'état
- Historique des événements

---

## 💾 État Global

```javascript
state = {
    intersection: "LIBRE",     // ou "OCCUPE"
    
    // FIFO
    queue: [],                 // Liste d'attente [id1, id2, ...]
    
    // FEU
    file_attente: [],          // Robots en attente de feu vert
    phase: 0,                  // 0=VertA, 1=RougeTout, 2=VertB, 3=RougeTout
    timer: 0,                  // Compteur de secondes
    feu: { A: "VERT", B: "ROUGE" },
    
    // PELOTON
    queue_voie_A: 0,           // Distance cumulée voie A
    queue_voie_B: 0,           // Distance cumulée voie B
    
    // Commun
    robots: {},                // Tous les robots connus
    history: [],               // Historique des événements
    stats: { total: 0, passed: 0 }
}
```

---

## 🚦 Mode FEU

### Logique

1. **Timer tick:** Incrémente `state.timer`
2. **Changement de phase:** Si durée atteinte
3. **Déblocage:** Si nouvelle phase = VERT, envoie GO aux robots en `file_attente`

### Phases et Durées

```javascript
const DUREE_VERT = 10;           // seconds
const DUREE_ROUGE_INTEGRAL = 3;  // seconds
```

| Phase | Feu A | Feu B | Durée |
|-------|-------|-------|-------|
| 0 | 🟢 | 🔴 | 10s |
| 1 | 🔴 | 🔴 | 3s |
| 2 | 🔴 | 🟢 | 10s |
| 3 | 🔴 | 🔴 | 3s |

### Code Clé

```javascript
// Changement de phase
if (state.timer >= duree_phase) {
    state.phase = (state.phase + 1) % 4;
    state.timer = 0;
}

// Déblocage sur feu vert
if (state.phase === 0 || state.phase === 2) {
    let voieVerte = (state.phase === 0) ? "A" : "B";
    state.file_attente.filter(id => robots[id].voie === voieVerte)
        .forEach(id => commands.push({ target_id: id, action: "GO" }));
}
```

---

## 📋 Mode FIFO

### Logique

1. **etape=1:** Ajoute à queue, GO si premier et LIBRE
2. **etape=2:** Sécurité, GO si premier et LIBRE
3. **etape=3:** Retire de queue, GO au suivant

### Pré-réservation

Le robot peut recevoir GO à l'étape 1, ce qui lui permet de faire un **PASS-THROUGH** à l'étape 2 (il ne s'arrête pas).

### Code Clé

```javascript
// Étape 1 - Entrée
if (!state.queue.includes(robot_id)) {
    state.queue.push(robot_id);
}
if (state.intersection === "LIBRE" && state.queue[0] === robot_id) {
    commands.push({ target_id: robot_id, action: "GO" });
    state.intersection = "OCCUPE";
}

// Étape 3 - Sortie
state.queue = state.queue.filter(id => id !== robot_id);
state.intersection = "LIBRE";
if (state.queue.length > 0) {
    commands.push({ target_id: state.queue[0], action: "GO" });
    state.intersection = "OCCUPE";
}
```

---

## 🚗 Mode PELOTON

### Logique

1. **Inférence de distance** basée sur la cause
2. **Tri** des robots par distance croissante
3. **GO** au leader si distance = 0 et LIBRE

### Calcul de Distance

| Événement | Distance |
|-----------|----------|
| `etape=1, cause=obstacle` | queue_voie + 35cm |
| `etape=1, cause=marker_entry` | 100 (loin) |
| `etape=2` | 0 (à la ligne) |

### Code Clé

```javascript
// Tri par distance
let robotsList = Object.entries(state.robots)
    .map(([id, r]) => ({ id, ...r }))
    .sort((a, b) => a.distance - b.distance);

// Décision
if (robotsList.length > 0) {
    let leader = robotsList[0];
    if (state.intersection === "LIBRE" && leader.distance === 0) {
        commands.push({ target_id: leader.id, action: "GO" });
        state.intersection = "OCCUPE";
    }
}
```

---

## 🔄 Personnalisation

### Modifier les durées FEU

Dans le node "Multi-Mode Controller":

```javascript
const DUREE_VERT = 15;           // Augmenter à 15 secondes
const DUREE_ROUGE_INTEGRAL = 5;  // Augmenter à 5 secondes
```

### Modifier la distance PELOTON

```javascript
const DISTANCE_INTER_ROBOT = 50;  // Augmenter à 50cm
```

### Ajouter un nouveau mode

1. Ajouter l'option dans le dropdown du dashboard
2. Ajouter un bloc `else if (mode === "NOUVEAU_MODE")` dans le contrôleur
3. Implémenter la logique

---

## 🐛 Dépannage

### Les flows ne se chargent pas

```bash
docker compose restart nodered
docker compose logs nodered
```

### Le dashboard ne s'affiche pas

Vérifiez que `node-red-dashboard` est installé:
```bash
docker exec nodered_controller npm list node-red-dashboard
```

### Les robots ne reçoivent pas le GO

1. Vérifiez le mode sélectionné dans le dashboard
2. Regardez les logs: `docker compose logs nodered`
3. Vérifiez l'état dans le debug Node-RED

---

## 📊 Dashboard

### Éléments

- **Sélecteur de mode:** FEU, FIFO, PELOTON
- **Bouton Reset:** Réinitialise l'état
- **État intersection:** LIBRE/OCCUPE
- **File d'attente:** Liste des robots
- **Feux (mode FEU):** État A et B
- **Historique:** Derniers événements

---

*Documentation Node-RED - VA55 UTBM*
