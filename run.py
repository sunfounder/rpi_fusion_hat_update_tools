import os
import time
from ui_tools import UiTools
import traceback
from iap import *

# change working directory to script directory
file_path = os.path.abspath(__file__)
file_dir = os.path.dirname(file_path)
os.chdir(file_dir)


firmware_files = []
FIRMWARE_DIR = "firmware"
for root, dirs, files in os.walk(FIRMWARE_DIR):
    # print(root, dirs, files)
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

def display_basic_info(location=(UI_WIDTH-24, 9)):
    ui.draw(f"Boot Version: {boot_version}", location=location)
    ui.draw(f"App Version: {app_version}", location=(location[0], location[1]+1))
    ui.draw(f"Factory Version: {factory_version}", location=(location[0], location[1]+2))
    ui.draw(f"Main Entry: {main_entry}", location=(location[0], location[1]+3))

def display_currnet_mode(location=(UI_WIDTH-24, 7)):
    if boot_i2c.is_ready():
        ui.draw(f" Current Mode: Boot ", color=ui.white_on_green, location=location)
    elif app_i2c.is_ready():
        ui.draw(f" Current Mode: App ", color=ui.white_on_green, location=location)
    else:
        ui.draw(f" Disconnected ", color=ui.white_on_red, location=location)

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
    # draw current mode
    display_currnet_mode(location=(UI_WIDTH-24, 7))
    # draw basic info
    display_basic_info(location=(UI_WIDTH-24, 9))

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
    # draw current mode
    display_currnet_mode(location=(UI_WIDTH-24, 7))
    # draw basic info
    display_basic_info(location=(UI_WIDTH-24, 9))

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
            return f"{FIRMWARE_DIR}/{chosen_file}"
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
    file_size = os.path.getsize(file_path)
    # 
    _file_str = [f"firmware: {file_path}", ]
    _file_str += [f"size: {file_size} bytes"]
    ui.draw(_file_str, location=(2, 2), box_width=50)
    # check file
    if file_size > FIRMWARE_MAX_BYTES:
        ui.draw([
                "",
                f"error: file size is too large, max {FIRMWARE_MAX_BYTES} bytes. ",
                "",
                " press any key to exit. "
                ],
                color=ui.black_on_yellow,
                location=(15, 5),
                box_width=50,
                align='center'
        )
        ui.inkey()
        return

    # draw current mode
    display_currnet_mode(location=(UI_WIDTH-24, 7))
    # display basic info
    display_basic_info(location=(UI_WIDTH-24, 9))

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
        _status = burn_data(ui, send_data, data_offset)
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
# =============================================================
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
    track_str = ""
    with ui.fullscreen(), ui.cbreak():
        try:
            loop()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            track_str = traceback.format_exc()
            ui.draw( [
                f"error: {e}",
                # f"{traceback.format_exc()}",
                "",
                " press any key to exit. "
                ],
                color=ui.white_on_red,
                location=(5, 5),
                box_width=70,
                align='left'
                )
            ui.inkey()
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
    print(track_str)

if __name__ == "__main__":
    main()
