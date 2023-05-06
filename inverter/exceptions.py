class ReadInverterError(RuntimeError):
    pass


class ModbusNoData(ReadInverterError):
    """
    Modbus register value is: 'no data' == ERROR_STR_NO_DATA
    """

    pass


class ModbusNoHexData(ModbusNoData):
    def __init__(self, data: str):
        self.data = data


class CrcError(ReadInverterError):
    pass


class ParseModbusValueError(ReadInverterError):
    pass


class ReadTimeout(ReadInverterError):
    pass


class ValidationError(AssertionError):
    """
    A readed inverter value is not valid.
    """

    pass
