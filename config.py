from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="METRICS", settings_files=["settings.yaml", ".secrets.yaml"],
)
