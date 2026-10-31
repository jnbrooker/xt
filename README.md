# xT

Expected threat (xT) for every player in a Premier League match, one simple page per match.

Event data comes from WhoScored via [soccerdata](https://github.com/probberechts/soccerdata). Actions are converted to SPADL and valued with [socceraction](https://github.com/ML-KULeuven/socceraction)'s xT model, using Karun Singh's open 12×8 grid (`data/xt_grid_12x8.json`). Only successful passes and carries count.

## Setup

```
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Chrome must be installed. WhoScored blocks headless browsers, so a Chrome window opens while data is being fetched.

## Use

```
.venv\Scripts\python build.py --today               # all matches today that have kicked off
.venv\Scripts\python build.py --today --watch 120   # keep live matches refreshing
.venv\Scripts\python build.py 1983629               # one match by WhoScored id
.venv\Scripts\python build.py --render              # rebuild pages from saved data
```

Pages are written to `docs/`. To publish with GitHub Pages, deploy from the `main` branch's `/docs` folder.
