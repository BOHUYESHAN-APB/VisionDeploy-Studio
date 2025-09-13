#!/usr/bin/env python3
"""
Archived backup of temp/TMP/test_core.py
"""

#!/usr/bin/env python3
"""
核心功能测试脚本备份（archived）
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.environment_manager_simple import EnvironmentManager
from core.hardware_detector_fixed import HardwareDetector
from tools.create_test_model import create_yolov5s_test

def test_environment():
	print("🧪 test environment...")
	env_manager = EnvironmentManager()
	python_versions = env_manager.get_available_python_versions()
	print(f"📋 python versions: {python_versions}")
	return True

def test_hardware():
	print("\n🧪 test hardware...")
	detector = HardwareDetector()
	hardware_info = detector.detect_all()
	print(f"💻 CPU: {hardware_info['cpu']['name']}")
	return True

def test_model_download():
	print("\n🧪 test model download...")
	return True

if __name__ == "__main__":
	test_environment()
	test_hardware()
	test_model_download()
