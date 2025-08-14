import os
import sys
import time
from i2c import I2C
from ui_tools import UiTools
from fusion_hat_globals import *

# change working directory to script directory
file_path = os.path.abspath(__file__)
file_dir = os.path.dirname(file_path)
os.chdir(file_dir)


firmware_files = []
FIRMWARE_DIR = "firmware"
for root, dirs, files in os.walk(FIRMWARE_DIR):
    print(root, dirs, files)
    for file in files:
        if file.endswith(".bin"):
            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, FIRMWARE_DIR)
            firmware_files.append(relative_path)
firmware_num = len(firmware_files)
chosen_firmware_index = 0

# print("Firmware files:")
# for i in range(firmware_num):
#     print(f"{i}: {firmware_files[i]}")
# exit()

app_i2c = I2C(addr=APP_I2C_ADDR, bus=1)
boot_i2c = I2C(addr=BOOT_I2C_ADDR, bus=1)


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
def check_boot_mode():
    if boot_i2c.is_ready():
        st = time.time()
        while time.time() - st < 5:
            # send ack
            boot_i2c._write_block_data(IAP_CMD_START, [IAP_CMD_ACK, 1, IAP_CMD_END])
            status = boot_i2c._read_byte()
            if status == IAP_OK:
                return True
            time.sleep(0.01)
        else:
            return False
    else:
        return False

def get_boot_verion():
    if app_i2c.is_ready():
        result = app_i2c._read_block_data(BOOT_VERSION_REG_ADDR, 3)
    elif boot_i2c.is_ready():
        result = boot_i2c._read_block_data(BOOT_VERSION_REG_ADDR_BOOT, 3)
    else:
        return None

    major = result[0]
    minor = result[1]
    patch = result[2]

    return f"{major}.{minor}.{patch}"

def get_app_verion():
    if app_i2c.is_ready():
        result = app_i2c._read_block_data(APP_VERSION_REG_ADDR, 3)
    elif boot_i2c.is_ready():
        result = boot_i2c._read_block_data(APP_VERSION_REG_ADDR_BOOT, 3)
    else:
        return None

    major = result[0]
    minor = result[1]
    patch = result[2]
    return f"{major}.{minor}.{patch}"

def get_factory_verion():
    if app_i2c.is_ready():
        result = app_i2c._read_block_data(FACTORY_VERSION_REG_ADDR, 3)
    elif boot_i2c.is_ready():
        result = boot_i2c._read_block_data(FACTORY_VERSION_REG_ADDR_BOOT, 3)
    else:
        return None

    major = result[0]
    minor = result[1]
    patch = result[2]
    return f"{major}.{minor}.{patch}"

def get_main_entry():
    if app_i2c.is_ready():
        result =  app_i2c._read_block_data(MIAN_ENTRY_REG_ADDR, 4)
    elif boot_i2c.is_ready():
        result =  boot_i2c._read_block_data(MIAN_ENTRY_REG_ADDR_BOOT, 4)
    else:
        return None
    
    _is_big = True
    if _is_big:
        result = result[0] << 24 | result[1] << 16 | result[2] << 8 | result[3]
    else:
        result = result[3] << 24 | result[2] << 16 | result[1] << 8 | result[0]
    return f'0x{result:08X}'

def enter_boot_mode():
    app_i2c._write_block_data(ADV_CMD_START, [ADV_CMD_ENTER_BOOT, 1, ADV_CMD_END])
    status = app_i2c._read_byte()
    if status != IAP_OK:
        return False
    # wait for device to enter iap mode, i2c change to 0x5d
    time.sleep(1)
    st = time.time()
    while time.time() - st < 5:
        if boot_i2c.is_ready():
           # send ack
           boot_i2c._write_block_data(IAP_CMD_START, [IAP_CMD_ACK, 1, IAP_CMD_END])
           status = boot_i2c._read_byte()
           if status == IAP_OK:
               return True
           time.sleep(0.01)
    else:
        return False


