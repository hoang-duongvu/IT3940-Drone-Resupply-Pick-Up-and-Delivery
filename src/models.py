"""
Models cho bài toán Drone Resupply Pick-up Delivery
"""
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from enum import Enum

try:
    from .config import (
        DEPOT_POS,
        TRUCK_CAPACITY, TRUCK_SPEED, TRUCK_SERVICE_TIME, TRUCK_RECEIVE_TIME,
        DRONE_CAPACITY, DRONE_SPEED, DRONE_FLIGHT_TIME, DRONE_HANDLING_TIME,
        NUM_TRUCKS, NUM_DRONES
    )
except ImportError:
    from config import (
        DEPOT_POS,
        TRUCK_CAPACITY, TRUCK_SPEED, TRUCK_SERVICE_TIME, TRUCK_RECEIVE_TIME,
        DRONE_CAPACITY, DRONE_SPEED, DRONE_FLIGHT_TIME, DRONE_HANDLING_TIME,
        NUM_TRUCKS, NUM_DRONES
    )


# ==================== CONSTANTS ====================
class CustomerType(Enum):
    D = "D"      # Delivery từ depot (C1)
    P = "P"      # Pickup (C2)
    DL = "DL"    # Delivery của cặp pickup-delivery (C2)


# ==================== DATA CLASSES ====================
@dataclass
class Customer:
    """Thông tin khách hàng"""
    id: int
    x: float
    y: float
    ctype: CustomerType
    ready_time: float  # Thời gian gói hàng sẵn sàng
    pair_id: int       # ID cặp pickup-delivery (0 nếu là C1)
    weight: int = 1    # Trọng lượng gói hàng (mặc định = 1)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if not isinstance(other, Customer):
            return False
        return self.id == other.id

    def __repr__(self):
        return f"Customer({self.id}, {self.ctype.value}, rt={self.ready_time})"


@dataclass
class Problem:
    """Dữ liệu bài toán"""
    customers: Dict[int, Customer]  # id → Customer
    c1_customers: List[int]         # IDs khách hàng loại C1 (D)
    c2_pairs: List[Tuple[int, int]] # Các cặp (pickup_id, delivery_id)
    depot: Tuple[float, float] = DEPOT_POS

    def get_customer(self, cid: int) -> Customer:
        return self.customers[cid]

    def get_position(self, cid: int) -> Tuple[float, float]:
        """Lấy tọa độ (0 = depot)"""
        if cid == 0:
            return self.depot
        return (self.customers[cid].x, self.customers[cid].y)

    def manhattan_distance(self, c1_id: int, c2_id: int) -> float:
        """Khoảng cách Manhattan (cho truck)"""
        x1, y1 = self.get_position(c1_id)
        x2, y2 = self.get_position(c2_id)
        return abs(x2 - x1) + abs(y2 - y1)

    def euclidean_distance(self, c1_id: int, c2_id: int) -> float:
        """Khoảng cách Euclidean (cho drone)"""
        x1, y1 = self.get_position(c1_id)
        x2, y2 = self.get_position(c2_id)
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

    def truck_travel_time(self, c1_id: int, c2_id: int) -> float:
        """Thời gian di chuyển của truck (phút)"""
        dist = self.manhattan_distance(c1_id, c2_id)
        return (dist / TRUCK_SPEED) * 60

    def drone_travel_time(self, c1_id: int, c2_id: int) -> float:
        """Thời gian bay của drone (phút)"""
        dist = self.euclidean_distance(c1_id, c2_id)
        return (dist / DRONE_SPEED) * 60


