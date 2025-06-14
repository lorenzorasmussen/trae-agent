# Copyright (c) 2025 ByteDance Ltd. and/or its affiliates
# SPDX-License-Identifier: MIT

import json
from pathlib import Path
import os
from dataclasses import dataclass


# data class for model parameters
@dataclass
class ModelParameters:
    """Model parameters for a model provider."""
    model: str
    api_key: str
    max_tokens: int
    temperature: float
    top_p: float
    top_k: int
    parallel_tool_calls: bool


class Config:
    """Configuration manager for Trae Agent."""
    
    def __init__(self, config_file: str = "trae_config.json"):
        config_path = Path(config_file)
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    self._config = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load config file {config_file}: {e}")
                self._config = {}
            
        self.default_provider: str = self._config.get("default_provider", "anthropic")
        self.max_steps: int = self._config.get("max_steps", 20)
        self.model_providers: dict[str, ModelParameters] = {}

        if len(self._config.get("model_providers", [])) == 0:
            self.model_providers = {
                "anthropic": ModelParameters(
                    model="claude-sonnet-4-20250514",
                    api_key="",
                    max_tokens=1000,
                    temperature=0.5,
                    top_p=1,
                    top_k=0,
                    parallel_tool_calls=False,
                ),
            }
        else:
            for provider in self._config.get("model_providers", {}).keys():
                provider_config: dict[str, str | int | float | bool] = self._config.get("model_providers", {}).get(provider, {})
                self.model_providers[provider] = ModelParameters(
                    model=str(provider_config.get("model", "")),
                    api_key=str(provider_config.get("api_key", "")),
                    max_tokens=int(provider_config.get("max_tokens", 1000)),
                    temperature=float(provider_config.get("temperature", 0.5)),
                    top_p=float(provider_config.get("top_p", 1)),
                    top_k=int(provider_config.get("top_k", 0)),
                    parallel_tool_calls=bool(provider_config.get("parallel_tool_calls", False)),
                )
            
        return
            

    def __str__(self) -> str:
        return f"Config(default_provider={self.default_provider}, max_steps={self.max_steps}, model_providers={self.model_providers})"


def load_config(config_file: str = "trae_config.json") -> Config:
    """Load configuration from file."""
    return Config(config_file)


def resolve_config_value(cli_value: int | str | float | None, config_value: int | str | float | None, env_var: str | None = None) -> int | str | float | None:
    """Resolve configuration value with priority: CLI > ENV > Config > Default."""
    if cli_value is not None:
        return cli_value
    
    if env_var and os.getenv(env_var):
        return os.getenv(env_var)
    
    if config_value is not None:
        return config_value
    
    return None