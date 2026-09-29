import json
from pathlib import Path
from tools.live_3d_test_server import make_fixture

def test_cockpit_safe_roster_projection():
    from app.match_cockpit import cockpit_context
    plan=json.loads(Path('tests/fixtures/match-visual-plan.json').read_text())
    plan['future_score']=[9,0]
    context=cockpit_context(plan)
    assert len(context['squads']['home'])==11
    assert len(context['squads']['away'])==11
    assert context['player']['actor_id']=='career_player'
    assert 'future_score' not in context
    assert 'attributes' not in context['squads']['home'][0]
    assert context['bench_complete'] is False

def test_match_cockpit_renders_live_regions_and_inert_report(tmp_path):
    app,sid=make_fixture(tmp_path/'cockpit.sqlite3')
    response=app.test_client().get('/match/'+sid)
    assert response.status_code==200
    from html.parser import HTMLParser
    class Document(HTMLParser):
        def __init__(self):
            super().__init__(); self.ids={}; self.tabs=[]; self.context=''; self.in_context=False
        def handle_starttag(self, tag, attrs):
            attrs=dict(attrs)
            if 'id' in attrs: self.ids[attrs['id']]=(tag,attrs)
            if attrs.get('role')=='tab': self.tabs.append(attrs)
            if attrs.get('id')=='cockpit-data': self.in_context=True
        def handle_endtag(self, tag):
            if tag=='script': self.in_context=False
        def handle_data(self, data):
            if self.in_context: self.context+=data
    dom=Document(); dom.feed(response.data.decode())
    for identifier in ['match-stage','match-broadcast','cockpit-latest','live-player-minutes','squad-tabs','jump-to-live']:
        assert identifier in dom.ids
    dialog=dom.ids['match-report-dialog']
    assert dialog[0]=='dialog' and 'open' not in dialog[1]
    assert 'post-match-mount' in dom.ids
    context=json.loads(dom.context)
    assert context['player']['display_name']=='3D QA Player'
    assert len(dom.tabs)==3
