import importlib, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
try:
    m = importlib.import_module('app.gui_ctk')
    print('imported app.gui_ctk OK')
    App = getattr(m, 'MainApp', None)
    if App:
        inst = App()
        print('MainApp instantiated')
    else:
        print('MainApp not found')
except Exception as e:
    print('ERROR', e)
