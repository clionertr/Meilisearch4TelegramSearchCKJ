from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="MTS",
    settings_files=['settings.toml', '.secrets.toml'],
    merge_enabled=True,
)