# ==================== SOLUTION COMPONENTS ====================
@dataclass
class Trip:
    """
    Một trip của truck: bắt đầu và kết thúc tại depot
    route = [0, c1, c2, c3, ..., 0]
    """
    route: List[int] = field(default_factory=lambda: [0, 0])

    def customers(self) -> List[int]:
        """Trả về danh sách khách hàng (không gồm depot)"""
        return [c for c in self.route if c != 0]

    def insert(self, position: int, customer_id: int):
        """Chèn khách hàng vào vị trí (1 <= position <= len-1)"""
        self.route.insert(position, customer_id)

    def remove(self, customer_id: int):
        """Xóa khách hàng khỏi trip"""
        if customer_id in self.route:
            self.route.remove(customer_id)

    def is_empty(self) -> bool:
        """Trip rỗng nếu chỉ có [0, 0]"""
        return len(self.route) == 2

    def __len__(self):
        return len(self.route)

    def copy(self) -> 'Trip':
        return Trip(route=self.route.copy())

    def __repr__(self):
        return f"Trip({self.route})"


@dataclass
class TruckRoute:
    """
    Lộ trình của một truck: gồm nhiều trips
    """
    truck_id: int
    trips: List[Trip] = field(default_factory=list)

    def add_trip(self, trip: Trip):
        self.trips.append(trip)

    def all_customers(self) -> List[int]:
        """Tất cả khách hàng trong tất cả trips"""
        result = []
        for trip in self.trips:
            result.extend(trip.customers())
        return result

    def find_customer_position(self, customer_id: int) -> Optional[Tuple[int, int]]:
        """Tìm vị trí (trip_idx, position_in_trip) của khách hàng"""
        for trip_idx, trip in enumerate(self.trips):
            if customer_id in trip.route:
                pos = trip.route.index(customer_id)
                return (trip_idx, pos)
        return None

    def copy(self) -> 'TruckRoute':
        return TruckRoute(
            truck_id=self.truck_id,
            trips=[t.copy() for t in self.trips]
        )

    def __repr__(self):
        return f"TruckRoute(id={self.truck_id}, trips={self.trips})"


@dataclass
class Mission:
    """
    Một mission của drone: bay từ depot đến điểm gặp truck rồi quay về
    - meet_point: ID khách hàng nơi gặp truck
    - truck_id: ID truck được resupply
    - packages: Danh sách ID các package mang theo
    """
    meet_point: int              # Customer ID nơi gặp truck (0 = depot)
    truck_id: int                # Truck được resupply
    packages: List[int] = field(default_factory=list)  # Package IDs

    def total_weight(self, problem: Problem) -> int:
        """Tổng trọng lượng packages"""
        return sum(problem.get_customer(p).weight for p in self.packages)

    def add_package(self, package_id: int):
        self.packages.append(package_id)

    def copy(self) -> 'Mission':
        return Mission(
            meet_point=self.meet_point,
            truck_id=self.truck_id,
            packages=self.packages.copy()
        )

    def __repr__(self):
        return f"Mission(meet={self.meet_point}, truck={self.truck_id}, pkgs={self.packages})"


@dataclass
class DroneRoute:
    """
    Lộ trình của một drone: gồm nhiều missions
    """
    drone_id: int
    missions: List[Mission] = field(default_factory=list)

    def add_mission(self, mission: Mission):
        self.missions.append(mission)

    def all_packages(self) -> List[int]:
        """Tất cả packages được drone này vận chuyển"""
        result = []
        for mission in self.missions:
            result.extend(mission.packages)
        return result

    def copy(self) -> 'DroneRoute':
        return DroneRoute(
            drone_id=self.drone_id,
            missions=[m.copy() for m in self.missions]
        )

    def __repr__(self):
        return f"DroneRoute(id={self.drone_id}, missions={self.missions})"


@dataclass
class ResupplyInfo:
    """Thông tin resupply cho một package"""
    package_id: int
    drone_id: int
    mission_idx: int
    meet_point: int  # Customer ID nơi gặp truck


