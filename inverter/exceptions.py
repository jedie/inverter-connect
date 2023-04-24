class ReadInverterError(RuntimeError):
    pass


class ModbusNoData(ReadInverterError):
    """
    Modbus register value is: 'no data' == ERROR_STR_NO_DATA
    """

    pass


class CrcError(ReadInverterError):
    pass


class ParseModbusValueError(ReadInverterError):
    pass


class ReadTimeout(ReadInverterError):
    pass
