from bx_py_utils.test_utils.unittest_utils import BaseDocTests

import inverter
from inverter.tests.fixtures import NoColors


class DocTests(BaseDocTests):
    def test_doctests(self):
        with NoColors():
            self.run_doctests(
                modules=(inverter,),
            )