def app_reset_device():
    for _ in range(IAP_RETRY_TIMES):
        app_i2c._write_block_data(ADV_CMD_START, [ADV_CMD_RST, 1, ADV_CMD_END])
        status = app_i2c._read_byte()
        if status == IAP_OK:
            return True
    else:
        return False

def boot_reset_device():
    for _ in range(IAP_RETRY_TIMES):
        boot_i2c._write_block_data(IAP_CMD_START, [IAP_CMD_RST, 1, IAP_CMD_END])
        status = boot_i2c._read_byte()
        if status == IAP_OK:
            return True
    else:
        return False


def reset_device():
    if app_i2c.is_ready():
        return  app_reset_device()
    elif boot_i2c.is_ready():
        return boot_reset_device()
    else:
        return False
    

def earse_flash(file_size):
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

    addr = NEW_APP_START
    addr = addr.to_bytes(4, 'big')
    addr = list(addr)

    for x in addr:
        check_sum ^= x
    for x in page_num:
        check_sum ^= x


    _send_data = [IAP_CMD_START, IAP_CMD_EARSE, check_sum, _len] + addr + page_num + [IAP_CMD_END]

    for _ in range(IAP_RETRY_TIMES):
        boot_i2c._write_block_data(_send_data[0], _send_data[1:])
        _st = time.time()
        status = IAP_NACK_ERR
        while time.time() - _st < 5:
            try:
                status = boot_i2c._read_byte()
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

def burn_data(data, data_offset):
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
    ui.clear_xline(ui._height)
    ui.clear_xline(ui._height+1)
    _send_data_hex = ""
    for x in _send_data:
        _send_data_hex += f"{x:02X}, "
    _send_data_hex = _send_data_hex[:-2]
    ui.draw(f"send_data: {_send_data_hex}", location=(0, ui._height))

    status = IAP_NACK_ERR 
    for _ in range(IAP_RETRY_TIMES):
        boot_i2c._write_block_data(_send_data[0], _send_data[1:])
        _st = time.time()
        status = IAP_NACK_ERR
        while time.time() - _st < 5:
            try:
                status = boot_i2c._read_byte()
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
    
def verify_data(data):
    # | start | cmd | checksum | len | addr          | size          | flash_checksum | end |
    # | ----- | --- | -------- | --- | ------------- | ------------- | -------------- | --- |
    # | 0     | 1   | 2        | 3   | 4~7 (u32,Big) | 8~9 (u16,Big) | 10             | 11  |
    check_sum = 0
    _len = 7 # addr + size + flash_checksum

    # addr
    addr = NEW_APP_START
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
    boot_i2c._write_block_data(_send_data[0], _send_data[1:])
    status = boot_i2c._read_byte()
    if status == IAP_OK:
        return True
    else:
        return False

def restore_factory_firmware():
    # | start | cmd | value | end |
    # | ----- | --- | ------| --- |
    # | 0     | 1   | 2     | 3   |
    for _ in range(IAP_RETRY_TIMES):
        boot_i2c._write_block_data(IAP_CMD_START, [IAP_CMD_RST_FACTORY, 1, IAP_CMD_END])
        status = boot_i2c._read_byte()
        if status == IAP_OK:
            return True
    else:
        return False

# UI
# ==============================================================================
UI_WIDTH = 80
UI_HEIGHT = 15
ui = UiTools(width=UI_WIDTH, height=UI_HEIGHT)
#
OPTIONS_TIPS = {
    "location": (UI_WIDTH-24, 2),
    "content": [
        "[↑]      Select Up  ",
        "[↓]      Select Down",
        "[Enter]  OK",
        "[Esc]    Exit"
    ]
}
#
options_offset = 0

# -----------------------------------------------------------------
boot_version = None
app_version = None
factory_version = None
main_entry = None
app_entry = None

