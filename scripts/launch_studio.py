#!/usr/bin/env python3
# Copy of launch_studio.py

import sys
import os
import locale
from pathlib import Path

def setup_environment():
	try:
		if hasattr(sys.stdout, 'reconfigure') and callable(getattr(sys.stdout, 'reconfigure', None)):
			if sys.stdout.encoding != 'utf-8':
				sys.stdout.reconfigure(encoding='utf-8')
	except:
		pass

	try:
		locale.setlocale(locale.LC_ALL, 'zh_CN.UTF-8')
	except:
		try:
			locale.setlocale(locale.LC_ALL, 'Chinese_China.936')
		except:
			pass

	project_root = Path(__file__).parent.parent
	sys.path.insert(0, str(project_root))

def main():
	setup_environment()
	print("(scripts copy) Launch script. Use root launch_studio.py for production.")

if __name__ == "__main__":
	main()

