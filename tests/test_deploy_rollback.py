import json
import sqlite3
import subprocess
import sys
from types import SimpleNamespace
import pytest
from scripts import deploy_ui


def test_failed_public_readiness_restores_previous_container(monkeypatch,tmp_path):
    data=tmp_path/'data';data.mkdir();release=tmp_path/'release';release.mkdir()
    with sqlite3.connect(data/'deepdive.db') as db:
        db.execute('CREATE TABLE runs(id TEXT,current_state TEXT)')
        db.execute("INSERT INTO runs VALUES('saved','END')")
    original={'Mounts':[{'Destination':'/app/data','Source':str(data)}],
              'HostConfig':{'NetworkMode':'test-network'},
              'Config':{'Env':[], 'Labels':{'traefik.enable':'true','org.opencontainers.image.revision':'old'}}}
    commands=[]
    def docker(*args):
        commands.append(args)
        return json.dumps([original]) if args==('inspect','deepdive') else 'ok'
    def run(command,**kwargs):
        commands.append(tuple(command))
        if command[:3]==['docker','container','inspect']:
            return SimpleNamespace(returncode=1)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(deploy_ui,'docker',docker)
    monkeypatch.setattr(deploy_ui.subprocess,'run',run)
    monkeypatch.setattr(deploy_ui.os,'fchmod',lambda *args:None,raising=False)
    monkeypatch.setattr(deploy_ui.time,'sleep',lambda _:None)
    def unavailable(*args,**kwargs): raise OSError('Fixture public health unavailable')
    monkeypatch.setattr(deploy_ui.urllib.request,'urlopen',unavailable)
    monkeypatch.setattr(sys,'argv',['deploy_ui.py','candidate-image',str(release),'--promote'])
    with pytest.raises(RuntimeError,match='Public readiness failed'):
        deploy_ui.main()
    assert ('docker','rm','-f','deepdive') in commands
    assert any(cmd[0]=='rename' and cmd[-1]=='deepdive' and str(cmd[1]).startswith('deepdive-rollback-ui-') for cmd in commands)
    assert ('start','deepdive') in commands
    production=next(cmd for cmd in commands if cmd[:4]==('run','-d','--name','deepdive'))
    assert 'org.opencontainers.image.revision=old' not in production
    assert (release/'validation-data/deepdive.db').exists()
