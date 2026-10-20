# Smart Store — IoT Project

A semester-long IoT project, built in phases. Each phase lives in its own folder with its own code, dependencies, and setup instructions — you can set up and run any phase on its own without needing the others.

## Phases

| Phase | Folder | What it does |
|---|---|---|
| Phase 1 | [`Phase 1/`](./Phase%201/README.md) | Customer registration page (HTML/CSS/JS + Flask + SQLite) with a Raspberry Pi 5, blue/red LEDs and a buzzer signalling success/failure. |
| Phase 2 | [`Phase 2/`](./Phase%202/README.md) | IoT fridge-monitoring dashboard: two ESP32 + DHT11 sensors publish temperature/humidity over MQTT to a Raspberry Pi broker, a Flask dashboard displays live gauges, sends an email alert when a fridge overheats, and turns on a fan (DC motor) when you confirm the email. |

Open each phase's own README for its full setup, wiring, and run instructions.

## Repo layout

```
Smart-store/
├── README.md              <- you are here
├── Phase 1/                <- self-contained: own venv, own requirements.txt
└── Phase 2/                <- self-contained: own venv, own requirements.txt
```

Each phase folder is independent — different `requirements.txt`, different virtual environment, different Flask app running on a different port (Phase 1 on 5000, Phase 2 on 5001), so you can `cd` into either one and run it without the other phase needing to exist or run at the same time.
