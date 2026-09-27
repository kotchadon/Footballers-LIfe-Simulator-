"""Disposable local browser fixture: never opens the player's career database."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from app.db import get_db
from app.services import create_career, get_active_career, advance_calendar_week, prepare_next_match

def make_fixture(database):
    app = create_app({'TESTING': True, 'DATABASE': str(database), 'SECRET_KEY': 'local-3d-qa'})
    with app.app_context():
        cid = create_career('3D QA Player', 'India', 'CAM')
        for _ in range(20):
            session = prepare_next_match(cid, seed=77)
            if session is not None:
                break
            ok, message, _ = advance_calendar_week(cid, seed=42)
            if not ok:
                raise RuntimeError(message)
        else:
            raise RuntimeError('No fixture available')
        public_id = session['public_id']
    return app, public_id

if __name__ == '__main__':
    with tempfile.TemporaryDirectory(prefix='footy-live3d-qa-') as temp:
        app, public_id = make_fixture(Path(temp) / 'qa.sqlite3')
        port = int(sys.argv[1]) if len(sys.argv) > 1 else 8778
        print(json.dumps({'url': f'http://127.0.0.1:{port}/match/{public_id}'}), flush=True)
        app.run(host='127.0.0.1', port=port, use_reloader=False)
