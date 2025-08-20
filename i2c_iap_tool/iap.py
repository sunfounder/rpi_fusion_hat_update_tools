import time
from .i2c import I2C

# =============================================================
# Enter boot mode
# | start | cmd | value | end |
# | ----- | --- | ------| --- |
# | 0     | 1   | 2     | 3   |
# - start：0xAC （I2C 高级指令）
# - cmd：0x04 （进入升级模式）
# - value：0x01 （True）
# - end：0xAE （结束）

ADV_CMD_START = 0xAC
ADV_CMD_END = 0xAE
ADV_CMD_OK = 0xE0
ADV_CMD_ERR = 0xEF

ADV_CMD_RST = 0x00
ADV_CMD_ENTER_BOOT = 0x04

# =============================================================
# IAP
# -------------
# ---------- Ack -------------
# | start | cmd | value | end |
# | ----- | --- | ------| --- |
# | 0     | 1   | 2     | 3   |
# - start：0xD0 （IAP command）
# - cmd：0xAC （ACK）
# - value：0x01 （True）
# - end：0xAE （end）

# ---------- Header ----------
# start | len | check_sum | firmware_size(2bytes, Big) | page_num | end
# - start: 0xDC
# - len: 3, firmware_size + page_num
# - check_sum:  check_sum of firmware_size and page_num
# - firmware_size: 2 bytes, Big endian
# - page_num: number of pages to be written (each page is 1K)
# - end: 0xED


PAGE_SIZE = 1024 # 1K
IAP_DATA_LEN = 24 # 4bytes aligned
IAP_RETRY_TIMES= 5

IAP_CMD_START = 0xD0
IAP_CMD_END = 0xED

IAP_CMD_ACK = 0xAC
IAP_CMD_RST = 0xAE
IAP_CMD_EARSE = 0xDC
IAP_CMD_WRITE = 0xDD
IAP_CMD_VERIFY = 0xDE
IAP_CMD_RST_FACTORY = 0xDF

IAP_OK = 0xE0
IAP_FAIL = 0xEF
IAP_CHECKSUM_ERR = 0xE1
IAP_SIZE_ERR = 0xE2
IAP_FLASH_ERR = 0xE3
IAP_4BYTES_ALIGN_ERR = 0xE4
IAP_DATA_ERR = 0xE5

IAP_NACK_ERR = 0xFF

# =============================================================

