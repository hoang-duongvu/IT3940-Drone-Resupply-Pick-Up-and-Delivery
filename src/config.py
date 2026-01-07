"""
Configuration - Đọc các tham số từ biến môi trường
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file từ thư mục gốc project
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


def get_env_float(key: str, default: float) -> float:
    """Đọc biến môi trường dạng float"""
    value = os.getenv(key)
    return float(value) if value is not None else default


def get_env_int(key: str, default: int) -> int:
    """Đọc biến môi trường dạng int"""
    value = os.getenv(key)
    return int(value) if value is not None else default


# ==================== CONFIGURATION ====================

# Depot
DEPOT_X = get_env_float('DEPOT_X', 10.0)
DEPOT_Y = get_env_float('DEPOT_Y', 10.0)
DEPOT_POS = (DEPOT_X, DEPOT_Y)

# Truck parameters
TRUCK_CAPACITY = get_env_int('TRUCK_CAPACITY', 50)          # packages
TRUCK_SPEED = get_env_float('TRUCK_SPEED', 30.0)            # km/h
TRUCK_SERVICE_TIME = get_env_float('TRUCK_SERVICE_TIME', 3.0)  # min
TRUCK_RECEIVE_TIME = get_env_float('TRUCK_RECEIVE_TIME', 5.0)  # min (δt)

# Drone parameters
DRONE_CAPACITY = get_env_int('DRONE_CAPACITY', 10)          # packages
DRONE_SPEED = get_env_float('DRONE_SPEED', 60.0)            # km/h
DRONE_FLIGHT_TIME = get_env_float('DRONE_FLIGHT_TIME', 90.0)  # min
DRONE_HANDLING_TIME = get_env_float('DRONE_HANDLING_TIME', 5.0)  # min

# Fleet size
NUM_TRUCKS = get_env_int('NUM_TRUCKS', 2)
NUM_DRONES = get_env_int('NUM_DRONES', 2)


def print_config():
    """In cấu hình hiện tại"""
    print("=" * 50)
    print("           CONFIGURATION")
    print("=" * 50)
    print(f"Depot: {DEPOT_POS}")
    print(f"Truck: capacity={TRUCK_CAPACITY}, speed={TRUCK_SPEED} km/h")
    print(f"       service_time={TRUCK_SERVICE_TIME} min, receive_time={TRUCK_RECEIVE_TIME} min")
    print(f"Drone: capacity={DRONE_CAPACITY}, speed={DRONE_SPEED} km/h")
    print(f"       flight_time={DRONE_FLIGHT_TIME} min, handling_time={DRONE_HANDLING_TIME} min")
    print(f"Fleet: {NUM_TRUCKS} trucks, {NUM_DRONES} drones")
    print("=" * 50)