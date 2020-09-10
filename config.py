from pathlib import Path

from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="METRICS", settings_files=["settings.yaml", ".secrets.yaml"],
)

METRICS_DIR = Path()
METRICS_OUTPUT = METRICS_DIR.joinpath("metrics_output")
