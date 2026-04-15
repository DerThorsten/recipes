import pytest
from pathlib import Path

def test_keyring():
    import keyring


def test_keyring_set_get_password():
    import keyring
    keyring.set_password("system", "username", "password")
    pw = keyring.get_password("system", "username")
    assert pw == 'password'