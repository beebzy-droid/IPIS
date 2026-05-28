"""Centralized settings for IPIS, loaded from environment variables.

Uses pydantic-settings to validate and type-check configuration.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class InfluxDBSettings(BaseSettings):
    """InfluxDB connection settings."""

    model_config = SettingsConfigDict(env_prefix="INFLUXDB_", extra="ignore")

    url: str = "http://localhost:8086"
    token: str = ""
    org: str = "ipis"
    bucket: str = "process_data"


class MQTTSettings(BaseSettings):
    """MQTT broker settings."""

    model_config = SettingsConfigDict(env_prefix="MQTT_", extra="ignore")

    broker_host: str = "localhost"
    broker_port: int = 1883
    username: str = ""
    password: str = ""


class OPCUASettings(BaseSettings):
    """OPC-UA server settings."""

    model_config = SettingsConfigDict(env_prefix="OPCUA_", extra="ignore")

    server_endpoint: str = "opc.tcp://localhost:4840"
    namespace: str = "ipis"


class MLflowSettings(BaseSettings):
    """MLflow tracking settings."""

    model_config = SettingsConfigDict(env_prefix="MLFLOW_", extra="ignore")

    tracking_uri: str = "file:./mlruns"
    experiment_name: str = "ipis-module1"


class APISettings(BaseSettings):
    """FastAPI settings."""

    model_config = SettingsConfigDict(env_prefix="API_", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False


class Settings(BaseSettings):
    """Root settings — composes all subsettings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    debug: bool = Field(default=False, alias="DEBUG")

    influxdb: InfluxDBSettings = Field(default_factory=InfluxDBSettings)
    mqtt: MQTTSettings = Field(default_factory=MQTTSettings)
    opcua: OPCUASettings = Field(default_factory=OPCUASettings)
    mlflow: MLflowSettings = Field(default_factory=MLflowSettings)
    api: APISettings = Field(default_factory=APISettings)


def get_settings() -> Settings:
    """Get the global settings instance.

    Returns:
        Settings loaded from environment variables and .env file.
    """
    return Settings()
