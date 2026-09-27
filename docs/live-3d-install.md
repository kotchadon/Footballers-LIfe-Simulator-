# Live 3D match candidate

Target: supplied `feat/3d-stadium-poc` at `b7fe610eb1838cffcd36cccbf77b19666b732a82`.

## What is implemented

Live Three.js renderer using the existing tactical engine, stadium, match events and Flask API. Both 2D and 3D consume one clock and one captured presentation state. The server still owns all results, match events, progression and settlement.

- 22 articulated, stylized footballers with team kits, distinct goalkeepers, shirt numbers and running/kicking/receiving/diving/celebration poses.
- A gold ground ring and overhead indicator follow the actual career player, including substitution onto the field; removed players lose their marker.
- Metre-based speed, acceleration, bounded turning and body separation; passing, dribbling, aerial ball trajectories, goal nets, crowd and broadcast/whole-pitch cameras.
- Goals cross the goal line only for an already revealed goal. Set pieces cannot invent a goal. Shots use a broadcast staging cut to the revealed position.
- Full-time freezes the scene and stops its animation loop. Completed reload never starts a match loop. Pausing, speed and renderer switching share the existing replay controller.
- Missing modules, missing models, unsupported WebGL, load timeout and context loss fall back to tactical 2D. Three.js and every dependency are local and pinned to 0.186.0; no CDN or security-policy changes.
- Pixel ratio capped at 1.5; instanced crowd and limited shadow casters.

## Install

Download `install_footy_live_3d.py` to Downloads. From Terminal:

```sh
cd "/Users/advaykatoch/Developer/footy sim"
.venv/bin/python "$HOME/Downloads/install_footy_live_3d.py"
```

The installer refuses a different branch, commit, dirty tree, changed source hashes or conflicting new files. It backs up affected files, installs, runs Python tests/compile/diff checks, and runs Node tests when Node 18+ is installed. Failed checks restore original source. It leaves changes uncommitted for review and does not modify career saves.

Restart your existing Flask server and refresh the match page. Live 3D loads automatically, with Tactical 2D available alongside it. Use the camera selector for the whole-pitch view.

To restore, use the exact `--restore` command printed by the installer. Restore refuses to overwrite files edited since installation.

## Verification and release status

This is an implementation candidate, **not a certified production release**. Automated Python, tactical state, real GLB scene, choreography, lifecycle and renderer-fallback tests run in the build environment. Actual browser rendering could not be exercised there: local Chromium was denied its process socket; the supported cloud browser blocked localhost. No browser screenshots, Safari acceptance or MacBook M3 frame-rate claims are made.

The player models are stylized jointed meshes, not photorealistic scanned players or motion-captured commercial football animation. The existing backend generates a sealed match and the 3D view presents its revealed events; it does not introduce a separate physics-driven football outcome engine.

Before committing/releasing, open a match and check: visible moving teams and ball; your marker; substitution on/off; goals/saves/cards; 1×/2×/4×; pause; 2D/3D switching; full time; completed reload; narrow window; Safari on your M3.

A reproducible Chromium acceptance runner is included. With Node 18+ and Playwright installed in an external QA directory:

```sh
npm install --prefix "$HOME/Downloads/footy-3d-qa" playwright
"$HOME/Downloads/footy-3d-qa/node_modules/.bin/playwright" install chromium
NODE_PATH="$HOME/Downloads/footy-3d-qa/node_modules" node tools/check_live_3d.cjs
```

This uses a separate temporary database, starts a loopback-only test server on port 8778, runs UI checks and writes screenshots/results under `.upgrade-backups/live3d-browser-qa`. It never opens your real career database. Browser acceptance has not yet been run in this environment.

## Decisions and limits

- The source collector omitted `app/schema.sql`. Isolated tests use the previously supplied schema, with byte-identical `app/db.py`; the installer does not ship or alter schema.sql. Cost if wrong: local regression may differ and installation will restore source on failure.
- No browser restriction was bypassed. Packaging proceeds as an uncommitted candidate, with local visual acceptance required. Cost: GPU/layout defects may remain until local acceptance.
- Existing stadium is retained; articulated bodies are generated inside its named actor roots. Cost: stylized visual quality rather than photorealism.
- No feature commit is created before actual browser acceptance. The synthetic imported baseline in the isolated build is not the user's Git history.

## Independent review

One fresh-context review found three integration defects. Fixed: paused/hidden choreography now uses simulation time for its watchdog; instant substitutions/cards refresh the captured frame without stepping; resize observes the shared visible broadcast container. Error paths also synchronize paused visuals, and late visual completion cannot overwrite the final report. The fixes have focused regression tests.

Two minor presentation limitations are deferred: a camera selection made before the 3D model finishes loading must be selected again after loading; the short transition banner uses wall time and can fade while paused. Neither changes match state, player identity, score or settlement.

The reviewer did not certify visual quality, GPU speed, Safari or responsive pixel appearance without a working browser. Installer install/restore/failure rollback were exercised separately in a disposable copy of the uploaded source; a synthetic fixture HEAD was used only inside that test, never in the delivered installer's guard.

Final automated evidence: **362 Python tests passed; 34 Node tests passed**. Python compilation and Git whitespace checks passed. The final installer fixture verified wrong-HEAD refusal, dirty-tree refusal, exact-source validation, successful installation, protection of later edits during restore, clean restoration, and automatic rollback on a deliberately failed mandatory test. Production Python backend files match the supplied snapshot hashes.
