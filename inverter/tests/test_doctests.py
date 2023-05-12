from bx_py_utils.test_utils.unittest_utils import BaseDocTests
from ha_services.cli_tools.test_utils.rich_test_utils import NoColorEnvRichClick

import inverter


class DocTests(BaseDocTests):
    def test_doctests(self):
        with NoColorEnvRichClick():
            self.run_doctests(
                modules=(inverter,),
            )