# ==================== SOLUTION ====================
@dataclass
class Solution:
    """Lời giải hoàn chỉnh"""
    trucks: List[TruckRoute]
    drones: List[DroneRoute]
    problem: Problem

    # Cache để tính toán nhanh
    _makespan: Optional[float] = field(default=None, repr=False)
    _is_feasible: Optional[bool] = field(default=None, repr=False)

    def get_resupply_info(self, package_id: int) -> Optional[ResupplyInfo]:
        """Tìm thông tin resupply của package"""
        for drone in self.drones:
            for m_idx, mission in enumerate(drone.missions):
                if package_id in mission.packages:
                    return ResupplyInfo(
                        package_id=package_id,
                        drone_id=drone.drone_id,
                        mission_idx=m_idx,
                        meet_point=mission.meet_point
                    )
        return None  # Package lấy từ depot

    def is_from_depot(self, package_id: int) -> bool:
        """Package có được lấy từ depot không?"""
        return self.get_resupply_info(package_id) is None

    def invalidate_cache(self):
        """Xóa cache khi solution thay đổi"""
        self._makespan = None
        self._is_feasible = None

    def copy(self) -> 'Solution':
        """Deep copy solution"""
        return Solution(
            trucks=[t.copy() for t in self.trucks],
            drones=[d.copy() for d in self.drones],
            problem=self.problem  # Problem không cần copy
        )

    # ========== FEASIBILITY CHECK ==========
    def check_capacity_truck(self) -> Tuple[bool, List[str]]:
        """Kiểm tra ràng buộc capacity của truck"""
        violations = []

        for truck in self.trucks:
            for trip_idx, trip in enumerate(truck.trips):
                current_load = 0

                # Đếm load ban đầu: packages C1 lấy từ depot (không qua drone resupply)
                for cid in trip.customers():
                    customer = self.problem.get_customer(cid)
                    # Chỉ C1 (type=D) mới lấy từ depot
                    if customer.ctype == CustomerType.D:
                        if self.is_from_depot(cid):
                            current_load += customer.weight

                # Duyệt qua route
                for pos, cid in enumerate(trip.route):
                    if cid == 0:
                        continue

                    customer = self.problem.get_customer(cid)

                    # Xử lý resupply TRƯỚC delivery (drone giao hàng tại điểm này)
                    for drone in self.drones:
                        for mission in drone.missions:
                            if mission.meet_point == cid and mission.truck_id == truck.truck_id:
                                for pkg in mission.packages:
                                    current_load += self.problem.get_customer(pkg).weight

                    # Xử lý delivery (giảm load) - C1 và DL của C2
                    if customer.ctype in [CustomerType.D, CustomerType.DL]:
                        current_load -= customer.weight

                    # Xử lý pickup (tăng load) - P của C2
                    if customer.ctype == CustomerType.P:
                        current_load += customer.weight

                    if current_load > TRUCK_CAPACITY:
                        violations.append(
                            f"Truck {truck.truck_id}, Trip {trip_idx}, "
                            f"at customer {cid}: load={current_load} > {TRUCK_CAPACITY}"
                        )

                    if current_load < 0:
                        violations.append(
                            f"Truck {truck.truck_id}, Trip {trip_idx}, "
                            f"at customer {cid}: negative load={current_load}"
                        )

        return len(violations) == 0, violations

    def check_capacity_drone(self) -> Tuple[bool, List[str]]:
        """Kiểm tra ràng buộc capacity của drone"""
        violations = []

        for drone in self.drones:
            for m_idx, mission in enumerate(drone.missions):
                total_weight = mission.total_weight(self.problem)
                if total_weight > DRONE_CAPACITY:
                    violations.append(
                        f"Drone {drone.drone_id}, Mission {m_idx}: "
                        f"weight={total_weight} > {DRONE_CAPACITY}"
                    )

        return len(violations) == 0, violations

    def check_drone_flight_time(self) -> Tuple[bool, List[str]]:
        """Kiểm tra ràng buộc thời gian bay của drone"""
        violations = []

        for drone in self.drones:
            for m_idx, mission in enumerate(drone.missions):
                # Thời gian = handling depot + bay đi + handling điểm gặp + bay về
                fly_time = 2 * self.problem.drone_travel_time(0, mission.meet_point)
                handling_time = 2 * DRONE_HANDLING_TIME
                total_time = fly_time + handling_time

                if total_time > DRONE_FLIGHT_TIME:
                    violations.append(
                        f"Drone {drone.drone_id}, Mission {m_idx}: "
                        f"flight_time={total_time:.1f} > {DRONE_FLIGHT_TIME}"
                    )

        return len(violations) == 0, violations

    def check_pickup_delivery_order(self) -> Tuple[bool, List[str]]:
        """Kiểm tra pickup phải trước delivery trong cùng truck"""
        violations = []

        for pickup_id, delivery_id in self.problem.c2_pairs:
            pickup_truck = None
            delivery_truck = None
            pickup_global_pos = None
            delivery_global_pos = None

            for truck in self.trucks:
                global_pos = 0
                for trip_idx, trip in enumerate(truck.trips):
                    for pos, cid in enumerate(trip.route):
                        if cid == pickup_id:
                            pickup_truck = truck.truck_id
                            pickup_global_pos = global_pos
                        if cid == delivery_id:
                            delivery_truck = truck.truck_id
                            delivery_global_pos = global_pos
                        global_pos += 1

            if pickup_truck is None or delivery_truck is None:
                violations.append(
                    f"Pair ({pickup_id}, {delivery_id}): not fully assigned"
                )
            elif pickup_truck != delivery_truck:
                violations.append(
                    f"Pair ({pickup_id}, {delivery_id}): "
                    f"pickup on truck {pickup_truck}, delivery on truck {delivery_truck}"
                )
            elif pickup_global_pos >= delivery_global_pos:
                violations.append(
                    f"Pair ({pickup_id}, {delivery_id}): "
                    f"pickup not before delivery"
                )

        return len(violations) == 0, violations

    def check_all_customers_served(self) -> Tuple[bool, List[str]]:
        """Kiểm tra tất cả khách hàng đều được phục vụ"""
        violations = []
        served = set()

        for truck in self.trucks:
            for cid in truck.all_customers():
                served.add(cid)

        all_customers = set(self.problem.customers.keys())
        unserved = all_customers - served

        if unserved:
            violations.append(f"Unserved customers: {unserved}")

        return len(violations) == 0, violations

    def is_feasible(self) -> Tuple[bool, List[str]]:
        """Kiểm tra tính khả thi của lời giải"""
        all_violations = []

        checks = [
            ("All customers served", self.check_all_customers_served()),
            ("Truck capacity", self.check_capacity_truck()),
            ("Drone capacity", self.check_capacity_drone()),
            ("Drone flight time", self.check_drone_flight_time()),
            ("Pickup-Delivery order", self.check_pickup_delivery_order()),
        ]

        feasible = True
        for check_name, (is_ok, violations) in checks:
            if not is_ok:
                feasible = False
                all_violations.extend(violations)

        self._is_feasible = feasible
        return feasible, all_violations

    # ========== MAKESPAN CALCULATION ==========
    def calculate_truck_time(self, truck: TruckRoute) -> float:
        """Tính thời gian hoàn thành của một truck"""
        total_time = 0.0

        for trip in truck.trips:
            if trip.is_empty():
                continue

            # Thời gian nhận hàng tại depot (đầu trip)
            total_time += TRUCK_RECEIVE_TIME

            # Duyệt route
            prev = 0
            for cid in trip.route[1:]:
                # Thời gian di chuyển
                total_time += self.problem.truck_travel_time(prev, cid)

                if cid != 0:
                    # Thời gian phục vụ khách hàng
                    total_time += TRUCK_SERVICE_TIME

                prev = cid

        return total_time

    def calculate_drone_time(self, drone: DroneRoute) -> float:
        """Tính thời gian hoàn thành của một drone"""
        total_time = 0.0

        for mission in drone.missions:
            # Handling tại depot
            total_time += DRONE_HANDLING_TIME
            # Bay đến điểm gặp
            total_time += self.problem.drone_travel_time(0, mission.meet_point)
            # Handling tại điểm gặp
            total_time += DRONE_HANDLING_TIME
            # Bay về depot
            total_time += self.problem.drone_travel_time(mission.meet_point, 0)

        return total_time

    def calculate_makespan(self) -> float:
        """Tính makespan (thời gian hoàn thành tất cả)"""
        if self._makespan is not None:
            return self._makespan

        truck_times = [self.calculate_truck_time(t) for t in self.trucks]
        drone_times = [self.calculate_drone_time(d) for d in self.drones]

        max_truck = max(truck_times) if truck_times else 0
        max_drone = max(drone_times) if drone_times else 0

        self._makespan = max(max_truck, max_drone)
        return self._makespan

    # ========== DISPLAY ==========
    def print_solution(self):
        """In lời giải chi tiết"""
        print("=" * 60)
        print("                    SOLUTION                    ")
        print("=" * 60)

        # Truck routes
        for truck in self.trucks:
            print(f"\n{'─' * 60}")
            print(f"TRUCK {truck.truck_id}:")
            print(f"{'─' * 60}")
            for t_idx, trip in enumerate(truck.trips):
                customers = trip.customers()
                if customers:
                    customer_details = []
                    for cid in customers:
                        c = self.problem.get_customer(cid)
                        customer_details.append(f"{cid}({c.ctype.value})")
                    print(f"  Trip {t_idx}: {' → '.join(['depot'] + customer_details + ['depot'])}")
                else:
                    print(f"  Trip {t_idx}: [empty]")
            print(f"  Time: {self.calculate_truck_time(truck):.2f} min")

        # Drone routes
        for drone in self.drones:
            print(f"\n{'─' * 60}")
            print(f"DRONE {drone.drone_id}:")
            print(f"{'─' * 60}")
            if drone.missions:
                for m_idx, mission in enumerate(drone.missions):
                    print(f"  Mission {m_idx}:")
                    print(f"    Route: depot → customer {mission.meet_point} → depot")
                    print(f"    Resupply to Truck: {mission.truck_id}")
                    print(f"    Packages: {mission.packages}")
                print(f"  Time: {self.calculate_drone_time(drone):.2f} min")
            else:
                print("  No missions")

        # Summary
        print(f"\n{'=' * 60}")
        print("SUMMARY")
        print(f"{'=' * 60}")
        print(f"Makespan: {self.calculate_makespan():.2f} min")

        feasible, violations = self.is_feasible()
        print(f"Feasible: {'Yes' if feasible else 'No'}")
        if violations:
            print("\nViolations:")
            for v in violations:
                print(f"  - {v}")
        print(f"{'=' * 60}")


