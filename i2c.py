from smbus2 import SMBus

class I2C():
    MASTER = 0
    SLAVE  = 1
    RETRY = 5

    def __init__(self, addr, bus=1):     
        self._bus = bus
        self._addr = addr
        self._smbus = SMBus(self._bus)

    def _write_byte(self, data):                      # i2C write function
        return self._smbus.write_byte(self._addr, data)

    def _write_byte_data(self, reg, data):
        return self._smbus.write_byte_data(self._addr, reg, data)

    def _write_word_data(self, reg, data):
        return self._smbus.write_word_data(self._addr, reg, data)

    def _write_block_data(self, reg, data):
        return self._smbus.write_i2c_block_data(self._addr, reg, data)

    def _read_byte(self):                             # i2C read functions
        return self._smbus.read_byte(self._addr)

    def _read_byte_data(self, reg):
        result = self._smbus.read_byte_data(self._addr, reg)
        return result

    def _read_word_data(self, reg):
        result = self._smbus.read_word_data(self._addr, reg)
        result_list = [result & 0xFF, (result >> 8) & 0xFF]
        return result_list
    
    def _read_block_data(self, reg, num):
        return self._smbus.read_i2c_block_data(self._addr, reg, num)

    def is_ready(self):
        addresses = I2C.scan(self._bus)
        if self._addr in addresses:
            return True
        else:
            return False

    @staticmethod
    def enabled(bus=1):
        import os
        return os.path.exists("/dev/i2c-{}".format(bus))

    @staticmethod
    def scan(busnum=1, force=False):
        devices = []
        for addr in range(0x03, 0x77 + 1):
            read = SMBus.read_byte, (addr,), {'force':force}
            write = SMBus.write_byte, (addr, 0), {'force':force}
            for func, args, kwargs in (read, write):
                try:
                    with SMBus(busnum) as bus:
                        data = func(bus, *args, **kwargs)
                        devices.append(addr)
                        break
                except OSError as expt:
                    if expt.errno == 16:
                        # just busy, maybe permanent by a kernel driver or just temporary by some user code
                        pass
        return devices

    def send(self, send, timeout=0):                      # sending data. `send`: data to be sent, `addr`: receiver's address 
        if isinstance(send, bytearray):
            data_all = list(send)
        elif isinstance(send, int):
            data_all = []
            d = "{:X}".format(send)
            d = "{}{}".format("0" if len(d)%2 == 1 else "", d)  
            for i in range(len(d)-2, -1, -2):                   # taking two chars in each iteration from right to left 
                tmp = int(d[i:i+2], 16)                         # convert 2-digit decimal to hex
                data_all.append(tmp)                            
            data_all.reverse()
        elif isinstance(send, list):
            data_all = send
        else:
            raise ValueError("send data must be int, list, or bytearray, not {}".format(type(send)))

        if len(data_all) == 1:                    
            data = data_all[0]
            self._write_byte(data)
        elif len(data_all) == 2:                   
            reg = data_all[0]
            data = data_all[1]
            self._write_byte_data( reg, data)
        elif len(data_all) == 3:                    
            reg = data_all[0]
            data = (data_all[2] << 8) + data_all[1]
            self._write_word_data(reg, data)
        else:
            reg = data_all[0]
            data = list(data_all[1:])
            self._write_block_data(reg, data)

    def recv(self, recv, timeout=0):                 # receive data
        if isinstance(recv, int):                               # convert `recv` to bytearray
            result = bytearray(recv)
        elif isinstance(recv, bytearray):
            result = recv
        else:
            return False
        for i in range(len(result)):
            result[i] = self._read_byte()
        return result

    def mem_write(self, data, memaddr, timeout=5000, addr_size=8): # memaddr match to chn
        if isinstance(data, bytearray):
            data_all = list(data)
        elif isinstance(data, list):
            data_all = data
        elif isinstance(data, int):
            data_all = []
            data = "%x"%data
            if len(data) % 2 == 1:
                data = "0" + data
            for i in range(0, len(data), 2):
                data_all.append(int(data[i:i+2], 16))
        else:
            raise ValueError("memery write require arguement of bytearray, list, int less than 0xFF")
        self._write_block_data(memaddr, data_all)

    def mem_read(self, data, memaddr, timeout=5000, addr_size=8):  # read data
        if isinstance(data, int):
            num = data
        elif isinstance(data, bytearray):
            num = len(data)
        else:
            return False
        result = bytearray(self._read_block_data( memaddr, num))
        return result

    def readfrom_mem_into(self, memaddr, buf):
        buf = self.mem_read(len(buf), memaddr)
        return buf

    def writeto_mem(self, memaddr, data):
        self.mem_write(data, memaddr)
