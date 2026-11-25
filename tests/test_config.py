import stat

import pytest

from fuze import config


def test_defaults_and_private_files(fuze_home):
    cfg = config.save(dict(config.DEFAULTS))
    assert cfg == config.load() and cfg["mode"] == "dry"
    assert cfg["size_mode"] == "percent" and cfg["percent"] == 10.0 and cfg["max_position_usd"] is None
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
                                 {"scale": True}, {"scale": "0.1"}, {"scale": float("nan")}, {"max_x": 26},
                                 {"max_x": 0.05}, {"daily_loss_frac": 0.6}, {"daily_loss_frac": 0.001},
                                 {"stale_flat_min": 0}, {"dry_balance": "1000"}, {"surprise": 1},
                                 {"size_mode": "constant"}, {"size_mode": None}, {"percent": 0.5},
                                 {"percent": 101}, {"percent": True}, {"fixed_usd": 5}, {"fixed_usd": 2e6},
                                 {"fixed_usd": None}, {"max_position_usd": 5}, {"max_position_usd": 2e6},
                                 {"max_position_usd": float("inf")}, {"max_position_usd": "500"}])
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


@pytest.mark.parametrize("scale,percent", [(0.1, 10.0), (0.07, 7.0), (1, 100.0), (0.01, 1.0)])
def test_old_scale_becomes_percent(scale, percent):
    cfg = config.validate({"scale": scale})
    assert cfg["percent"] == percent and cfg["size_mode"] == "percent" and "scale" not in cfg


def test_old_config_file_still_loads(fuze_home):
    config.ensure_home()
    (fuze_home / "config.json").write_text('{"mode": "dry", "scale": 0.25, "max_x": 2.0, "daily_loss_frac": 0.1}')
    cfg = config.load()
    assert cfg["percent"] == 25.0 and cfg["max_x"] == 2.0 and "scale" not in cfg
    config.save(cfg)
    assert "scale" not in (fuze_home / "config.json").read_text()


def test_percent_wins_over_an_old_scale():
    assert config.validate({"scale": 0.5, "percent": 5})["percent"] == 5.0


def test_current_balance(fuze_home):
    cfg = config.validate({})
    assert config.current_balance(cfg) == 1000.0
    config.write_json(config.ensure_home() / "status.json", {"account": {"balance": 1234.5}})
    assert config.current_balance(cfg) == 1234.5
    (fuze_home / "status.json").write_text("not json")
    assert config.current_balance(cfg) == 1000.0
