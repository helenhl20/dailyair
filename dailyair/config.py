"""DailyAir configuration loader."""

import os
import yaml
from pathlib import Path


def _resolve_env(value: str, env_var: str) -> str:
    return os.environ.get(env_var, value or "")


def load_config(config_path: str = "config.yaml") -> dict:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            "Copy config.example.yaml to config.yaml and fill in your details."
        )
    with open(path) as f:
        config = yaml.safe_load(f)

    if config.get("llm"):
        config["llm"]["api_key"] = _resolve_env(
            config["llm"].get("api_key", ""), "DAILYAIR_LLM_API_KEY"
        )
    if config.get("email"):
        config["email"]["password"] = _resolve_env(
            config["email"].get("password", ""), "DAILYAIR_EMAIL_PASSWORD"
        )
    if config.get("output", {}).get("email"):
        config["output"]["email"]["password"] = _resolve_env(
            config["output"]["email"].get("password", ""), "DAILYAIR_SMTP_PASSWORD"
        )

    return config
