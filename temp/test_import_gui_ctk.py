"""Local test: import and setup app.gui_ctk without entering GUI mainloop.

Run manually when ready (do not run in automated terminal here per instructions):

python temp/test_import_gui_ctk.py

The script will only import the module and call MainApp.setup(), not start
any mainloop. It's safe to run interactively.
"""

import importlib
import traceback

try:
    m = importlib.import_module('app.gui_ctk')
    print('imported app.gui_ctk OK')
    MainApp = getattr(m, 'MainApp', None)
    if MainApp is None:
        print('MainApp not found in app.gui_ctk')
    else:
        try:
            app = MainApp()
            app.setup()
            print('MainApp.setup() succeeded (no mainloop started)')
        except Exception as e:
            print('MainApp.setup() failed:')
            traceback.print_exc()
except Exception:
    print('Failed to import app.gui_ctk:')
    traceback.print_exc()
