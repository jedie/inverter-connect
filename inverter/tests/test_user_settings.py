import json
import tempfile
from pathlib import Path
from unittest import TestCase

from bx_py_utils.environ import OverrideEnviron
from bx_py_utils.path import assert_is_file
from ha_services.cli_tools.test_utils.assertion import assert_in
from ha_services.toml_settings.api import TomlSettings

from inverter.user_settings import SystemdServiceInfo, UserSettings, migrate_old_settings


class UserSettingsTestCase(TestCase):
    def test_migrate_old_settings(self):
        with tempfile.TemporaryDirectory(prefix='test-inverter-connect') as temp_dir:
            temp_path = Path(temp_dir)
            with OverrideEnviron(HOME=temp_dir):
                assert Path('~').expanduser() == temp_path
                Path(temp_path / '.config').mkdir()

                toml_settings = TomlSettings(
                    dir_name='test_dir_name',
                    file_name='test_file_name',
                    settings_dataclass=UserSettings(),
                )

                # Test convert the old, old settings file:
                old_settings_path = temp_path / '.inverter-connect'
                old_settings_path.write_text(
                    json.dumps(
                        dict(
                            host='my-mosquitto.tld',
                            port=1883,
                            user_name='test-user',
                            password='NoSecurePassword',
                        )
                    )
                )

                # Test: '~/.inverter-connect' -> '~/config/inverter-connect/inverter-connect.toml'
                with self.assertLogs(logger=None) as logs:
                    migrate_old_settings(toml_settings)

                self.assertEqual(
                    logs.output,
                    [
                        f'INFO:root:Migrate v1 settings from: {temp_dir}/.inverter-connect',
                        f'INFO:root:Migrate settings to: {temp_dir}/.config/test_dir_name/test_file_name.toml',
                    ],
                )
                self.assertFalse(Path(f'{temp_dir}/.inverter-connect').exists())

                # Test: '~/.inverter-connect.toml' -> '~/config/inverter-connect/inverter-connect.toml'
                Path(f'{temp_dir}/.config/test_dir_name/test_file_name.toml').rename(
                    Path(f'{temp_dir}/.inverter-connect.toml')
                )
                Path(f'{temp_dir}/.config/test_dir_name/').rmdir()
                with self.assertLogs(logger=None) as logs:
                    migrate_old_settings(toml_settings)

                self.assertEqual(
                    logs.output,
                    [
                        (
                            'INFO:root:Move settings file '
                            f'{temp_dir}/.inverter-connect.toml to '
                            f'{temp_dir}/.config/test_dir_name/test_file_name.toml'
                        ),
                    ],
                )

            self.assertFalse(old_settings_path.is_file())
            new_settings_path = Path(f'{temp_dir}/.config/test_dir_name/test_file_name.toml')
            assert_is_file(new_settings_path)
            new_settings_str = new_settings_path.read_text()

        assert_in(
            content=new_settings_str,
            parts=(
                '[mqtt]',
                'host = "my-mosquitto.tld"',
                'password = "NoSecurePassword"',
                '[systemd]',
                'systemd_base_path = "/etc/systemd/system"',
                'service_file_path = "/etc/systemd/system/inverter_connect.service"',
            ),
        )

    def test_systemd_service_info(self):
        user_settings = UserSettings()
        systemd_settings = user_settings.systemd
        self.assertIsInstance(systemd_settings, SystemdServiceInfo)

        # Check some samples:
        self.assertEqual(systemd_settings.template_context.verbose_service_name, 'Inverter Connect')
        self.assertEqual(systemd_settings.service_slug, 'inverter_connect')
        self.assertEqual(systemd_settings.template_context.syslog_identifier, 'inverter_connect')
        self.assertEqual(systemd_settings.service_file_path, Path('/etc/systemd/system/inverter_connect.service'))
