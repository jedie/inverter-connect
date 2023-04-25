from bx_py_utils.test_utils.unittest_utils import BaseDocTests

from inverter import mqtt4homeassistant


class DocTests(BaseDocTests):
    def test_doctests(self):
        self.run_doctests(
            modules=(mqtt4homeassistant,),
        )
