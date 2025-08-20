import os
import time
import traceback
import subprocess

from .ui_tools import UiTools
from .iap import Iap
from .iap import *

# change working directory to script directory
file_path = os.path.abspath(__file__)
file_dir = os.path.dirname(file_path)
os.chdir(file_dir)

firmware_files = []
FIRMWARE_DIR = "../firmware"
for root, dirs, files in os.walk(FIRMWARE_DIR):
    # print(root, dirs, files)
    for file in files:
        if file.endswith(".bin"):
            full_path = os.path.join(root, file)
            relative_path = os.path.relpath(full_path, FIRMWARE_DIR)
            firmware_files.append(relative_path)
firmware_num = len(firmware_files)

# print("Firmware files:")
# for i in range(firmware_num):
#     print(f"{i}: {firmware_files[i]}")
# exit()




UI_WIDTH = 80
UI_HEIGHT = 15

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


# -----------------------------------------------------------------
OPERATIONS = [
    " Update Firmware",
    " Restore Factory Firmware",
    " Reset Device",
] 

UPATE_MODE = 0
RESTORE_MODE = 1
RESET_MODE = 2

# -----------------------------------------------------------------
CONFLICT_SERVICES = [
    "pipower5.service",
    "pironman5.service",
]


def is_service_active(service_name):
    try:
        result = subprocess.run(
            ['sudo', 'systemctl', 'is-active', '--quiet', service_name],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            return True
        else:
            return False
    except Exception as e:
        return None

def stop_service(service_name):
    try:
        result = subprocess.run(
            ['sudo', 'systemctl', 'stop', service_name],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            return True
        else:
            return False
    except Exception as e:
        return None

# -----------------------------------------------------------------
class IapToolApp:
    def __init__(self, globals):
        self.globals = globals
        self.ui = UiTools(width=UI_WIDTH, height=UI_HEIGHT)
        self.iap = Iap(self.globals)

        self.boot_version = None
        self.app_version = None
        self.factory_version = None
        self.main_entry = None

        self.chosen_firmware_index = 0
        self.options_offset = 0

    # -----------------------------------------------------------------
    def get_basic_info(self):
        self.boot_version = self.iap.get_boot_verion()
        self.app_version = self.iap.get_app_verion()
        self.factory_version = self.iap.get_factory_verion()
        self.main_entry = self.iap.get_main_entry()

    def display_basic_info(self, location=(UI_WIDTH-24, 9)):
        self.ui.draw(f"Boot Version: {self.boot_version}", location=location)
        self.ui.draw(f"App Version: {self.app_version}", location=(location[0], location[1]+1))
        self.ui.draw(f"Factory Version: {self.factory_version}", location=(location[0], location[1]+2))
        self.ui.draw(f"Main Entry: {self.main_entry}", location=(location[0], location[1]+3))

    def display_currnet_mode(self, location=(UI_WIDTH-24, 7)):
        if self.iap.boot_i2c.is_ready():
            self.ui.draw(f" Current Mode: Boot ", color=self.ui.white_on_green, location=location)
        elif self.iap.app_i2c.is_ready():
            self.ui.draw(f" Current Mode: App ", color=self.ui.white_on_green, location=location)
        else:
            self.ui.draw(f" Disconnected ", color=self.ui.white_on_red, location=location)
        
    def select_operation_handler(self):
        operation = 0
        
        # get basic info
        self.get_basic_info()

        # clear screen
        print(f"{self.ui.home}{self.ui.THEME_BGROUND_COLOR}{self.ui.clear}")
        # draw title
        self.ui.draw_title(f"I2C IAP for {self.globals['NAME']}")
        # draw options tips
        self.ui.draw(OPTIONS_TIPS['content'], location=OPTIONS_TIPS['location'])
        # draw current mode
        self.display_currnet_mode(location=(UI_WIDTH-24, 7))
        # draw basic info
        self.display_basic_info(location=(UI_WIDTH-24, 9))

        # draw options
        self.ui.draw_options(OPERATIONS, operation, location=(2, 2), box_width=35)

        # select operation
        while True:
            key = self.ui.inkey()
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
            self.ui.draw_options(OPERATIONS, operation, location=(2, 2), box_width=35)

    def enter_boot_mode_handler(self):
        # clear screen
        # print(f"{self.ui.home}{self.ui.THEME_BGROUND_COLOR}{self.ui.clear}")
        #
        self.ui.draw([
                "",
                " Entering bootloader ...",
                ""
                ],
                color=self.ui.THEME_CHOSEN_COLOR,
                location=(15, 5),
                box_width=50,
                align='center'
        )
        time.sleep(0.5)
        #
        status = self.iap.enter_boot_mode()
        #
        if not status:
            self.ui.draw([
                    "",
                    " Entering bootloader ... Failed.",
                    "",
                    "press any key to exit.  "
                    ],
                    color=self.ui.white_on_red,
                    location=(15, 5),
                    box_width=50,
                    align='center'
            )
            self.ui.inkey()
            return False
        else:
            return True

    def select_firmware_handler(self):
        # 
        OPTIONS_LIST_NUM = 8

        # get basic info
        self.get_basic_info()

        # clear screen
        print(f"{self.ui.home}{self.ui.THEME_BGROUND_COLOR}{self.ui.clear}")
        # draw title
        self.ui.draw_title("select firmware")
        # draw options tips
        self.ui.draw(OPTIONS_TIPS['content'], location=OPTIONS_TIPS['location'])
        # draw current mode
        self.display_currnet_mode(location=(UI_WIDTH-24, 7))
        # draw basic info
        self.display_basic_info(location=(UI_WIDTH-24, 9))

        # draw options
        if firmware_num > 0:
            _files  = firmware_files[self.options_offset:self.options_offset+OPTIONS_LIST_NUM]
            self.ui.draw_options(_files, self.chosen_firmware_index-self.options_offset, location=(2, 2), box_width=35)
            self.ui.draw(f"{self.chosen_firmware_index+1}/{firmware_num}", location=(45, 2), box_width=7, align='right')
        else:
            self.ui.draw("  No firmware found.", location=(5, 3))
            key = self.ui.inkey()
            exit()

        while True:
            key = self.ui.inkey()
            if key.name == 'KEY_UP':
                self.chosen_firmware_index = (self.chosen_firmware_index - 1) % firmware_num
            elif key.name == 'KEY_DOWN':
                self.chosen_firmware_index = (self.chosen_firmware_index + 1) % firmware_num
            elif key.name == 'KEY_ENTER':
                chosen_file = firmware_files[self.chosen_firmware_index]
                return f"{FIRMWARE_DIR}/{chosen_file}"
            elif key.name == 'KEY_ESCAPE':
                exit()
            else:
                continue

            # draw options
            if self.chosen_firmware_index > self.options_offset+OPTIONS_LIST_NUM:
                self.options_offset = self.chosen_firmware_index - OPTIONS_LIST_NUM-1
                _files  = firmware_files[self.options_offset:self.options_offset+OPTIONS_LIST_NUM]
            elif self.chosen_firmware_index < self.options_offset:
                self.options_offset = self.chosen_firmware_index
                _files  = firmware_files[self.options_offset:self.options_offset+OPTIONS_LIST_NUM]
            self.ui.draw_options(_files, self.chosen_firmware_index-self.options_offset, location=(2, 2), box_width=35)
            self.ui.draw(f"{self.chosen_firmware_index+1}/{firmware_num}", location=(45, 2), box_width=7, align='right')

    #
    def burn_firmware_handler(self, file_path):
        # clear screen
        print(f"{self.ui.home}{self.ui.THEME_BGROUND_COLOR}{self.ui.clear}")
        # draw title
        self.ui.draw_title("burn firmware")
        #
        file_size = os.path.getsize(file_path)
        # 
        _file_str = [f"firmware: {file_path}", ]
        _file_str += [f"size: {file_size} bytes"]
        self.ui.draw(_file_str, location=(2, 2), box_width=50)
        # check file
        if file_size > self.globals["FIRMWARE_MAX_BYTES"]:
            self.ui.draw([
                    "",
                    f"error: file size is too large, max {self.globals['FIRMWARE_MAX_BYTES']} bytes. ",
                    "",
                    " press any key to exit. "
                    ],
                    color=self.ui.black_on_yellow,
                    location=(15, 5),
                    box_width=50,
                    align='center'
            )
            self.ui.inkey()
            return

        # draw current mode
        self.display_currnet_mode(location=(UI_WIDTH-24, 7))
        # display basic info
        self.display_basic_info(location=(UI_WIDTH-24, 9))

        # burn firmware
        # ----------------------------------------------------------------------------
        self.ui.draw([
                "[Enter] Burn",
                "[Esc]   Exit",
                ],
                location=((UI_WIDTH-24, 2))
                )
        while True:
            key = self.ui.inkey()
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
        self.ui.draw(f"erasing ...", location=(0, self.ui._height-1))
        _status = self.iap.earse_flash(data_len)
        if _status is True:
            self.ui.draw(f"OK", location=(14, self.ui._height-1), color=self.ui.green)
            time.sleep(1)
        else:
            self.ui.draw([
                    f"error: erase flash failed. ",
                    "",
                    " press any key to exit. "
                    ],
                    color=self.ui.white_on_red,
                    location=(15, 5),
                    box_width=50,
                    align='center'
            )
            self.ui.inkey()
            return

        # ---- burning ----
        self.ui.draw(f"burning: ", location=(0, self.ui._height-1))
        self.ui.draw_progress_bar(progress_perc, location=(9, self.ui._height-1), box_width=25)
        self.ui.draw(f"{data_offset}/{data_len} ", location=(42, self.ui._height-1))

        while True:
            if data_offset > data_len - IAP_DATA_LEN:
                send_data = data[data_offset:]
            else:
                send_data = data[data_offset:data_offset+IAP_DATA_LEN]
            #
            _status = self.iap.burn_data(self.ui, send_data, data_offset)
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
            self.ui.draw_progress_bar(progress_perc, location=(9, self.ui._height-1), box_width=25)
            self.ui.draw(f"{data_offset}/{data_len} ", location=(42, self.ui._height-1))

            #
            if progress_perc == 100:
                is_ok = True
                break
            #
            time.sleep(0.01)

        if is_ok:
            # ---- verify ----
            self.ui.draw(f"{' '*self.ui._width}", location=(0, self.ui._height-1))
            self.ui.draw(f"verifying ...", location=(0, self.ui._height-1))
            _status = self.iap.verify_data(data)
            if _status is True:
                is_ok = True
                self.ui.draw(f"OK", location=(14, self.ui._height-1), color=self.ui.green)
            else:
                is_ok = False
                self.ui.draw([
                    f"verify failed.  ",
                    "",
                    " press any key to exit. "
                    ],
                    color=self.ui.white_on_red,
                    location=(15, 5),
                    box_width=50,
                    align='center'
                    )
                self.ui.inkey()
                return          

        if is_ok:
            opt = self.ui.draw_ask([
                    f"burn success. ",
                    "",
                    " Would you like to reboot the device? [y/n] "
                    ],
                    color=self.ui.white_on_green,
                    location=(15, 5),
                    box_width=50,
                    align='center'
            )
            if opt is True:
                self.reset_device_handller()
            else:
                return
        else:
            self.ui.draw([
                    f"burn failed. 0x{_status:02x} ",
                    "",
                    " press any key to exit. "
                    ],
                    color=self.ui.white_on_red,
                    location=(15, 5),
                    box_width=50,
                    align='center'
            )
            self.ui.inkey()
            return

    def update_mdoe_handler(self):
        is_boot_mode = self.iap.check_boot_mode()
        if not is_boot_mode:
            status = self.enter_boot_mode_handler()
            if not status:
                return
        chosen_file = self.select_firmware_handler()
        self.burn_firmware_handler(chosen_file)

    def restore_firmware_handler(self):
        # enter boot mode
        is_boot_mode = self.iap.check_boot_mode()
        if not is_boot_mode:
            status = self.enter_boot_mode_handler()
            if not status:
                return
        # restore factory firmware
        status = self.iap.restore_factory_firmware()
        #
        if status is True:
            opt = self.ui.draw_ask([
                    f"restore factory firmware success. ",
                    "",
                    " Would you like to reboot the device? [y/n] "
                    ],
                    color=self.ui.white_on_green,
                    location=(15, 5),
                    box_width=50,
                    align='center'
            )
            if opt is True:
                self.reset_device_handller()
            else:
                return
        else:
            self.ui.draw([
                    f"restore factory firmware failed. ",
                    "",
                    " press any key to exit. "
                    ],
                    color=self.ui.white_on_red,
                    location=(15, 5),
                    box_width=50,
                    align='center'
            )
            self.ui.inkey()
            return

    def reset_device_handller(self):
        status = self.iap.reset_device()
        if status:
            self.ui.draw([
                    f"reset device success. ",
                    "",
                    " press any key to exit. "
                    ],
                    color=self.ui.white_on_green,
                    location=(15, 5),
                    box_width=50,
                    align='center'
            )
        else:
            self.ui.draw([
                    f"reset device failed.  ",
                    "",
                    " press any key to exit. "
                    ],
                    color=self.ui.white_on_red,
                    location=(15, 5),
                    box_width=50,
                    align='center'
            )
        self.ui.inkey()

    def check_conflict_service_hanlder(self):
        _active_conflict_service = []
        for _service in CONFLICT_SERVICES:
            if is_service_active(_service):
                _active_conflict_service.append(_service)
        if len(_active_conflict_service) > 0:
            # ----
            operation = 0
            # get basic info
            self.get_basic_info()

            # clear screen
            print(f"{self.ui.home}{self.ui.THEME_BGROUND_COLOR}{self.ui.clear}")
            # draw title
            self.ui.draw_title(f"I2C IAP for {self.globals['NAME']}")
            # draw options tips
            self.ui.draw(OPTIONS_TIPS['content'], location=OPTIONS_TIPS['location'])
            # draw current mode
            self.display_currnet_mode(location=(UI_WIDTH-24, 7))
            # draw basic info
            self.display_basic_info(location=(UI_WIDTH-24, 9))

            # draw options
            self.ui.draw_options(OPERATIONS, operation, location=(2, 2), box_width=35)

            # -----
            opt = self.ui.draw_ask([
                    "Detected services that may cause I2C conflicts. ",
                    f"{_active_conflict_service}",
                    "Do you want to close them? [y/n]",
                    "",
                    ],
                    color=self.ui.white_on_yellow,
                    location=(15, 5),
                    box_width=50,
                    align='center'
            )
            if opt is True:
                self.ui.draw([
                    "",
                    "Stopping services... ",
                    "",
                    "",
                    ],
                    color=self.ui.white_on_yellow,
                    location=(15, 5),
                    box_width=50,
                    align='center'
                )
                _cannot_stop_service = []
                for _service in _active_conflict_service:
                    _status = stop_service(_service)
                    if _status is False:
                        _cannot_stop_service.append(_service)
                if len(_cannot_stop_service) > 0:
                    self.ui.draw([
                        "Some services cannot be stopped. ",
                        f"{_cannot_stop_service}",
                        "Please close the conflict services manually to continue.",
                        "",
                        " press any key to exit. "
                        ],
                        color=self.ui.white_on_red,
                        location=(15, 5),
                        box_width=50,
                        align='center'
                    )
                    self.ui.inkey()
                    exit(0)

            else:
                self.ui.draw([
                    "Please close the conflict services to continue. ",
                    "",
                    " press any key to exit. ",
                    "",
                    ],
                    color=self.ui.black_on_gray,
                    location=(15, 5),
                    box_width=50,
                    align='center'
                )
                self.ui.inkey()
                exit(0)
    #
    # =============================================================
    def loop(self):
        while True:
            self.check_conflict_service_hanlder()
            operation = self.select_operation_handler()
            if operation == UPATE_MODE:
                self.update_mdoe_handler()
            elif operation == RESTORE_MODE:
                self.restore_firmware_handler()  
            elif operation == RESET_MODE:
                opt = self.ui.draw_ask([
                    "",
                    f"Would you like to reboot the device? [y/n]",
                    "",
                    ],
                    color=self.ui.white_on_green,
                    location=(15, 5),
                    box_width=50,
                    align='center'
                )
                if opt is True:
                    self.reset_device_handller()

    def run(self):
        track_str = ""
        with self.ui.fullscreen(), self.ui.cbreak():
            try:
                self.loop()
            except KeyboardInterrupt:
                pass
            except Exception as e:
                track_str = traceback.format_exc()
                self.ui.draw( [
                    f"error: {e}",
                    # f"{traceback.format_exc()}",
                    "",
                    " press any key to exit. "
                    ],
                    color=self.ui.white_on_red,
                    location=(5, 5),
                    box_width=70,
                    align='left'
                    )
                self.ui.inkey()
            finally:
                if self.iap.boot_i2c.is_ready():
                    opt = self.ui.draw_ask([
                        "Would you like to reboot the device ",
                        f"to exit boot mode? [y/n]",
                        "",
                        ],
                        color=self.ui.white_on_green,
                        location=(15, 5),
                        box_width=50,
                        align='center'
                    )
                    if opt is True:
                        self.reset_device_handller()
        print(track_str)




