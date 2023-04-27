def convert_address_option(raw_address: str, debug: bool = True) -> int:
    """
    >>> convert_address_option(raw_address='0x123', debug=True)
    Address: 0x123
    291
    >>> convert_address_option(raw_address='456', debug=True)
    Address: 0x1c8
    456
    """
    if 'x' in raw_address:
        base = 16
    else:
        base = 10
    address = int(raw_address, base=base)
    if debug:
        print('Address:', hex(address))

    return address
