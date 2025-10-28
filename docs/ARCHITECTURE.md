# Architecture Comparison

## Before: Continuous Mode Only

```
┌─────────────────────────────────────────────────┐
│  Docker Container (Always Running)              │
│  ┌───────────────────────────────────────────┐  │
│  │  TweetCordBot                             │  │
│  │  ┌─────────────────────────────────────┐ │  │
│  │  │  1. Fetch tweets                    │ │  │
│  │  │  2. Check for new tweets            │ │  │
│  │  │  3. Post to Discord                 │ │  │
│  │  │  4. Sleep 8 hours ⏰                │ │  │
│  │  │  5. GOTO 1 (infinite loop)          │ │  │
│  │  └─────────────────────────────────────┘ │  │
│  │                                           │  │
│  │  last_tweet_id = None (in memory only) ❌ │  │
│  └───────────────────────────────────────────┘  │
│                                                  │
│  Problem: Container restart → Memory lost       │
│           → Duplicate tweets 🐛                 │
└─────────────────────────────────────────────────┘
```

## After: CronJob Mode with Persistence

```
┌─────────────────────────────────────────────────────────────┐
│  Kubernetes CronJob (Schedule: 0 */8 * * *)                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Every 8 hours, spawn a new Pod:                      │  │
│  │  ┌─────────────────────────────────────────────────┐  │  │
│  │  │  TweetCordBot (RUN_MODE=once)                   │  │  │
│  │  │  ┌───────────────────────────────────────────┐  │  │  │
│  │  │  │  1. Load state from disk 💾               │  │  │  │
│  │  │  │     last_tweet_id = "123456..."           │  │  │  │
│  │  │  │  2. Fetch tweets from Twitter             │  │  │  │
│  │  │  │  3. Compare with last_tweet_id            │  │  │  │
│  │  │  │  4. Post new tweets to Discord            │  │  │  │
│  │  │  │  5. Save new state to disk 💾             │  │  │  │
│  │  │  │  6. Exit (pod terminates) ✅              │  │  │  │
│  │  │  └───────────────────────────────────────────┘  │  │  │
│  │  │                                                 │  │  │
│  │  │  Volume Mount:                                  │  │  │
│  │  │  /app/logs → PersistentVolumeClaim             │  │  │
│  │  └─────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  PersistentVolumeClaim (10Mi)                       │    │
│  │  ┌───────────────────────────────────────────────┐  │    │
│  │  │  logs/last_tweet_id.txt                       │  │    │
│  │  │  Content: "1234567890123456789"               │  │    │
│  │  │  ✅ Survives pod restarts                     │  │    │
│  │  │  ✅ Survives node restarts                    │  │    │
│  │  │  ✅ Survives cluster restarts                 │  │    │
│  │  └───────────────────────────────────────────────┘  │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  Benefits:                                                   │
│  ✅ No duplicate tweets                                     │
│  ✅ Resource efficient (runs only ~30 seconds)             │
│  ✅ Kubernetes-native scheduling                           │
│  ✅ Easy to debug (isolated runs)                          │
└─────────────────────────────────────────────────────────────┘
```

## State Persistence Flow

```
First Run:
─────────
┌──────────┐    ┌─────────────────┐    ┌──────────────┐
│ Pod      │───▶│ logs/ not found │───▶│ last_tweet_id│
│ Starts   │    │ Start fresh ✨  │    │ = None       │
└──────────┘    └─────────────────┘    └──────────────┘
                                               │
                                               ▼
┌──────────┐    ┌─────────────────┐    ┌──────────────┐
│ Post to  │◀───│ Find 3 new      │◀───│ Fetch tweets │
│ Discord  │    │ tweets          │    │ from Twitter │
└──────────┘    └─────────────────┘    └──────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ Save state to disk:              │
│ logs/last_tweet_id.txt           │
│ → "9999999999999999999"          │
└──────────────────────────────────┘
       │
       ▼
┌──────────┐
│ Pod Exit │
└──────────┘


Second Run (8 hours later):
──────────────────────────
┌──────────┐    ┌─────────────────┐    ┌──────────────┐
│ New Pod  │───▶│ Load from disk  │───▶│ last_tweet_id│
│ Starts   │    │ logs/last_tweet │    │ = "999999..."│
└──────────┘    │ _id.txt ✅      │    └──────────────┘
                └─────────────────┘            │
                                               ▼
┌──────────┐    ┌─────────────────┐    ┌──────────────┐
│ Post NEW │◀───│ Compare and find│◀───│ Fetch tweets │
│ tweets   │    │ only 1 new tweet│    │ from Twitter │
│ only     │    │ after "999999..." │    └──────────────┘
└──────────┘    └─────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ Update state on disk:            │
│ logs/last_tweet_id.txt           │
│ → "1111111111111111111" (new)    │
└──────────────────────────────────┘
       │
       ▼
┌──────────┐
│ Pod Exit │
└──────────┘


Container Restart (mini PC reboot):
────────────────────────────────────
┌──────────┐    ┌─────────────────┐    ┌──────────────┐
│ Mini PC  │───▶│ PVC survives! ✅│───▶│ Next pod     │
│ Reboots  │    │ State file still│    │ loads correct│
└──────────┘    │ contains        │    │ last_tweet_id│
                │ "1111111..."    │    │ No duplicates│
                └─────────────────┘    └──────────────┘
```

## Resource Usage Comparison

### Continuous Mode (Docker Compose)
```
Time:     [0h ────── 8h ────── 16h ────── 24h ───────]
CPU:      [█████████ █████████ █████████ ██████████]
Memory:   [64MB continuous ──────────────────────────]
Active:   [Always running, sleeping 99.9% of time   ]
```

### CronJob Mode (Kubernetes)
```
Time:     [0h ────── 8h ────── 16h ────── 24h ───────]
CPU:      [█         █         █         █          ]
Memory:   [64MB for 30s, then 0MB ──────────────────]
Active:   [Only during fetch (30s every 8 hours)    ]

Savings: ~99.9% CPU time, ~99.9% memory time
```

## Deployment Comparison

| Feature | Continuous Mode | CronJob Mode |
|---------|----------------|--------------|
| Deployment | Docker Compose | Kubernetes CronJob |
| Scheduling | Internal (time.sleep) | External (Kubernetes) |
| Resource Usage | Always running | Only during execution |
| State Persistence | ✅ (via volume) | ✅ (via PVC) |
| Handles restarts | ✅ | ✅ |
| Scalability | ❌ (single container) | ✅ (K8s native) |
| Observability | Container logs | Job history + logs |
| Best for | Simple deployments | Production clusters |

## Migration Path

```
┌─────────────────┐
│ Current Setup   │
│ (Continuous)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Step 1: Add     │
│ Persistence ✅  │◀── You are here!
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Step 2: Test    │
│ locally with    │
│ RUN_MODE=once   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Step 3: Deploy  │
│ to Kubernetes   │
│ CronJob         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Step 4: Monitor │
│ & optimize      │
│ schedule        │
└─────────────────┘
```