def get_basic_info():
    global boot_version, app_version, factory_version, main_entry, app_entry
    boot_version = get_boot_verion()
    app_version = get_app_verion()
    factory_version = get_factory_verion()
    main_entry = get_main_entry()

def display_basic_info(location=(UI_WIDTH-24, 8)):
    ui.draw(f"Boot Version: {boot_version}", location=location)
    ui.draw(f"App Version: {app_version}", location=(location[0], location[1]+1))
    ui.draw(f"Factory Version: {factory_version}", location=(location[0], location[1]+2))
    ui.draw(f"Main Entry: {main_entry}", location=(location[0], location[1]+4))

# -----------------------------------------------------------------
TITLE = "I2C IAP for Fusion HAT+"
OPERATIONS = [
    " Update Firmware",
    " Restore Factory Firmware",
    " Reset Device",
] 

UPATE_MODE = 0
RESTORE_MODE = 1
RESET_MODE = 2
    
def select_operation_handler():
    operation = 0
    # clear screen
    print(f"{ui.home}{ui.THEME_BGROUND_COLOR}{ui.clear}")
    # draw title
    ui.draw_title(TITLE)
    # draw options tips
    ui.draw(OPTIONS_TIPS['content'], location=OPTIONS_TIPS['location'])
    # draw basic info
    display_basic_info(location=(UI_WIDTH-24, 8))

    # draw options
    ui.draw_options(OPERATIONS, operation, location=(2, 2), box_width=35)

    # select operation
    while True:
        key = ui.inkey()
        if key.name == 'KEY_UP':
            operation = (operation - 1) % len(OPERATIONS)
        elif key.name == 'KEY_DOWN':
            operation = (operation + 1) % len(OPERATIONS)
        elif key.name == 'KEY_ENTER':
            return operation
        elif key.name == 'KEY_ESCAPE':
            exit()
        else:
            continue

        # draw options
        ui.draw_options(OPERATIONS, operation, location=(2, 2), box_width=35)

def enter_boot_mode_handler():
    # clear screen
    # print(f"{ui.home}{ui.THEME_BGROUND_COLOR}{ui.clear}")
    #
    ui.draw([
            "",
            " Entering bootloader ...",
            ""
            ],
            color=ui.THEME_CHOSEN_COLOR,
            location=(15, 5),
            box_width=50,
            align='center'
    )
    time.sleep(0.5)
    #
    status = enter_boot_mode()
    #
    if not status:
        ui.draw([
                "",
                " Entering bootloader ... Failed.",
                "",
                "press any key to exit.  "
                ],
                color=ui.white_on_red,
                location=(15, 5),
                box_width=50,
                align='center'
        )
        ui.inkey()
        return False
    else:
        return True

def select_firmware_handler():
    global chosen_firmware_index, options_offset

    # 
    OPTIONS_LIST_NUM = 8

    # clear screen
    print(f"{ui.home}{ui.THEME_BGROUND_COLOR}{ui.clear}")
    # draw title
    ui.draw_title("select firmware")
    # draw options tips
    ui.draw(OPTIONS_TIPS['content'], location=OPTIONS_TIPS['location'])
    # draw basic info
    display_basic_info(location=(UI_WIDTH-24, 8))

    # draw options
    if firmware_num > 0:
        _files  = firmware_files[options_offset:options_offset+OPTIONS_LIST_NUM]
        ui.draw_options(_files, chosen_firmware_index-options_offset, location=(2, 2), box_width=35)
        ui.draw(f"{chosen_firmware_index+1}/{firmware_num}", location=(45, 2), box_width=7, align='right')
    else:
        ui.draw("  No firmware found.", location=(5, 3))
        key = ui.inkey()
        exit()

    while True:
        key = ui.inkey()
        if key.name == 'KEY_UP':
            chosen_firmware_index = (chosen_firmware_index - 1) % firmware_num
        elif key.name == 'KEY_DOWN':
            chosen_firmware_index = (chosen_firmware_index + 1) % firmware_num
        elif key.name == 'KEY_ENTER':
            chosen_file = firmware_files[chosen_firmware_index]
            return chosen_file
        elif key.name == 'KEY_ESCAPE':
            exit()
        else:
            continue

        # draw options
        if chosen_firmware_index > options_offset+OPTIONS_LIST_NUM:
            options_offset = chosen_firmware_index - OPTIONS_LIST_NUM-1
            _files  = firmware_files[options_offset:options_offset+OPTIONS_LIST_NUM]
        elif chosen_firmware_index < options_offset:
            options_offset = chosen_firmware_index
            _files  = firmware_files[options_offset:options_offset+OPTIONS_LIST_NUM]
        ui.draw_options(_files, chosen_firmware_index-options_offset, location=(2, 2), box_width=35)
        ui.draw(f"{chosen_firmware_index+1}/{firmware_num}", location=(45, 2), box_width=7, align='right')

