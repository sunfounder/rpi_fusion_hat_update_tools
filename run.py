from i2c_iap_tool.app import IapToolApp
from globals.fusion_hat_globals import Fusion_HAT_Globals

if __name__ == '__main__':
    app = IapToolApp(globals=Fusion_HAT_Globals)
    app.run()