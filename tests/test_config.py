import stat

import pytest

from fuze import config


def test_defaults_and_private_files(fuze_home):
    cfg = config.save(dict(config.DEFAULTS))
    assert cfg == config.load() and cfg["mode"] == "dry" and cfg["scale"] == 0.1
    assert stat.S_IMODE(fuze_home.stat().st_mode) == 0o700
    assert stat.S_IMODE((fuze_home / "config.json").stat().st_mode) == 0o600
    assert not list(fuze_home.glob(".tmp-*"))


@pytest.mark.parametrize("url", ["http://fuze.trade", "ftp://fuze.trade", "https://user:pw@fuze.trade",
                                 "https://fuze.trade/x", "https://fuze.trade?a=1", "https://", 5,
                                 "http://localhost.evil.com"])
def test_bad_servers(url):
    with pytest.raises(ValueError):
        config.validate({"server": url})


@pytest.mark.parametrize("url", ["https://fuze.trade/", "http://localhost:8080", "http://127.0.0.1:9"])
def test_good_servers(url):
    assert config.validate({"server": url})["server"] == url.rstrip("/")


@pytest.mark.parametrize("bad", [{"mode": "live"}, {"mode": "testnet"}, {"scale": 0}, {"scale": 1.5},
                                 {"scale": True}, {"scale": float("nan")}, {"max_x": 26}, {"max_x": 0.05},
                                 {"daily_loss_frac": 0.6}, {"daily_loss_frac": 0.001}, {"stale_flat_min": 0},
                                 {"dry_balance": "1000"}, {"surprise": 1}])
def test_bad_values(bad):
    with pytest.raises(ValueError):
        config.validate(bad)


def test_mode_message_is_clear():
    with pytest.raises(ValueError, match="dry"):
        config.validate({"mode": "mainnet"})


def test_invalid_file_refused(fuze_home):
    config.ensure_home()
    (fuze_home / "config.json").write_text('{"max_x": 100}')
    with pytest.raises(ValueError):
        config.load()