#
def burn_firmware_handler(file_path):
    # clear screen
    print(f"{ui.home}{ui.THEME_BGROUND_COLOR}{ui.clear}")
    # draw title
    ui.draw_title("burn firmware")
    #
    ui.draw(f"firmware: {file_path}", location=(2, 2))
    # check file
    file_size = os.path.getsize(file_path)
    ui.draw(f"    size: {file_size} bytes", location=(2, 3))
    if file_size > FIRMWARE_MAX_BYTES:
        ui.draw([
                "",
                f"error: file size is too large, max {FIRMWARE_MAX_BYTES} bytes. ",
                "",
                " press any key to exit. "
                ],
                color=ui.THEME_CHOSEN_COLOR,
                location=(15, 5),
                box_width=50,
                align='center'
        )
        ui.inkey()
        return

    # display basic info
    display_basic_info(location=(UI_WIDTH-24, 8))

    # burn firmware
    # ----------------------------------------------------------------------------
    ui.draw([
            "[Enter] Burn",
            "[Esc]   Exit",
            ],
            location=((UI_WIDTH-24, 2))
            )
    while True:
        key = ui.inkey()
        if key.name == 'KEY_ENTER':
            break
        elif key.name == 'KEY_ESCAPE':
            return

    with open(file_path, 'rb') as f:
        data = f.read()
    data = list(data)

    progress_perc = 0
    data_offset = 0
    data_len = len(data)
    is_ok = False

    # ---- erasing ----
    ui.draw(f"erasing ...", location=(0, ui._height-1))
    _status = earse_flash(data_len)
    if _status is True:
        ui.draw(f"OK", location=(14, ui._height-1), color=ui.green)
        time.sleep(1)
    else:
        ui.draw([
                f"error: erase flash failed. ",
                "",
                " press any key to exit. "
                ],
                color=ui.white_on_red,
                location=(15, 5),
                box_width=50,
                align='center'
        )
        ui.inkey()
        return

    # ---- burning ----
    ui.draw(f"burning: ", location=(0, ui._height-1))
    ui.draw_progress_bar(progress_perc, location=(9, ui._height-1), box_width=25)
    ui.draw(f"{data_offset}/{data_len} ", location=(42, ui._height-1))

    while True:
        if data_offset > data_len - IAP_DATA_LEN:
            send_data = data[data_offset:]
        else:
            send_data = data[data_offset:data_offset+IAP_DATA_LEN]
        #
        _status = burn_data(send_data, data_offset)
        if _status == IAP_OK:
            data_offset += IAP_DATA_LEN
            if data_offset > data_len:
                data_offset = data_len 
        else:
            is_ok = False
            break
        #
        progress_perc = int((data_offset)*100/data_len)
        if progress_perc > 100:
            progress_perc = 100
        ui.draw_progress_bar(progress_perc, location=(9, ui._height-1), box_width=25)
        ui.draw(f"{data_offset}/{data_len} ", location=(42, ui._height-1))

        #
        if progress_perc == 100:
            is_ok = True
            break
        #
        time.sleep(0.01)

    if is_ok:
        # ---- verify ----
        ui.draw(f"{' '*ui._width}", location=(0, ui._height-1))
        ui.draw(f"verifying ...", location=(0, ui._height-1))
        _status = verify_data(data)
        if _status is True:
            is_ok = True
            ui.draw(f"OK", location=(14, ui._height-1), color=ui.green)
        else:
            is_ok = False
            ui.draw([
                f"verify failed.  ",
                "",
                " press any key to exit. "
                ],
                color=ui.white_on_red,
                location=(15, 5),
                box_width=50,
                align='center'
                )
            ui.inkey()
            return          

    if is_ok:
        opt = ui.draw_ask([
                f"burn success. ",
                "",
                " Would you like to reboot the device? [y/n] "
                ],
                color=ui.white_on_green,
                location=(15, 5),
                box_width=50,
                align='center'
        )
        if opt is True:
            reset_device_handller()
        else:
            return
    else:
        ui.draw([
                f"burn failed. 0x{_status:02x} ",
                "",
                " press any key to exit. "
                ],
                color=ui.white_on_red,
                location=(15, 5),
                box_width=50,
                align='center'
        )
        ui.inkey()
        return