# ==================== DATA LOADER ====================
def load_problem(filepath: str) -> Problem:
    """Đọc dữ liệu từ file"""
    customers = {}
    c1_customers = []
    c2_pairs_dict = {}  # pair_id → {'P': pickup_id, 'DL': delivery_id}

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            if len(parts) < 6:
                continue

            cid = int(parts[0])
            x = float(parts[1])
            y = float(parts[2])
            ctype = CustomerType(parts[3])
            ready_time = float(parts[4])
            pair_id = int(parts[5])

            customer = Customer(
                id=cid, x=x, y=y, ctype=ctype,
                ready_time=ready_time, pair_id=pair_id
            )
            customers[cid] = customer

            if ctype == CustomerType.D:
                c1_customers.append(cid)
            elif ctype == CustomerType.P:
                if pair_id not in c2_pairs_dict:
                    c2_pairs_dict[pair_id] = {}
                c2_pairs_dict[pair_id]['P'] = cid
            elif ctype == CustomerType.DL:
                if pair_id not in c2_pairs_dict:
                    c2_pairs_dict[pair_id] = {}
                c2_pairs_dict[pair_id]['DL'] = cid

    # Tạo list các cặp C2
    c2_pairs = []
    for pair_id, pair_data in c2_pairs_dict.items():
        if 'P' in pair_data and 'DL' in pair_data:
            c2_pairs.append((pair_data['P'], pair_data['DL']))

    return Problem(
        customers=customers,
        c1_customers=c1_customers,
        c2_pairs=c2_pairs
    )
