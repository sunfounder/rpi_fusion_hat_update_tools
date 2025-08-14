'''

'''

# global variables
APP_I2C_ADDR = 0x17
BOOT_I2C_ADDR = 0x5d

#
BOARD_ID_REG_ADDR = 3 # 3: id_h, 4: id_l
                      # Fusion Hat: 1908
APP_VERSION_REG_ADDR = 5 # 5: major, 6: minor, 7, patch                                                                     |
BOOT_VERSION_REG_ADDR = 207 # 207: major, 208: minor, 209, patch
FACTORY_VERSION_REG_ADDR = 204 # 204: major, 205: minor, 206, patch
MIAN_ENTRY_REG_ADDR = 200 # 200~203: bit3 ~ bit0

#
BOOT_VERSION_REG_ADDR_BOOT = 0
FACTORY_VERSION_REG_ADDR_BOOT = 3
APP_VERSION_REG_ADDR_BOOT = 6
BOOT_MODE_BOOT = 9
MIAN_ENTRY_REG_ADDR_BOOT = 10

#
FACTORY_APP_MODE = 0
NEW_APP_MODE = 1
UPGRADE_MODE = 2
#
NEW_APP_START = 0x08008000


# config max bytes for firmware
FIRMWARE_MAX_BYTES = 24*1024 # 24K