def update_mdoe_handler():
    is_boot_mode = check_boot_mode()
    if not is_boot_mode:
        status = enter_boot_mode_handler()
        if not status:
            return
    chosen_file = select_firmware_handler()
    burn_firmware_handler(chosen_file)

def restore_firmware_handler():
    # enter boot mode
    is_boot_mode = check_boot_mode()
    if not is_boot_mode:
        status = enter_boot_mode_handler()
        if not status:
            return
    # restore factory firmware
    status = restore_factory_firmware()
    #
    if status is True:
        opt = ui.draw_ask([
                f"restore factory firmware success. ",
                "",
                " Would you like to reboot the device? [y/n] "
                ],
                color=ui.white_on_green,
                location=(15, 5),
                box_width=50,
                align='center'
        )
        if opt is True:
            reset_device_handller()
        else:
            return
    else:
        ui.draw([
                f"restore factory firmware failed. ",
                "",
                " press any key to exit. "
                ],
                color=ui.white_on_red,
                location=(15, 5),
                box_width=50,
                align='center'
        )
        ui.inkey()
        return

def reset_device_handller():
    status = reset_device()
    if status:
        ui.draw([
                f"reset device success. ",
                "",
                " press any key to exit. "
                ],
                color=ui.white_on_green,
                location=(15, 5),
                box_width=50,
                align='center'
        )
    else:
        ui.draw([
                f"reset device failed.  ",
                "",
                " press any key to exit. "
                ],
                color=ui.white_on_red,
                location=(15, 5),
                box_width=50,
                align='center'
        )
    ui.inkey()
          
#
def loop():
    while True:
        get_basic_info()
        operation = select_operation_handler()
        if operation == UPATE_MODE:
            update_mdoe_handler()
        elif operation == RESTORE_MODE:
            restore_firmware_handler()  
        elif operation == RESET_MODE:
            opt = ui.draw_ask([
                "",
                f"Would you like to reboot the device? [y/n]",
                "",
                ],
                color=ui.white_on_green,
                location=(15, 5),
                box_width=50,
                align='center'
            )
            if opt is True:
                reset_device_handller()

def main():
    with ui.fullscreen(), ui.cbreak():
        try:
            loop()
        except KeyboardInterrupt:
            pass
        finally:
            if boot_i2c.is_ready():
                opt = ui.draw_ask([
                    "Would you like to reboot the device ",
                    f"to exit boot mode? [y/n]",
                    "",
                    ],
                    color=ui.white_on_green,
                    location=(15, 5),
                    box_width=50,
                    align='center'
                )
                if opt is True:
                    reset_device_handller()

if __name__ == "__main__":
    main()
