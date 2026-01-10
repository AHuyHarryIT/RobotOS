#!/usr/bin/env python3
"""
Quick test script to verify Jetson calibration setup.
Checks all prerequisites before running the full calibration system.
"""

import os
import sys
import json
import pathlib
from dotenv import load_dotenv

def check_mark(passed):
    return "✅" if passed else "❌"

def test_python_version():
    """Check Python version >= 3.6"""
    major, minor = sys.version_info[:2]
    passed = (major >= 3 and minor >= 6)
    print(f"{check_mark(passed)} Python {major}.{minor} (need >= 3.6)")
    return passed

def test_imports():
    """Check if required packages are installed"""
    packages = {
        "cv2": "opencv-python",
        "numpy": "numpy",
        "zmq": "pyzmq",
        "dotenv": "python-dotenv"
    }
    
    all_passed = True
    for module, pip_name in packages.items():
        try:
            __import__(module)
            print(f"✅ {pip_name}")
        except ImportError:
            print(f"❌ {pip_name} - run: pip3 install {pip_name}")
            all_passed = False
    
    return all_passed

def test_env_file():
    """Check if .env file exists and has required variables"""
    env_path = pathlib.Path(".env")
    if not env_path.exists():
        print(f"❌ .env file not found")
        print("   Create it: cp .env.example .env")
        return False
    
    print(f"✅ .env file exists")
    
    load_dotenv()
    server_ip = os.getenv("SERVER_IP")
    server_port = os.getenv("SERVER_PORT")
    
    if not server_ip:
        print(f"❌ SERVER_IP not set in .env")
        return False
    print(f"✅ SERVER_IP = {server_ip}")
    
    if not server_port:
        print(f"❌ SERVER_PORT not set in .env")
        return False
    print(f"✅ SERVER_PORT = {server_port}")
    
    return True

def test_config_json():
    """Check if config.json exists"""
    config_path = pathlib.Path("config.json")
    if not config_path.exists():
        print(f"❌ config.json not found")
        return False
    
    try:
        with config_path.open("r") as f:
            cfg = json.load(f)
        print(f"✅ config.json loaded")
        
        # Check important keys
        if "CAM_DEVICE" in cfg:
            print(f"  Camera: {cfg['CAM_DEVICE']}")
        if "ACCEPTANCE" in cfg:
            print(f"  Acceptance: {cfg['ACCEPTANCE']}°")
        
        return True
    except Exception as e:
        print(f"❌ config.json invalid: {e}")
        return False

def test_roi_file():
    """Check if ROI points file exists"""
    roi_path = pathlib.Path("AUTO_CAR_V2/roi_points.txt")
    if not roi_path.exists():
        print(f"❌ ROI not configured (AUTO_CAR_V2/roi_points.txt missing)")
        print("   Setup: cd AUTO_CAR_V2 && python3 main.py")
        return False
    
    print(f"✅ ROI configured")
    return True

def test_auto_car_modules():
    """Check if AUTO_CAR_V2 modules exist"""
    modules = ["calibrate.py", "static_stop.py", "ROI.py", "helpers.py"]
    all_exist = True
    
    for mod in modules:
        mod_path = pathlib.Path(f"AUTO_CAR_V2/{mod}")
        if not mod_path.exists():
            print(f"❌ AUTO_CAR_V2/{mod} not found")
            all_exist = False
        else:
            print(f"✅ AUTO_CAR_V2/{mod}")
    
    return all_exist

def test_camera():
    """Test if camera can be opened"""
    try:
        import cv2 as cv
        
        # Try to load config to get camera device
        try:
            with open("config.json", "r") as f:
                cfg = json.load(f)
                cam_device = cfg.get("CAM_DEVICE", 0)
        except:
            cam_device = 0
        
        cap = cv.VideoCapture(cam_device)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret:
                print(f"✅ Camera {cam_device} works ({frame.shape})")
                return True
            else:
                print(f"❌ Camera {cam_device} opened but can't read frames")
                return False
        else:
            print(f"❌ Camera {cam_device} can't open")
            print(f"   Try: ls /dev/video*")
            return False
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return False

def test_network():
    """Test connection to miniPC client"""
    try:
        import zmq
        from dotenv import load_dotenv
        
        load_dotenv()
        server_ip = os.getenv("SERVER_IP", "192.168.1.100")
        server_port = os.getenv("SERVER_PORT", "5557")
        addr = f"tcp://{server_ip}:{server_port}"
        
        print(f"Testing connection to {addr}...")
        
        ctx = zmq.Context.instance()
        sock = ctx.socket(zmq.REQ)
        sock.setsockopt(zmq.RCVTIMEO, 2000)  # 2s timeout
        sock.setsockopt(zmq.SNDTIMEO, 2000)
        sock.connect(addr)
        
        # Try to send a test command
        sock.send_string("stop")
        reply = sock.recv()
        sock.close()
        
        print(f"✅ Connected to server at {addr}")
        print(f"   Reply: {reply.decode('utf-8')[:50]}")
        return True
        
    except zmq.Again:
        print(f"❌ Connection timeout - server not responding")
        print(f"   Is miniPC server running? Check docker ps on {server_ip}")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"   Check: ping {server_ip}")
        return False

def main():
    print("=" * 60)
    print("  JETSON CALIBRATION SYSTEM - SETUP TEST")
    print("=" * 60)
    print()
    
    results = {}
    
    print("📦 Checking Python and packages...")
    results['python'] = test_python_version()
    results['imports'] = test_imports()
    print()
    
    print("📁 Checking configuration files...")
    results['env'] = test_env_file()
    results['config'] = test_config_json()
    results['roi'] = test_roi_file()
    print()
    
    print("🔧 Checking AUTO_CAR_V2 modules...")
    results['modules'] = test_auto_car_modules()
    print()
    
    print("📷 Checking camera...")
    results['camera'] = test_camera()
    print()
    
    print("🌐 Checking network connection...")
    results['network'] = test_network()
    print()
    
    # Summary
    print("=" * 60)
    passed = sum(results.values())
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print()
        print("Ready to run:")
        print("  python3 calibration_main.py")
    else:
        print(f"⚠️  {passed}/{total} tests passed")
        print()
        print("Fix the issues above, then run this test again:")
        print("  python3 test_setup.py")
        print()
        print("For help, see:")
        print("  - QUICKSTART.md")
        print("  - README.md")
    
    print("=" * 60)
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
