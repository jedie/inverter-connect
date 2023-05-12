
from ha_services.mqtt4homeassistant.data_classes import MqttSettings

from inverter.data_types import Config


def set_defaults(dictionary: dict, defaults: dict):
    for key, value in defaults.items():
        dictionary.setdefault(key, value)


def get_config(**kwargs) -> Config:
    set_defaults(
        kwargs,
        defaults=dict(
            verbosity=0,
            host='123.123.0.1',
            port=48899,
            mqtt_settings=MqttSettings(),
            inverter_name='deye_2mppt',
        ),
    )
    return Config(**kwargs)

#
# class MockCurrentWorkDir:
#     def __init__(self, temp_path: Path):
#         self.temp_path = temp_path
#         self.old_cwd = Path().cwd()
#         assert self.temp_path != self.old_cwd
#
#     def __enter__(self):
#         os.chdir(self.temp_path)
#         return self
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         os.chdir(self.old_cwd)
#         if exc_type:
#             return False
#
#
# class MockedSys:
#     executable = '/mocked/.venv/bin/python3'
#
#
# class MockedUserSetting(MassContextManager):
#     """
#     TODO: Move to hs-services !
#     """
#
#     def __init__(self, temp_path: Path, settings_dataclass: dataclasses, **env_overwrites):
#         self.temp_path = temp_path
#
#         assert dataclasses.is_dataclass(settings_dataclass)
#         self.settings_dataclass = settings_dataclass
#
#         env_overwrites.setdefault('PYTHONUNBUFFERED', '1')
#         env_overwrites.setdefault('COLUMNS', '120')
#
#         self.mocks = (
#             MockCurrentWorkDir(temp_path=temp_path),
#             OverrideEnviron(HOME=str(temp_path), **env_overwrites),
#             mock.patch.object(defaults, 'sys', MockedSys()),
#         )
#
#     def __enter__(self) -> 'MockedUserSetting':
#         super().__enter__()
#
#         mocked_systemd_base_path = self.temp_path / 'etc-systemd-system'
#         mocked_systemd_base_path.mkdir()
#
#         Path(self.temp_path, '.config').mkdir()
#
#         settings_dataclass = self.settings_dataclass()
#         self.toml_settings = TomlSettings(
#             dir_name=SETTINGS_DIR_NAME,
#             file_name=SETTINGS_FILE_NAME,
#             settings_dataclass=settings_dataclass,
#         )
#         self.settings_file_path = self.toml_settings.file_path
#
#         document: TOMLDocument = dataclass2toml(instance=settings_dataclass)
#         doc_str = tomlkit.dumps(document, sort_keys=False)
#         self.settings_file_path.write_text(doc_str, encoding='UTF-8')
#
#         return self
#
#
# class NoColors(MassContextManager):
#     # TODO: Move to CLI-tools
#     mocks = (OverrideEnviron(COLUMNS='120', TERM='dump', NO_COLOR='1'),)
#
#     def __enter__(self):
#         super().__enter__()
#
#         console = get_console()  # global console instance
#         console._highlight = False
#
#     def __exit__(self, exc_type, exc_val, exc_tb):
#         super().__exit__(exc_type, exc_val, exc_tb)
#         if exc_type:
#             return False
