"""
Khởi tạo nghiệm ban đầu - Nearest Neighbor + Cluster
"""
from typing import List, Dict, Set, Tuple
import random

try:
    from .models import (
        Problem, Solution, Customer, CustomerType,
        TruckRoute, Trip, DroneRoute, Mission
    )
    from .config import (
        TRUCK_CAPACITY, TRUCK_SERVICE_TIME, TRUCK_RECEIVE_TIME,
        DRONE_CAPACITY, DRONE_FLIGHT_TIME, DRONE_HANDLING_TIME,
        NUM_TRUCKS, NUM_DRONES
    )
except ImportError:
    from models import (
        Problem, Solution, Customer, CustomerType,
        TruckRoute, Trip, DroneRoute, Mission
    )
    from config import (
        TRUCK_CAPACITY, TRUCK_SERVICE_TIME, TRUCK_RECEIVE_TIME,
        DRONE_CAPACITY, DRONE_FLIGHT_TIME, DRONE_HANDLING_TIME,
        NUM_TRUCKS, NUM_DRONES
    )


class SolutionInitializer:
    """Khởi tạo nghiệm ban đầu"""

    def __init__(self, problem: Problem):
        self.problem = problem

    def initialize(self) -> Solution:
        """
        Chiến lược: Nearest Neighbor + Cluster
        1. Cluster khách hàng theo vị trí
        2. Gán mỗi cluster cho 1 truck
        3. Với mỗi cluster, dùng nearest neighbor để sắp xếp
        4. Xác định drone resupply cho packages có ready_time cao
        """
        print("\n[Initializer] Starting Nearest Neighbor + Cluster...")

        # Bước 1: Cluster khách hàng
        clusters = self._cluster_customers()
        print(f"[Initializer] Created {len(clusters)} clusters")
        for i, customers in clusters.items():
            print(f"  Cluster {i}: {len(customers)} customers - {customers}")

        # Bước 2 & 3: Tạo route cho mỗi truck
        trucks = []
        for truck_id in range(NUM_TRUCKS):
            customer_ids = clusters.get(truck_id, [])
            truck_route = self._build_truck_route(truck_id, customer_ids)
            trucks.append(truck_route)
            print(f"[Initializer] Truck {truck_id} route: {truck_route.trips[0].route if truck_route.trips else []}")

        # Bước 4: Xác định drone resupply
        drones = self._assign_drone_resupply(trucks)
        print(f"[Initializer] Assigned drone missions")
        for drone in drones:
            print(f"  Drone {drone.drone_id}: {len(drone.missions)} missions")

        # Bước 5: Tạo solution và repair nếu có vi phạm
        solution = Solution(trucks=trucks, drones=drones, problem=self.problem)
        solution = self._repair_drone_missions(solution)
        return solution

    def initialize4bench(self) -> Solution:
        # Bước 1: Cluster khách hàng
        clusters = self._cluster_customers()

        # Bước 2 & 3: Tạo route cho mỗi truck
        trucks = []
        for truck_id in range(NUM_TRUCKS):
            customer_ids = clusters.get(truck_id, [])
            truck_route = self._build_truck_route(truck_id, customer_ids)
            trucks.append(truck_route)

        # Bước 4: Xác định drone resupply
        drones = self._assign_drone_resupply(trucks)
        
        # Bước 5: Tạo solution và repair nếu có vi phạm
        solution = Solution(trucks=trucks, drones=drones, problem=self.problem)
        solution = self._repair_drone_missions(solution)
        return solution

    # OK
    def _cluster_customers(self) -> Dict[int, List[int]]:
        """
        Cluster khách hàng theo vị trí địa lý
        Sử dụng phương pháp đơn giản: chia theo góc từ depot
        """
        import math

        depot_x, depot_y = self.problem.depot
        customer_angles = []

        # Tính góc của mỗi khách hàng so với depot
        for cid, customer in self.problem.customers.items():
            dx = customer.x - depot_x
            dy = customer.y - depot_y
            angle = math.atan2(dy, dx)  # Góc từ -π đến π
            customer_angles.append((cid, angle))

        # Sắp xếp theo góc
        customer_angles.sort(key=lambda x: x[1])

        # Chia đều cho các truck
        clusters = {i: [] for i in range(NUM_TRUCKS)}
        customers_per_cluster = len(customer_angles) // NUM_TRUCKS

        for idx, (cid, angle) in enumerate(customer_angles):
            cluster_id = min(idx // max(1, customers_per_cluster), NUM_TRUCKS - 1)
            clusters[cluster_id].append(cid)

        # Đảm bảo các cặp C2 cùng cluster
        clusters = self._fix_c2_pairs_cluster(clusters)

        return clusters

    # OK
    def _fix_c2_pairs_cluster(self, clusters: Dict[int, List[int]]) -> Dict[int, List[int]]:
        """Đảm bảo pickup và delivery của cặp C2 cùng cluster"""
        for pickup_id, delivery_id in self.problem.c2_pairs:
            pickup_cluster = None
            delivery_cluster = None

            for cluster_id, members in clusters.items():
                if pickup_id in members:
                    pickup_cluster = cluster_id
                if delivery_id in members:
                    delivery_cluster = cluster_id

            # Nếu khác cluster, chuyển delivery về cluster của pickup
            if pickup_cluster is not None and delivery_cluster is not None:
                if pickup_cluster != delivery_cluster:
                    clusters[delivery_cluster].remove(delivery_id)
                    clusters[pickup_cluster].append(delivery_id)
                    # delivery_id se luon o sau pickup_id (do append)

        return clusters

    # OK
    def _build_truck_route(self, truck_id: int, customer_ids: List[int]) -> TruckRoute:
        """
        Xây dựng route cho truck bằng nearest neighbor
        Có kiểm tra TRUCK_CAPACITY - tạo trip mới khi vượt capacity
        Delivery của C2 được chèn vào vị trí tối ưu (không nhất thiết ngay sau Pickup)
        """
        truck = TruckRoute(truck_id=truck_id)

        if not customer_ids:
            truck.add_trip(Trip())
            return truck

        # Tách C1 và C2
        c1_customers = []
        c2_pickup_delivery = {}  # pickup_id → delivery_id

        for cid in customer_ids:
            customer = self.problem.get_customer(cid)
            if customer.ctype == CustomerType.D:
                c1_customers.append(cid)
            elif customer.ctype == CustomerType.P:
                # Tìm delivery tương ứng
                for p_id, d_id in self.problem.c2_pairs:
                    if p_id == cid:
                        c2_pickup_delivery[cid] = d_id
                        break

        # Xây dựng route bằng nearest neighbor với kiểm tra capacity
        trip = Trip()
        current = 0  # Bắt đầu từ depot
        unvisited_c1 = set(c1_customers)
        unvisited_c2_pickups = set(c2_pickup_delivery.keys())
        pending_deliveries = []  # List of (pickup_id, delivery_id) chờ chèn DL

        # Track load: d_load = tổng weight của packages D load từ depot
        d_load = 0

        while unvisited_c1 or unvisited_c2_pickups or pending_deliveries:
            best_next = None
            best_dist = float('inf')
            is_c2_pickup = False
            is_pending_delivery = False
            best_delivery_info = None

            # Tính current_load tại điểm cuối route
            current_load = self._calculate_load_at_end(trip, d_load)

            # 1. Tìm D (C1) gần nhất (kiểm tra capacity tại depot)
            for cid in unvisited_c1:
                customer = self.problem.get_customer(cid)
                # Với D: package load từ depot → kiểm tra d_load + weight
                if d_load + customer.weight > TRUCK_CAPACITY:
                    continue

                dist = self.problem.manhattan_distance(current, cid)
                if dist < best_dist:
                    best_dist = dist
                    best_next = cid
                    is_c2_pickup = False
                    is_pending_delivery = False

            # 2. Tìm P (C2) gần nhất (kiểm tra capacity tại điểm pickup)
            for pickup_id in unvisited_c2_pickups:
                pickup_customer = self.problem.get_customer(pickup_id)
                # Sau pickup, load tăng thêm weight
                if current_load + pickup_customer.weight > TRUCK_CAPACITY:
                    continue

                dist = self.problem.manhattan_distance(current, pickup_id)
                if dist < best_dist:
                    best_dist = dist
                    best_next = pickup_id
                    is_c2_pickup = True
                    is_pending_delivery = False

            # 3. Xét pending deliveries - có thể chèn nếu gần
            for pickup_id, delivery_id in pending_deliveries:
                dist = self.problem.manhattan_distance(current, delivery_id)
                if dist < best_dist:
                    best_dist = dist
                    best_next = delivery_id
                    is_c2_pickup = False
                    is_pending_delivery = True
                    best_delivery_info = (pickup_id, delivery_id)

            # Nếu không tìm được customer phù hợp
            if best_next is None:
                # Nếu còn pending deliveries → chèn hết vào cuối trip
                if pending_deliveries:
                    for pickup_id, delivery_id in pending_deliveries:
                        trip.insert(len(trip) - 1, delivery_id)
                    pending_deliveries.clear()
                    current = trip.route[-2] if len(trip) > 2 else 0
                    continue

                # Nếu còn customer chưa visit → tạo trip mới
                if unvisited_c1 or unvisited_c2_pickups:
                    if not trip.is_empty():
                        truck.add_trip(trip)
                    trip = Trip()
                    current = 0
                    d_load = 0
                    continue
                else:
                    break

            # Thêm customer vào route
            if is_pending_delivery:
                # Chèn delivery
                pickup_id, delivery_id = best_delivery_info
                trip.insert(len(trip) - 1, delivery_id)
                pending_deliveries.remove(best_delivery_info)
                current = delivery_id

            elif is_c2_pickup:
                # Chèn pickup, delivery sẽ được chèn sau
                pickup_id = best_next
                delivery_id = c2_pickup_delivery[pickup_id]

                trip.insert(len(trip) - 1, pickup_id)
                unvisited_c2_pickups.remove(pickup_id)
                pending_deliveries.append((pickup_id, delivery_id))
                current = pickup_id

            else:
                # D customer
                customer = self.problem.get_customer(best_next)
                trip.insert(len(trip) - 1, best_next)
                unvisited_c1.remove(best_next)
                d_load += customer.weight
                current = best_next

        # Chèn các pending deliveries còn lại
        for pickup_id, delivery_id in pending_deliveries:
            trip.insert(len(trip) - 1, delivery_id)

        # Thêm trip cuối cùng
        if not trip.is_empty():
            truck.add_trip(trip)

        # Đảm bảo truck có ít nhất 1 trip
        if not truck.trips:
            truck.add_trip(Trip())

        return truck

    # OK
    def _calculate_load_at_end(self, trip: Trip, d_load: int) -> int:
        """
        Tính load tại cuối route hiện tại
        d_load: tổng weight của D packages (load từ depot)
        """
        if trip.is_empty():
            return d_load

        current_load = d_load
        for cid in trip.route:
            if cid == 0:
                continue
            customer = self.problem.get_customer(cid)
            if customer.ctype == CustomerType.D:
                current_load -= customer.weight
            elif customer.ctype == CustomerType.P:
                current_load += customer.weight
            elif customer.ctype == CustomerType.DL:
                current_load -= customer.weight

        return current_load

    # OK
    def _assign_drone_resupply(self, trucks: List[TruckRoute]) -> List[DroneRoute]:
        """
        Xác định packages cần drone resupply
        Logic: Packages C1 có ready_time > thời gian truck đến → cần drone resupply
        Gộp packages theo trip: các packages cùng trip của cùng truck sẽ được gom vào 1 mission
        """
        drones = [DroneRoute(drone_id=i) for i in range(NUM_DRONES)]

        # Tìm packages C1 có ready_time > 0, nhóm theo (truck_id, trip_idx)
        from collections import defaultdict
        grouped_packages = defaultdict(list)  # (truck_id, trip_idx) → list of packages

        for truck in trucks:
            current_time = 0
            for trip_idx, trip in enumerate(truck.trips):
                current_time += TRUCK_RECEIVE_TIME
                prev = 0

                for cid in trip.route[1:]:  # Bỏ depot đầu
                    current_time += self.problem.truck_travel_time(prev, cid)

                    if cid == 0:
                        continue
                           
                    customer = self.problem.get_customer(cid)

                    # Nếu là C1 và truck đến TRƯỚC khi package ready
                    if customer.ctype == CustomerType.D and customer.ready_time > 0:
                        if current_time < customer.ready_time:
                            # Thêm vào nhóm theo (truck_id, trip_idx)
                            key = (truck.truck_id, trip_idx)
                            grouped_packages[key].append({
                                'package_id': cid,
                                'ready_time': customer.ready_time,
                                'meet_point': cid,
                                'weight': customer.weight
                            })

                    current_time += TRUCK_SERVICE_TIME
                    prev = cid

                # Nếu không có package nào được chọn -> Chọn package có ready time lớn nhất
                key = (truck.truck_id, trip_idx)
                if not grouped_packages[key]:
                    # Tìm max ready time package trong trip (chỉ C1)
                    best_pkg = None
                    max_rt = -1
                    
                    for c_id in trip.customers():
                         c = self.problem.get_customer(c_id)
                         if c.ctype == CustomerType.D and c.ready_time > 0:
                             if c.ready_time > max_rt:
                                 max_rt = c.ready_time
                                 best_pkg = c
                    
                    if best_pkg:
                        grouped_packages[key].append({
                            'package_id': best_pkg.id,
                            'ready_time': best_pkg.ready_time,
                            'meet_point': best_pkg.id,
                            'weight': best_pkg.weight
                        })

        # Tạo missions từ các nhóm packages
        all_missions = []

        for (truck_id, trip_idx), pkg_list in grouped_packages.items():
            # Giữ nguyên thứ tự route (không sort theo ready_time)
            
            # Gộp packages vào missions
            current_packages = []
            current_weight = 0
            current_meet_point = None

            for pkg_info in pkg_list:
                pkg_id = pkg_info['package_id']
                pkg_weight = pkg_info['weight']
                pkg_meet = pkg_info['meet_point']

                # Thử thêm vào mission hiện tại
                added = False
                if current_packages:
                    if current_weight + pkg_weight <= DRONE_CAPACITY:
                        current_packages.append(pkg_id)
                        current_weight += pkg_weight
                        added = True
                    else:
                        # Mission hiện tại đầy -> lưu lại
                        all_missions.append({
                            'meet_point': current_meet_point,
                            'truck_id': truck_id,
                            'packages': current_packages,
                            'weight': current_weight
                        })
                        current_packages = []
                        current_weight = 0
                        current_meet_point = None

                # Nếu chưa được thêm (do mission đầy hoặc mới bắt đầu) -> Tìm meet point hợp lệ và tạo mission mới
                if not added:
                    # Lấy trip hiện tại
                    truck = next(t for t in trucks if t.truck_id == truck_id)
                    trip = truck.trips[trip_idx]
                    
                    # Tìm meet point hợp lệ (backtrack từ vị trí package về đầu trip)
                    valid_meet_point = self._find_valid_meet_point(
                        trip, pkg_id, pkg_info['ready_time']
                    )
                    
                    if valid_meet_point is None:
                        # Không tìm được meet point hợp lệ -> Bỏ qua, package sẽ load từ depot
                        continue

                    current_packages = [pkg_id]
                    current_weight = pkg_weight
                    current_meet_point = valid_meet_point

            # Mission cuối cùng của nhóm
            if current_packages:
                all_missions.append({
                    'meet_point': current_meet_point,
                    'truck_id': truck_id,
                    'packages': current_packages,
                    'weight': current_weight
                })

        # Phân bổ missions cho drones (cân bằng theo số lượng missions)
        drone_idx = 0
        for mission_info in all_missions:
            mission = Mission(
                meet_point=mission_info['meet_point'],
                truck_id=mission_info['truck_id'],
                packages=mission_info['packages']
            )
            drones[drone_idx].add_mission(mission)
            drone_idx = (drone_idx + 1) % NUM_DRONES

        return drones

    def _estimate_arrival_time(self, truck: TruckRoute, trip: Trip, target_cid: int) -> float:
        """Ước tính thời gian truck đến target_cid"""
        time = TRUCK_RECEIVE_TIME  # Nhận hàng ở depot

        prev = 0
        for cid in trip.route[1:]:
            time += self.problem.truck_travel_time(prev, cid)
            if cid == target_cid:
                return time
            if cid != 0:
                time += TRUCK_SERVICE_TIME
            prev = cid

        return time

    def _find_valid_meet_point(self, trip: Trip, pkg_id: int, pkg_ready_time: float) -> int:
        """
        Tìm meet point hợp lệ cho gói hàng bằng cách backtrack từ vị trí package về đầu trip.
        Meet point hợp lệ phải thỏa mãn: tổng flight time (bao gồm wait time) < DRONE_FLIGHT_TIME
        
        Args:
            trip: Trip của truck
            pkg_id: ID của package cần tìm meet point
            pkg_ready_time: Thời gian package sẵn sàng tại depot
            
        Returns:
            meet_point ID nếu tìm được, None nếu không tìm được
        """
        # Xác định vị trí của package trong trip
        try:
            pkg_idx = trip.route.index(pkg_id)
        except ValueError:
            return None

        # Các candidate là các điểm từ đầu trip đến vị trí package (bao gồm cả package)
        # Backtrack từ vị trí package ngược về đầu trip
        candidates = trip.route[1:pkg_idx+1]  # Bỏ depot đầu
        
        for meet_point in reversed(candidates):
            if meet_point == 0:
                continue  # Bỏ qua depot
                
            # 1. Tính thời gian bay
            fly_out = self.problem.drone_travel_time(0, meet_point)
            fly_in = self.problem.drone_travel_time(meet_point, 0)
            
            # 2. Ước tính thời gian truck đến meet point
            truck_arrival = self._estimate_arrival_time(None, trip, meet_point)
            
            # 3. Ước tính thời gian drone đến meet point
            # Drone xuất phát khi package ready + handling time + fly time
            drone_arrival = pkg_ready_time + DRONE_HANDLING_TIME + fly_out
            
            # 4. Ước tính wait time (drone chờ truck)
            wait_time = max(0, truck_arrival - drone_arrival)
            
            # 5. Tổng flight time = fly_out + wait + transfer + fly_in
            total_flight_time = fly_out + wait_time + DRONE_HANDLING_TIME + fly_in
            
            # Sử dụng safety buffer 90% để đảm bảo không vi phạm
            if total_flight_time <= DRONE_FLIGHT_TIME * 0.9:
                return meet_point
                
        return None  # Không tìm được meet point hợp lệ

    def _repair_drone_missions(self, solution: Solution) -> Solution:
        """
        Kiểm tra và sửa chữa các drone mission vi phạm flight time constraint.
        
        Chiến lược sửa chữa:
        1. Kiểm tra feasibility của solution
        2. Nếu có mission vi phạm flight time:
           - Thử tìm meet point mới (gần hơn) cho mission đó
           - Nếu không tìm được -> loại bỏ mission (package sẽ load từ depot)
        3. Lặp lại cho đến khi không còn vi phạm flight time
        """
        import re
        
        max_repair_iterations = 10
        
        for iteration in range(max_repair_iterations):
            # Kiểm tra feasibility
            is_feasible, violations = solution.is_feasible()
            
            if is_feasible:
                return solution  # Đã hợp lệ
            
            # Lọc các vi phạm flight time
            flight_violations = [v for v in violations if 'flight_time' in v.lower()]
            
            if not flight_violations:
                # Không còn vi phạm flight time (có thể còn vi phạm khác)
                return solution
            
            # Parse violations để tìm drone_id và mission_idx vi phạm
            repaired_any = False
            
            for violation in flight_violations:
                # Format: "Drone X, Mission Y: flight_time=Z > W"
                match = re.search(r'Drone (\d+), Mission (\d+)', violation)
                if not match:
                    continue
                    
                drone_id = int(match.group(1))
                mission_idx = int(match.group(2))
                
                # Tìm drone và mission
                drone = next((d for d in solution.drones if d.drone_id == drone_id), None)
                if not drone or mission_idx >= len(drone.missions):
                    continue
                    
                mission = drone.missions[mission_idx]
                
                # Tìm truck và trip của mission này
                truck = next((t for t in solution.trucks if t.truck_id == mission.truck_id), None)
                if not truck:
                    # Không tìm được truck -> loại bỏ mission
                    drone.missions.pop(mission_idx)
                    repaired_any = True
                    break
                
                # Tìm trip chứa meet_point
                trip = None
                for t in truck.trips:
                    if mission.meet_point in t.route:
                        trip = t
                        break
                
                if not trip:
                    # Meet point không còn trên truck -> loại bỏ mission
                    drone.missions.pop(mission_idx)
                    repaired_any = True
                    break
                
                # Thử tìm meet point mới cho từng package trong mission
                # Lấy max ready_time của các packages
                max_ready = max(self.problem.get_customer(p).ready_time for p in mission.packages)
                
                # Tìm package đầu tiên trong route (để tìm meet point)
                first_pkg = None
                first_pos = float('inf')
                for pkg_id in mission.packages:
                    try:
                        pos = trip.route.index(pkg_id)
                        if pos < first_pos:
                            first_pos = pos
                            first_pkg = pkg_id
                    except ValueError:
                        continue
                
                if first_pkg is None:
                    # Không tìm được package nào trong trip -> loại bỏ mission
                    drone.missions.pop(mission_idx)
                    repaired_any = True
                    break
                
                # Tìm meet point mới hợp lệ
                new_meet_point = self._find_valid_meet_point(trip, first_pkg, max_ready)
                
                if new_meet_point is not None and new_meet_point != mission.meet_point:
                    # Cập nhật meet point mới (khác với meet point cũ)
                    mission.meet_point = new_meet_point
                    repaired_any = True
                else:
                    # Không tìm được meet point hợp lệ hoặc meet point không thay đổi
                    # -> Loại bỏ mission (package sẽ load từ depot)
                    drone.missions.pop(mission_idx)
                    repaired_any = True
                
                # Invalidate cache và break để kiểm tra lại
                solution.invalidate_cache()
                break
            
            if not repaired_any:
                # Không sửa được gì thêm
                break
        
        return solution