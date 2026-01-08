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
        
        # Lấy timeline chính xác (bao gồm chờ đợi)
        _, drone_map, calc_violations = self.calculate_timestamps()
        
        # Nếu quá trình tính toán đã có lỗi (vd: không tìm thấy meeting point), return luôn
        if calc_violations:
            return False, calc_violations

        for drone in self.drones:
            for m_idx, mission in enumerate(drone.missions):
                info = drone_map.get((drone.drone_id, m_idx))
                if not info:
                    continue # Should be caught in calc_violations
                    
                total_time = info['flight_time']

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
                global_pos = 0 # Vị trí của điểm này trong toàn thể lộ trình của truck chứ không riêng gì 1 trip
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

    # ========== MAKESPAN CALCULATION (GRAPH BASED) ==========
    def calculate_timestamps(self) -> Tuple[Dict, Dict, List[str]]:
        """
        Tính toán mốc thời gian chi tiết cho toàn bộ hệ thống (Truck & Drone).
        Trả về:
          - truck_timeline: Dict[(truck_id, trip_idx, pos), {events...}]
          - drone_timeline: Dict[(drone_id, mission_idx), {events...}]
          - violations: List[str] các lỗi thời gian (nếu có)
        """
        violations = []

        # 1. Xây dựng MAP:
        #    - drone_mission_map: (drone_id, mission_idx) -> Mission object
        #    - truck_node_map: (truck_id, trip_idx, pos) -> Customer ID
        #    - resupply_map: (truck_id, trip_idx, pos) -> (drone_id, mission_idx)
        resupply_map = {}
        
        # Duyệt drone để xây dựng resupply map
        for drone in self.drones:
            for m_idx, mission in enumerate(drone.missions):
                # Tìm vị trí truck mà drone này resupply
                # truck_id = mission.truck_id, meet_point = mission.meet_point
                # Phải tìm trip_idx, pos trong truck route
                found = False
                for truck in self.trucks:
                    if truck.truck_id == mission.truck_id:
                        pos_info = truck.find_customer_position(mission.meet_point)
                        if pos_info:
                            trip_idx, pos = pos_info
                            # Lưu ánh xạ: Tại vị trí này của truck, có drone mission này
                            resupply_map[(truck.truck_id, trip_idx, pos)] = (drone.drone_id, m_idx)
                            found = True
                        break
                if not found:
                    violations.append(f"Drone {drone.drone_id} Mission {m_idx}: Cannot find meet point {mission.meet_point} on Truck {mission.truck_id}")

        # 2. Khởi tạo Memoization Cache
        memo_truck = {} # Key: (truck_id, trip_idx, pos) -> {arrival, depart...}
        memo_drone = {} # Key: (drone_id, mission_idx) -> {ready, return...}
        visiting = set() # Phát hiện chu trình

        # 3. Recursive Functions

        def get_drone_times(d_id, m_idx):
            # Tính mốc thời gian của 1 chuyến mission: m_idx - ôk
            state_key = f"D{d_id}_{m_idx}"
            if (d_id, m_idx) in memo_drone: return memo_drone[(d_id, m_idx)]
            if state_key in visiting:
                return None 
            visiting.add(state_key)

            drone = next(d for d in self.drones if d.drone_id == d_id)
            mission = drone.missions[m_idx]

            # 1. Ready at Depot - OK
            if m_idx == 0:
                ready_at_depot = 0.0
            else:
                prev_mission = get_drone_times(d_id, m_idx - 1)
                ready_at_depot = prev_mission['return_depot']

            # Ràng buộc: ready_time của packages - OK
            max_pkg_ready = 0
            for pkg_id in mission.packages:
                max_pkg_ready = max(max_pkg_ready, self.problem.get_customer(pkg_id).ready_time)
            
            ready_at_depot = max(ready_at_depot, max_pkg_ready)

            # 2. Start Service at Depot (Handling) - OK
            start_load = ready_at_depot
            finish_load = start_load + DRONE_HANDLING_TIME
            
            # 3. Fly to Meet Point
            depart_depot = finish_load
            fly_time_out = self.problem.drone_travel_time(0, mission.meet_point)
            arrive_meet = depart_depot + fly_time_out

            # 4. Interaction with Truck (Wait for Truck) - OK
            truck_resinfo = None
            for tid, trips_val in resupply_map.items():
                if trips_val == (d_id, m_idx):
                    truck_resinfo = tid # (truck_id, trip_idx, pos)
                    break
            
            if not truck_resinfo:
                 visiting.remove(state_key)
                 return {} 
            
            tr_id, tr_idx, tr_pos = truck_resinfo
            
            # Lấy thông tin Arrival của Truck (chưa tính resupply wait) - OK
            truck_node_times = get_truck_base_arrival(tr_id, tr_idx, tr_pos)
            
            truck = next(t for t in self.trucks if t.truck_id == tr_id)
            c_curr_id = truck.trips[tr_idx].route[tr_pos]
            
            # Check if resupply is needed for current customer
            is_needed_now = (c_curr_id in mission.packages)
            
            if is_needed_now:
                # Needed NOW: Truck Arrive -> Receive -> Service
                # Truck ready to receive ngay khi đến
                truck_ready_for_drone = truck_node_times['arrival']
            else:
                # Future use: Truck Arrive -> Service -> Receive
                service_duration = TRUCK_SERVICE_TIME if c_curr_id != 0 else 0
                truck_ready_for_drone = truck_node_times['arrival'] + service_duration

            # SYNC
            start_transfer = max(arrive_meet, truck_ready_for_drone)
            finish_transfer = start_transfer + DRONE_HANDLING_TIME
            
            # 5. Fly Back
            depart_meet = finish_transfer
            fly_time_in = self.problem.drone_travel_time(mission.meet_point, 0)
            return_depot = depart_meet + fly_time_in
            
            res = {
                'ready_at_depot': ready_at_depot,
                'start_load': start_load,
                'depart_depot': depart_depot,
                'arrive_meet': arrive_meet,
                'start_transfer': start_transfer,
                'finish_transfer': finish_transfer,
                'depart_meet': depart_meet,
                'return_depot': return_depot,
                'flight_time': return_depot - depart_depot # Total flight cycle
            }
            memo_drone[(d_id, m_idx)] = res
            visiting.remove(state_key)
            return res

        def get_truck_base_arrival(t_id, tr_idx, pos):
            # Tính thời gian đến 1 điểm trong lộ trình của Truck - ok
            # Arrival(N) = Departure(N-1) + Travel
            if pos == 0:
                if tr_idx == 0:
                    return {'arrival': 0.0} 
                else:
                    # Arrival tại depot = Departure của trip trước
                    truck = next(t for t in self.trucks if t.truck_id == t_id)
                    prev_trip = truck.trips[tr_idx - 1]
                    prev_node = get_truck_full_node(t_id, tr_idx - 1, len(prev_trip.route) - 1)
                    return {'arrival': prev_node['departure']}
            
            prev_node = get_truck_full_node(t_id, tr_idx, pos - 1)
            truck = next(t for t in self.trucks if t.truck_id == t_id)
            curr_trip = truck.trips[tr_idx]
            prev_cid = curr_trip.route[pos - 1]
            curr_cid = curr_trip.route[pos]
            
            travel_time = self.problem.truck_travel_time(prev_cid, curr_cid)
            arrival = prev_node['departure'] + travel_time
            return {'arrival': arrival}

        def get_truck_full_node(t_id, tr_idx, pos):
            # Tính mốc thời gian của 1 truck tại 1 node: m_idx - ôk
            state_key = f"T{t_id}_{tr_idx}_{pos}"
            if (t_id, tr_idx, pos) in memo_truck: return memo_truck[(t_id, tr_idx, pos)]
            if state_key in visiting:
                return {'departure': float('inf')} 
            visiting.add(state_key)

            # 1. Arrival - OK
            base = get_truck_base_arrival(t_id, tr_idx, pos)
            arrival = base['arrival']
            
            truck = next(t for t in self.trucks if t.truck_id == t_id)
            cid = truck.trips[tr_idx].route[pos]
            
            # Depot processing - OK
            if cid == 0:
                # Nếu là đầu trip (pos=0), cần Loading Time & Wait for Package Ready Time
                process_duration = TRUCK_RECEIVE_TIME * (1 if pos == 0 else 0)
                
                start_time = arrival
                
                # Check package ready time for this trip
                if pos == 0:
                    trip = truck.trips[tr_idx]
                    trip_customers = trip.customers()
                    max_ready = 0
                    
                    for c_id in trip_customers:
                         customer = self.problem.get_customer(c_id)
                         # Chỉ quan tâm C1 (D) được load từ depot cho trip này
                         if customer.ctype == CustomerType.D:
                             # Check xem có bị drone resupply khoong?
                             # resupply_map key: (truck_id, trip_idx, pos_of_customer)
                             # c_id nam o dau trong trip?
                             c_pos = trip.route.index(c_id)
                             if (t_id, tr_idx, c_pos) not in resupply_map:
                                 max_ready = max(max_ready, customer.ready_time)
                    
                    start_time = max(arrival, max_ready)

                service_start = start_time
                service_end = service_start + process_duration
                departure = service_end
                
                res = {
                    'arrival': arrival,
                    'service_start': service_start,
                    'service_end': service_end,
                    'resupply_start': None,
                    'resupply_end': None,
                    'departure': departure
                }
                memo_truck[(t_id, tr_idx, pos)] = res
                visiting.remove(state_key)
                return res

            # Khách hàng
            resupply_mission_key = resupply_map.get((t_id, tr_idx, pos))
            service_duration = TRUCK_SERVICE_TIME
            
            if not resupply_mission_key:
                # OK
                # Không phải gói hàng Resupply: Arrive -> Service -> Depart
                service_start = arrival
                service_end = arrival + service_duration
                departure = service_end
                res = {
                    'arrival': arrival,
                    'service_start': service_start,
                    'service_end': service_end,
                    'resupply_start': None,
                    'resupply_end': None,
                    'departure': departure
                }
            else:
                # Có resupply
                d_id, m_idx = resupply_mission_key
                drone_times = get_drone_times(d_id, m_idx) # Trigger wait for drone
                
                drone_mission = next(d for d in self.drones if d.drone_id == d_id).missions[m_idx]
                is_needed_now = (cid in drone_mission.packages) # Gói hàng này có trong chuyến resupply không ?
                
                
                if is_needed_now:
                    # OK
                    # Nếu có thì resupply trước rồi mới giao
                    # RESUPPLY FIRST: Ack start_transfer calculated in Drone
                    resupply_start = drone_times['start_transfer']
                    resupply_end = drone_times['finish_transfer']
                    
                    service_start = resupply_end
                    service_end = service_start + service_duration
                    departure = service_end
                    
                    res = {
                        'arrival': arrival,
                        'resupply_start': resupply_start,
                        'resupply_end': resupply_end,
                        'service_start': service_start,
                        'service_end': service_end,
                        'departure': departure
                    }
                else:
                    # OK
                    # Giao trước rồi mới nhận resupply
                    # SERVICE FIRST
                    service_start = arrival
                    service_end = service_start + service_duration
                    
                    resupply_start = drone_times['start_transfer']
                    resupply_end = drone_times['finish_transfer']
                    departure = resupply_end
                    
                    res = {
                        'arrival': arrival,
                        'service_start': service_start,
                        'service_end': service_end,
                        'resupply_start': resupply_start,
                        'resupply_end': resupply_end,
                        'departure': departure
                    }

            memo_truck[(t_id, tr_idx, pos)] = res
            visiting.remove(state_key)
            return res

        # 4. Starting Points
        for truck in self.trucks:
            if truck.trips:
                last_trip_idx = len(truck.trips) - 1
                last_trip = truck.trips[-1]
                if last_trip.route:
                    get_truck_full_node(truck.truck_id, last_trip_idx, len(last_trip.route) - 1)
        
        for drone in self.drones:
            if drone.missions:
                get_drone_times(drone.drone_id, len(drone.missions) - 1)

        return memo_truck, memo_drone, violations

    def calculate_makespan(self) -> float:
        """Tính makespan (thời gian hoàn thành tất cả)"""
        if self._makespan is not None:
             return self._makespan

        truck_times, drone_times, _ = self.calculate_timestamps()
        
        max_time = 0.0
        for t_info in truck_times.values():
            max_time = max(max_time, t_info['departure'])
        for d_info in drone_times.values():
            max_time = max(max_time, d_info['return_depot'])
            
        self._makespan = max_time
        return max_time

        # ========== DISPLAY ==========
    def print_solution(self):
        """In lời giải chi tiết"""
        truck_map, drone_map, violations = self.calculate_timestamps()
        makespan = self.calculate_makespan()
        
        print("=" * 100)
        print(f"{'SOLUTION DETAIL':^100}")
        print("=" * 100)

        # Truck routes
        for truck in self.trucks:
            print(f"\nTRUCK {truck.truck_id}:")
            print(f"{'Trip':<5} | {'Event':<25} | {'Loc':<6} | {'Arrive':<8} | {'Service/Resupply':<35} | {'Depart':<8}")
            print("-" * 100)
            
            for t_idx, trip in enumerate(truck.trips):
                for pos, cid in enumerate(trip.route):
                    info = truck_map.get((truck.truck_id, t_idx, pos), {})
                    if not info: continue
                    
                    c_type = "Depot"
                    if cid != 0:
                        c_type = self.problem.get_customer(cid).ctype.value
                    
                    time_s = f"{info['arrival']:.1f}"
                    time_e = f"{info['departure']:.1f}"
                    
                    details = []
                    if info.get('service_start') is not None and cid != 0:
                        details.append(f"Srv:{info['service_start']:.1f}-{info['service_end']:.1f}")
                    elif cid == 0 and info.get('service_end') > info.get('service_start'):
                        details.append(f"Load:{info['service_start']:.1f}-{info['service_end']:.1f}")

                    if info.get('resupply_start') is not None:
                        details.append(f"Rsp:{info['resupply_start']:.1f}-{info['resupply_end']:.1f}")
                        
                    note = " | ".join(details)
                    print(f"{t_idx:<5} | {c_type:<25} | {cid:<6} | {time_s:<8} | {note:<35} | {time_e:<8}")

        # Drone routes
        for drone in self.drones:
            print(f"\nDRONE {drone.drone_id}:")
            print(f"{'Msn':<5} | {'Meet':<6} | {'Pkgs':<10} | {'Load@Depot':<18} | {'Arrive Meet':<12} | {'Transfer':<18} | {'Return':<8} | {'Flight':<8}")
            print("-" * 100)
            
            for m_idx, mission in enumerate(drone.missions):
                info = drone_map.get((drone.drone_id, m_idx), {})
                if not info: continue
                
                pkgs = str(mission.packages)
                print(f"{m_idx:<5} | {mission.meet_point:<6} | {pkgs:<10} | "
                      f"{info['start_load']:.1f}-{info['depart_depot']:.1f}          | "
                      f"{info['arrive_meet']:.1f}         | "
                      f"{info['start_transfer']:.1f}-{info['finish_transfer']:.1f}          | "
                      f"{info['return_depot']:.1f}     | "
                      f"{info['flight_time']:.1f}")

        # Summary
        print(f"\n{'=' * 100}")
        print("SUMMARY STATUS")
        print(f"Makespan: {makespan:.2f} min")
        
        feasible, logic_violations = self.is_feasible()
        all_violations = logic_violations + violations
        
        print(f"Feasible: {'Yes' if feasible and not violations else 'No'}")
        if all_violations:
            print("\nViolations:")
            for v in all_violations:
                print(f"  - {v}")
        print(f"{'=' * 100}")


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
