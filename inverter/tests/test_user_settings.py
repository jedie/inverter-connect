import json
import tempfile
from pathlib import Path
from unittest import TestCase

from bx_py_utils.environ import OverrideEnviron
from bx_py_utils.path import assert_is_file
from bx_py_utils.test_utils.snapshot import assert_text_snapshot

from inverter.user_settings import migrate_old_settings


class UserSettingsTestCase(TestCase):
    def test_migrate_old_settings(self):
        with tempfile.TemporaryDirectory(prefix='test-inverter-connect') as temp_dir:
            temp_path = Path(temp_dir)
            with OverrideEnviron(HOME=temp_dir):
                assert Path('~').expanduser() == temp_path

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

                with self.assertLogs(logger=None) as logs:
                    migrate_old_settings()

                self.assertEqual(
                    logs.output,
                    [
                        f'INFO:root:Migrate old settings from: {temp_dir}/.inverter-connect',
                        f'INFO:root:Migrate settings to: {temp_dir}/.inverter-connect.toml',
                    ],
                )

            self.assertFalse(old_settings_path.is_file())
            new_settings_path = temp_path / '.inverter-connect.toml'
            assert_is_file(new_settings_path)
            new_settings_str = new_settings_path.read_text()

        self.assertIn('[mqtt]', new_settings_str)
        self.assertIn('host = "my-mosquitto.tld"', new_settings_str)
        self.assertIn('password = "NoSecurePassword"', new_settings_str)

        assert_text_snapshot(got=new_settings_str, extension='.toml')