class Iap:
    def __init__(self, globals):
        self.globals = globals
        self.app_i2c = I2C(addr=self.globals["APP_I2C_ADDR"], bus=1)
        self.boot_i2c = I2C(addr=self.globals["BOOT_I2C_ADDR"], bus=1)

    def check_boot_mode(self):
        if self.boot_i2c.is_ready():
            st = time.time()
            while time.time() - st < 5:
                # send ack
                self.boot_i2c._write_block_data(IAP_CMD_START, [IAP_CMD_ACK, 1, IAP_CMD_END])
                status = self.boot_i2c._read_byte()
                if status == IAP_OK:
                    return True
                time.sleep(0.01)
            else:
                return False
        else:
            return False

    def get_boot_verion(self):
        if self.app_i2c.is_ready():
            result = self.app_i2c._read_block_data(self.globals["BOOT_VERSION_REG_ADDR"], 3)
        elif self.boot_i2c.is_ready():
            result = self.boot_i2c._read_block_data(self.globals["BOOT_VERSION_REG_ADDR_BOOT"], 3)
        else:
            return None

        major = result[0]
        minor = result[1]
        patch = result[2]

        return f"{major}.{minor}.{patch}"

    def get_app_verion(self):
        if self.app_i2c.is_ready():
            result = self.app_i2c._read_block_data(self.globals["APP_VERSION_REG_ADDR"], 3)
        elif self.boot_i2c.is_ready():
            result = self.boot_i2c._read_block_data(self.globals["APP_VERSION_REG_ADDR_BOOT"], 3)
        else:
            return None

        major = result[0]
        minor = result[1]
        patch = result[2]
        return f"{major}.{minor}.{patch}"

    def get_factory_verion(self):
        if self.app_i2c.is_ready():
            result = self.app_i2c._read_block_data(self.globals["FACTORY_VERSION_REG_ADDR"], 3)
        elif self.boot_i2c.is_ready():
            result = self.boot_i2c._read_block_data(self.globals["FACTORY_VERSION_REG_ADDR_BOOT"], 3)
        else:
            return None

        major = result[0]
        minor = result[1]
        patch = result[2]
        return f"{major}.{minor}.{patch}"

    def get_main_entry(self):
        if self.app_i2c.is_ready():
            result =  self.app_i2c._read_block_data(self.globals["MIAN_ENTRY_REG_ADDR"], 4)
        elif self.boot_i2c.is_ready():
            result =  self.boot_i2c._read_block_data(self.globals["MIAN_ENTRY_REG_ADDR_BOOT"], 4)
        else:
            return None
        
        _is_big = True
        if _is_big:
            result = result[0] << 24 | result[1] << 16 | result[2] << 8 | result[3]
        else:
            result = result[3] << 24 | result[2] << 16 | result[1] << 8 | result[0]
        return f'0x{result:08X}'

    def enter_boot_mode(self):
        self.app_i2c._write_block_data(ADV_CMD_START, [ADV_CMD_ENTER_BOOT, 1, ADV_CMD_END])
        time.sleep(0.1)
        status = self.app_i2c._read_byte()
        if status != IAP_OK:
            return False
        # wait for device to enter iap mode, i2c change to 0x5d
        time.sleep(1)
        st = time.time()
        while time.time() - st < 5:
            if self.boot_i2c.is_ready():
                # send ack
                self.boot_i2c._write_block_data(IAP_CMD_START, [IAP_CMD_ACK, 1, IAP_CMD_END])
                status = self.boot_i2c._read_byte()
                if status == IAP_OK:
                    return True
                time.sleep(0.01)
        else:
            return False

    def app_reset_device(self):
        for _ in range(IAP_RETRY_TIMES):
            self.app_i2c._write_block_data(ADV_CMD_START, [ADV_CMD_RST, 1, ADV_CMD_END])
            status = self.app_i2c._read_byte()
            if status == IAP_OK:
                return True
        else:
            return False

    def boot_reset_device(self):
        for _ in range(IAP_RETRY_TIMES):
            self.boot_i2c._write_block_data(IAP_CMD_START, [IAP_CMD_RST, 1, IAP_CMD_END])
            status = self.boot_i2c._read_byte()
            if status == IAP_OK:
                return True
        else:
            return False


    def reset_device(self):
        if self.app_i2c.is_ready():
            return self.app_reset_device()
        elif self.boot_i2c.is_ready():
            return self.boot_reset_device()
        else:
            return False
        

    def earse_flash(self, file_size):
        # | start | cmd | checksum | len | addr             | page_num     | end |
        # | ----- | --- | -------- | --- | ---------------- | ------------- | --- |
        # | 0     | 1   | 2        | 3   | 4~7 （u32, Big） | 8~9(u16, Big) | 10  |
        check_sum = 0
        _len = 6 
    
        if file_size % PAGE_SIZE != 0:
            page_num = file_size // PAGE_SIZE + 1
        else:
            page_num = file_size // PAGE_SIZE
        page_num = page_num.to_bytes(2, 'big')
        page_num = list(page_num)

        addr = self.globals["NEW_APP_START"]
        addr = addr.to_bytes(4, 'big')
        addr = list(addr)

        for x in addr:
            check_sum ^= x
        for x in page_num:
            check_sum ^= x

        _send_data = [IAP_CMD_START, IAP_CMD_EARSE, check_sum, _len] + addr + page_num + [IAP_CMD_END]

        for _ in range(IAP_RETRY_TIMES):
            self.boot_i2c._write_block_data(_send_data[0], _send_data[1:])
            _st = time.time()
            status = IAP_NACK_ERR
            while time.time() - _st < 5:
                try:
                    status = self.boot_i2c._read_byte()
                    break
                except TimeoutError:
                    pass
                time.sleep(0.01)
            
            # print(f"\nearse status: {status:#02x}")
            # print(f"page_num: {page_num}")
            if status == IAP_OK:
                return True
        else:
            return False

    def burn_data(self, ui_obj, data, data_offset):
        # | start | cmd | checksum | len  | data_offset    | data | end |
        # | ----- | --- | -------- | ---- | -------------- | ---- | --- |
        # | 0     | 1   | 2        | 3    | 4~5（u16,Big） | 6... | -1  |
        check_sum = 0
        
        # 4 bytes aligned
        data_len = len(data) 
        if data_len % 4 != 0:
            data += [0xFF]*(4-(data_len%4))

        #
        data_len = len(data)
        _len = data_len + 2 # data_offset + data

        data_offset = data_offset.to_bytes(2, 'big')
        data_offset = list(data_offset)
        
        for x in data_offset:
            check_sum ^= x
        for x in data:
            check_sum ^= x

        _send_data = [IAP_CMD_START, IAP_CMD_WRITE, check_sum, _len] + data_offset + data + [IAP_CMD_END]
        ui_obj.clear_xline(ui_obj._height)
        ui_obj.clear_xline(ui_obj._height+1)
        _send_data_hex = ""
        for x in _send_data:
            _send_data_hex += f"{x:02X}, "
        _send_data_hex = _send_data_hex[:-2]
        ui_obj.draw(f"send_data: {_send_data_hex}", location=(0, ui_obj._height))

        status = IAP_NACK_ERR 
        for _ in range(IAP_RETRY_TIMES):
            self.boot_i2c._write_block_data(_send_data[0], _send_data[1:])
            _st = time.time()
            status = IAP_NACK_ERR
            while time.time() - _st < 5:
                try:
                    status = self.boot_i2c._read_byte()
                    break
                except TimeoutError:
                    pass
                time.sleep(0.01)

            # print(f"\nburn status: {status:#02x}")

            # if status == IAP_OK:
            #     return True
            return status
        else:
            return status
        
    def verify_data(self, data):
        # | start | cmd | checksum | len | addr          | size          | flash_checksum | end |
        # | ----- | --- | -------- | --- | ------------- | ------------- | -------------- | --- |
        # | 0     | 1   | 2        | 3   | 4~7 (u32,Big) | 8~9 (u16,Big) | 10             | 11  |
        check_sum = 0
        _len = 7 # addr + size + flash_checksum

        # addr
        addr = self.globals["NEW_APP_START"]
        addr = addr.to_bytes(4, 'big')
        addr = list(addr)
        # size
        firmware_check_sum = 0
        firmware_size = len(data).to_bytes(2, 'big')
        firmware_size = list(firmware_size)
        # flash_checksum
        for x in data:
            firmware_check_sum ^= x
        # checksum
        for x in addr:
            check_sum ^= x
        for x in firmware_size:
            check_sum ^= x
        check_sum ^= firmware_check_sum
        #
        _send_data = [IAP_CMD_START, IAP_CMD_VERIFY, check_sum, _len] + addr + firmware_size + [firmware_check_sum] + [IAP_CMD_END]
        self.boot_i2c._write_block_data(_send_data[0], _send_data[1:])
        status = self.boot_i2c._read_byte()
        if status == IAP_OK:
            return True
        else:
            return False

    def restore_factory_firmware(self):
        # | start | cmd | value | end |
        # | ----- | --- | ------| --- |
        # | 0     | 1   | 2     | 3   |
        for _ in range(IAP_RETRY_TIMES):
            self.boot_i2c._write_block_data(IAP_CMD_START, [IAP_CMD_RST_FACTORY, 1, IAP_CMD_END])
            status = self.boot_i2c._read_byte()
            if status == IAP_OK:
                return True
        else:
            return False
