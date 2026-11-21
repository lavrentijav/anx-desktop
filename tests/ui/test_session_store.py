from anx_desktop.api import AnixartClient
from anx_desktop.ui.session_store import FileTokenStore


def test_session_survives_reopening_and_logout_clears_it(tmp_path):
    path = tmp_path / 'data' / 'session.json'
    with AnixartClient(token_store=FileTokenStore(path)) as client:
        client.set_token('test-session', profile_id=42)
    with AnixartClient(token_store=FileTokenStore(path)) as client:
        assert client.is_authenticated
        assert client.token == 'test-session'
        assert client.session.profile_id == 42
        client.auth.logout()
    assert FileTokenStore(path).load() is None


def test_move_legacy_session_without_restoring_it_after_logout(tmp_path):
    from anx_desktop.api.auth import StoredToken

    old = FileTokenStore(tmp_path / 'old' / 'session.json')
    new = FileTokenStore(tmp_path / 'new' / 'session.json')
    old.save(StoredToken('test-session', 42))
    new.migrate_from(old.path)
    assert new.load() == StoredToken('test-session', 42)
    assert not old.path.exists()
    new.clear()
    new.migrate_from(old.path)
    assert new.load() is None
