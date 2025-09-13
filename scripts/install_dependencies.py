"""
Copy of top-level install_dependencies.py for convenience.
Do not import this copy from code; it's a maintenance helper.
"""

#!/usr/bin/env python3
import subprocess
import sys
import platform
import os
from pathlib import Path

def install_package(package, index_url=None, extra_index_url=None):
	try:
		cmd = [sys.executable, "-m", "pip", "install", package]
		if index_url:
			cmd.extend(["--index-url", index_url])
		if extra_index_url:
			cmd.extend(["--extra-index-url", extra_index_url])
		subprocess.check_call(cmd)
		print(f"✅ {package} installed")
		return True
	except subprocess.CalledProcessError as e:
		print(f"❌ {package} install failed: {e}")
		return False

def detect_china_network():
	try:
		import urllib.request
		urllib.request.urlopen("https://www.google.com", timeout=3)
		return False
	except:
		try:
			import urllib.request
			urllib.request.urlopen("https://www.baidu.com", timeout=3)
			return True
		except:
			return False

def main():
	print("🔍 Checking and installing dependencies...")
	is_china = detect_china_network()
	if is_china:
		index_url = "https://mirrors.aliyun.com/pypi/simple/"
		torch_extra_url = "https://download.pytorch.org/whl/cu118"
	else:
		index_url = "https://pypi.org/simple/"
		torch_extra_url = "https://download.pytorch.org/whl/cu118"

	required_packages = [
		"dearpygui",
		"psutil",
		"requests",
		"Pillow",
		"PyYAML",
		"GPUtil",
		"pynvml",
	]

	failed_packages = []
	for package in required_packages:
		if not install_package(package, index_url):
			failed_packages.append(package)

	if failed_packages:
		print("\n❌ Some packages failed to install:")
		for p in failed_packages:
			print(f" - {p}")
	else:
		print("\n🎉 All dependencies installed")

if __name__ == "__main__":
	main()

