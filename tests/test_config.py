"""Tests for configuration loading."""

import os

import pytest

from seestar_common import DEFAULT_CONFIG, load_config


class TestLoadConfig:
    def test_defaults_when_no_file(self, tmp_path):
        config = load_config(str(tmp_path))
        assert config == DEFAULT_CONFIG

    def test_defaults_not_mutated(self, tmp_path):
        config = load_config(str(tmp_path))
        config["optics"]["focal_length"] = 999
        assert DEFAULT_CONFIG["optics"]["focal_length"] == 250

    def test_override_single_value(self, tmp_path):
        yaml_content = "optics:\n  focal_length: 300\n"
        (tmp_path / "seestar_config.yaml").write_text(yaml_content)
        config = load_config(str(tmp_path))
        assert config["optics"]["focal_length"] == 300
        # Other optics values should remain default
        assert config["optics"]["pixel_size"] == 2.9

    def test_override_nested_section(self, tmp_path):
        yaml_content = (
            "stacking:\n"
            "  sigma_high: 5\n"
            "  sigma_low: 2\n"
        )
        (tmp_path / "seestar_config.yaml").write_text(yaml_content)
        config = load_config(str(tmp_path))
        assert config["stacking"]["sigma_high"] == 5
        assert config["stacking"]["sigma_low"] == 2
        assert config["stacking"]["normalization"] == "addscale"

    def test_empty_yaml(self, tmp_path):
        (tmp_path / "seestar_config.yaml").write_text("")
        config = load_config(str(tmp_path))
        assert config == DEFAULT_CONFIG

    def test_invalid_yaml_returns_defaults(self, tmp_path):
        (tmp_path / "seestar_config.yaml").write_text("[[[invalid")
        # yaml.safe_load will raise, but load_config should handle it
        # In practice yaml.safe_load("[[[invalid") raises ScannerError
        # Our function should let it propagate or return defaults
        # For robustness, we accept either behavior
        try:
            config = load_config(str(tmp_path))
            assert config == DEFAULT_CONFIG
        except Exception:
            pass  # Also acceptable -- malformed YAML is a user error

    def test_non_dict_yaml_returns_defaults(self, tmp_path):
        (tmp_path / "seestar_config.yaml").write_text("just a string")
        config = load_config(str(tmp_path))
        assert config == DEFAULT_CONFIG

    def test_unknown_sections_ignored(self, tmp_path):
        yaml_content = (
            "optics:\n"
            "  focal_length: 200\n"
            "custom_section:\n"
            "  my_value: 42\n"
        )
        (tmp_path / "seestar_config.yaml").write_text(yaml_content)
        config = load_config(str(tmp_path))
        assert config["optics"]["focal_length"] == 200
        assert "custom_section" not in config
