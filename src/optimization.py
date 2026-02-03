import random
import time
from typing import List, Tuple, Dict, Optional
from copy import deepcopy

try:
    from .models import Solution, TruckRoute, Trip, CustomerType
    from .config import TRUCK_CAPACITY, DRONE_CAPACITY
except ImportError:
    from models import Solution, TruckRoute, Trip, CustomerType
    from config import TRUCK_CAPACITY, DRONE_CAPACITY

class NeighborhoodGenerator:
    """Sinh các lân cận cho Tabu Search"""

    def __init__(self, problem):
        self.problem = problem

    # OK
    def get_relocate_moves(self, solution: Solution) -> List[Tuple[str, int, int, int, int, int, int]]:
        """
        Sinh các move Relocate: Di chuyển khách hàng từ (t1, trip1, pos1) sang (t2, trip2, pos2)
        Format move: ('relocate', t1_id, trip1_idx, pos1, t2_id, trip2_idx, pos2)
        """
        moves = []
        trucks = solution.trucks
        
        # Lấy danh sách tất cả vị trí khách hàng (trừ depot)
        customer_positions = []
        for t_idx, truck in enumerate(trucks):
            for tr_idx, trip in enumerate(truck.trips):
                for pos, cid in enumerate(trip.route):
                    if cid != 0:
                        customer_positions.append((t_idx, tr_idx, pos))

        # Thử di chuyển mỗi khách hàng đến một vị trí mới
        # Giới hạn số lượng move check mỗi vòng để đảm bảo hiệu năng
        selected_positions = customer_positions
        if len(customer_positions) > 100:
             import random
             selected_positions = random.sample(customer_positions, 100)
        
        for (t1_idx, tr1_idx, pos1) in selected_positions:
            cid = trucks[t1_idx].trips[tr1_idx].route[pos1]
            customer = self.problem.get_customer(cid)
            
            # Nếu là C2, logic phức tạp hơn (phải move cả cặp hoặc check ràng buộc) => tạm thời skip C2
            if customer.ctype in [CustomerType.P, CustomerType.DL]:
                continue

            # Thử chèn vào các vị trí khác
            for t2_idx, truck2 in enumerate(trucks):
                for tr2_idx, trip2 in enumerate(truck2.trips):
                    # Các vị trí chèn có thể: 1 đến len(route)-1 (vì 0 và -1 là depot)
                    # Tuy nhiên route hiện tại có thể là [0, c1, c2, 0] -> len 4. 
                    # Insert vào index 1 (trước c1), 2 (trước c2), 3 (trước 0 cuối)
                    valid_insert_positions = range(1, len(trip2.route))
                    
                    for pos2 in valid_insert_positions:
                        # Không chèn vào chính vị trí hiện tại hoặc ngay sau nó (vô nghĩa)
                        if t1_idx == t2_idx and tr1_idx == tr2_idx:
                            if pos2 == pos1 or pos2 == pos1 + 1:
                                continue
                                
                        moves.append(('relocate', t1_idx, tr1_idx, pos1, t2_idx, tr2_idx, pos2))
        
        return moves

   # OK
    def get_swap_moves(self, solution: Solution) -> List[Tuple[str, int, int, int, int, int, int]]:
        """
        Sinh các move Swap: Hoán đổi khách hàng tại (t1, tr1, p1) và (t2, tr2, p2)
        Format move: ('swap', t1_idx, tr1_idx, pos1, t2_idx, tr2_idx, pos2)
        """
        moves = []
        trucks = solution.trucks
        
        customer_positions = []
        for t_idx, truck in enumerate(trucks):
            for tr_idx, trip in enumerate(truck.trips):
                for pos, cid in enumerate(trip.route):
                    if cid != 0:
                        customer_positions.append((t_idx, tr_idx, pos))
        
        if len(customer_positions) < 2:
            return []
            
        # Sample random pairs
        num_swaps = 100
        for _ in range(num_swaps):
            import random
            pos_a, pos_b = random.sample(customer_positions, 2)
            
            t1, tr1, p1 = pos_a
            t2, tr2, p2 = pos_b
            
            c1 = trucks[t1].trips[tr1].route[p1]
            c2 = trucks[t2].trips[tr2].route[p2]
            
            cust1 = self.problem.get_customer(c1)
            cust2 = self.problem.get_customer(c2)
            
            # Skip C2 để giảm độ phức tạp
            if cust1.ctype in [CustomerType.P, CustomerType.DL] or \
               cust2.ctype in [CustomerType.P, CustomerType.DL]:
               continue
               
            moves.append(('swap', t1, tr1, p1, t2, tr2, p2))
            
        return moves
        
    def get_add_drone_package_moves(self, solution: Solution) -> List[Tuple[str, int, int, int]]:
        """
        Sinh các move Add Package: Thêm một gói hàng vào mission hiện có
        Format: ('add_drone_pkg', drone_id, mission_idx, package_id)
        Logic: Chỉ chọn gói hàng nằm trên lộ trình Truck SAU meet_point, 
               nhưng trong phạm vi trip đó.
        """
        moves = []
        trucks = solution.trucks
        
        for drone in solution.drones:
            for m_idx, mission in enumerate(drone.missions):
                if not mission.packages:
                    continue # Mission rỗng (hiếm gặp nếu logic tốt)
                
                # Check Capacity sơ bộ
                current_weight = mission.total_weight(self.problem)
                
                # Xác định Trip mà mission đang resupply
                truck = next(t for t in trucks if t.truck_id == mission.truck_id)
                # Tìm meet_point nằm ở trip nào, pos nào
                pos_info = truck.find_customer_position(mission.meet_point)
                if not pos_info:
                    continue
                    
                trip_idx, meet_pos = pos_info
                trip = truck.trips[trip_idx]
                
                # Duyệt các gói hàng trong trip này (trừ depot)
                # Chỉ lấy các gói hàng loại C1 (D) có thể giao bằng drone
                for pos, cid in enumerate(trip.route):
                    if cid == 0: continue
                    
                    # Logic Mới: Cho phép thêm cả gói hàng trước và sau meet_point
                    # Nếu thêm gói trước meet_point -> meet_point sẽ phải thay đổi (về gói sớm nhất)
                    # Logic update sẽ được xử lý trong apply_move -> _update_drone_missions
                    
                    customer = self.problem.get_customer(cid)
                    
                    # Chỉ C1 mới đi drone được
                    if customer.ctype != CustomerType.D:
                        continue
                        
                    # Gói hàng này đã có trong mission chưa?
                    if cid in mission.packages:
                        continue
                        
                    # Gói hàng đã được drone KHÁC phục vụ chưa?
                    if not solution.is_from_depot(cid):
                        continue # Đã được phục vụ bởi drone khác (hoặc chính drone này mission khác)
                        
                    # Check capacity
                    if current_weight + customer.weight > DRONE_CAPACITY:
                        continue
                        
                    moves.append(('add_drone_pkg', drone.drone_id, m_idx, cid))
                    
        return moves

    def get_remove_drone_package_moves(self, solution: Solution) -> List[Tuple[str, int, int, int]]:
        """
        Sinh các move Remove Package: Xóa gói hàng khỏi mission
        Format: ('remove_drone_pkg', drone_id, mission_idx, package_id)
        """
        moves = []
        for drone in solution.drones:
            for m_idx, mission in enumerate(drone.missions):
                if not mission.packages:
                    continue
                
                for pkg in mission.packages:
                    # Thử xóa pkg này
                    moves.append(('remove_drone_pkg', drone.drone_id, m_idx, pkg))
        return moves

    def apply_move(self, solution: Solution, move) -> Solution:
        """
        Áp dụng move vào solution (tạo bản copy)
        """
        new_sol = solution.copy()
        move_type = move[0]
        
        if move_type == 'relocate':
            _, t1, tr1, p1, t2, tr2, p2 = move
            # Lấy customer ra
            truck1 = new_sol.trucks[t1]
            trip1 = truck1.trips[tr1]
            cid = trip1.route[p1]
            
            # Xóa khỏi vị trí cũ
            # Nếu t1==t2 và tr1==tr2 (cùng 1 trip cùng 1 xe), index có thể thay đổi sau khi xóa
            
            if t1 == t2 and tr1 == tr2:
                # Di chuyển trong cùng trip
                if p1 < p2:
                    # Chèn trước, xóa sau: p2 giảm 1
                    trip1.route.insert(p2, cid)
                    del trip1.route[p1]
                else:
                    # Xóa trước, chèn sau
                    del trip1.route[p1]
                    trip1.route.insert(p2, cid)
            else:
                # Khác trip
                trip1.route.pop(p1)
                new_sol.trucks[t2].trips[tr2].route.insert(p2, cid)
                
        elif move_type == 'swap':
            _, t1, tr1, p1, t2, tr2, p2 = move
            truck1 = new_sol.trucks[t1]
            truck2 = new_sol.trucks[t2]
            
            c1 = truck1.trips[tr1].route[p1]
            c2 = truck2.trips[tr2].route[p2]
            
            truck2.trips[tr2].route[p2] = c1
            
        elif move_type == 'add_drone_pkg':
            _, d_id, m_idx, pkg_id = move
            drone = next(d for d in new_sol.drones if d.drone_id == d_id)
            mission = drone.missions[m_idx]
            mission.add_package(pkg_id)
            
            # Cập nhật meet_point nếu gói hàng mới nằm trước meet_point cũ
            # Tìm vị trí meet_point hiện tại và gói hàng mới
            truck = next(t for t in new_sol.trucks if t.truck_id == mission.truck_id)
            pos_meet = truck.find_customer_position(mission.meet_point)
            pos_new = truck.find_customer_position(pkg_id)
            
            if pos_meet and pos_new:
                 # Cả 2 cùng 1 trip (giả định logic get_move)
                 if pos_new[1] < pos_meet[1]:
                     mission.meet_point = pkg_id
            
        elif move_type == 'remove_drone_pkg':
            _, d_id, m_idx, pkg_id = move
            drone = next(d for d in new_sol.drones if d.drone_id == d_id)
            mission = drone.missions[m_idx]
            if pkg_id in mission.packages:
                mission.packages.remove(pkg_id)
            
            # Nếu mission rỗng sau khi xóa -> Xóa mission luôn khỏi danh sách
            if not mission.packages:
                drone.missions.pop(m_idx)
            
        # Do solution đã thay đổi nên cần xóa các thông tin cũ (is_feasible, makespan)
        new_sol.invalidate_cache()
        
        # Quan trọng: Khi thay đổi route truck, các Drone Mission trỏ đến meet_point cũ 
        # có thể bị invalid (ví dụ: meet_point không còn nằm trên truck đó nữa, hoặc sai thứ tự).
        if move_type in ['relocate', 'swap']:
            self._update_drone_missions(new_sol)
        
        return new_sol
        
    def _update_drone_missions(self, solution: Solution):
        """
        Cập nhật lại các mission của drone khi lộ trình xe tải thay đổi:
        1. Duyệt từng gói hàng trong mission, nếu địa chỉ (truck, trip) thay đổi -> Xóa khỏi mission.
        2. Cập nhật lại meet_point = khách hàng xuất hiện sớm nhất trong số các gói hàng còn lại.
        """
        # 1. Map customer -> (truck_id, trip_idx, pos)
        cust_locs = {}
        for truck in solution.trucks:
            for t_idx, trip in enumerate(truck.trips):
                for pos, cid in enumerate(trip.route):
                    if cid != 0:
                        cust_locs[cid] = (truck.truck_id, t_idx, pos)

        for drone in solution.drones:
            for mission in drone.missions:
                if not mission.packages:
                    continue

                # Xác định "Anchor" (Truck, Trip) cho mission này.
                # Gom nhóm các gói hàng theo (Truck, Trip)
                # target_addr -> count
                addr_counts = {} 
                
                for pkg in mission.packages:
                    if pkg in cust_locs:
                        tid, tr_idx, _ = cust_locs[pkg]
                        key = (tid, tr_idx)
                        addr_counts[key] = addr_counts.get(key, 0) + 1
                
                if not addr_counts:
                    # Tất cả packages biến mất? (không thể xảy ra nếu Relocate/Swap đúng)
                    mission.packages = []
                    continue
                    
                # Chọn nhóm địa chỉ phổ biến nhất (Major Vote)
                # Để đảm bảo mission đi theo đa số các gói hàng
                target_tid, target_tr_idx = max(addr_counts, key=addr_counts.get)
                
                # Lọc packages: Chỉ giữ lại gói hàng nằm đúng địa chỉ target
                valid_packages = []
                for pkg in mission.packages:
                    if pkg in cust_locs:
                        tid, tr_idx, _ = cust_locs[pkg]
                        if tid == target_tid and tr_idx == target_tr_idx:
                            valid_packages.append(pkg)
                
                mission.packages = valid_packages
                
                if not mission.packages:
                    continue
                
                # Cập nhật thông tin Truck cho mission
                mission.truck_id = target_tid
                    
                # 3. Chọn meet point mới theo khách hàng xuất hiện sớm nhất trong lộ trình mới
                earliest_pkg = None
                min_pos = float('inf')
                
                for pkg in mission.packages:
                    # Chắc chắn pkg trong cust_locs và đúng truck/trip
                    _, _, pos = cust_locs[pkg]
                    if pos < min_pos:
                        min_pos = pos
                        earliest_pkg = pkg
                
                if earliest_pkg is not None:
                    mission.meet_point = earliest_pkg


class TabuSearch:
    def __init__(self, problem, initial_solution: Solution):
        self.problem = problem
        self.best_solution = initial_solution
        self.current_solution = initial_solution
        self.neighborhood = NeighborhoodGenerator(problem)
        self.tabu_list = {} # Key: move_signature, Value: expiry_iteration
        
    def get_move_signature(self, move):
        move_type = move[0]
        if move_type == 'relocate':
            return tuple(move)
        elif move_type == 'swap':
            return tuple(move)
        elif move_type == 'add_drone_pkg':
            return tuple(move)
        elif move_type == 'remove_drone_pkg':
            return tuple(move)
        return None

    def solve(self, max_iterations=50, tabu_tenure=10):
        print(f"\n[TabuSearch] Starting optimization for {max_iterations} iterations...")
        
        iteration = 0
        best_makespan = self.best_solution.calculate_makespan()
        
        # Initial validation
        valid, violations = self.best_solution.is_feasible()
        if not valid:
            print(f"[TabuSearch] WARNING: Initial solution is infeasible! {violations[:2]}...")
            best_makespan = float('inf')

        print(f"[TabuSearch] Initial Makespan: {best_makespan:.2f}")

        while iteration < max_iterations:
            iteration += 1
            
            # 1. Generate Neighborhood with Ratios
            # User request: 60% Relocate, 30% Swap, 5% Add Drone, 5% Remove Drone
            # Assumed batch size: 100 candidates per iteration
            BATCH_SIZE = 1000
            
            moves_relocate = self.neighborhood.get_relocate_moves(self.current_solution)
            moves_swap = self.neighborhood.get_swap_moves(self.current_solution)
            moves_add = self.neighborhood.get_add_drone_package_moves(self.current_solution)
            moves_remove = self.neighborhood.get_remove_drone_package_moves(self.current_solution)
            
            import random
            
            # Helper to sample
            def sample_moves(moves, count):
                if len(moves) > count:
                    return random.sample(moves, count)
                return moves

            candidates = []
            candidates.extend(sample_moves(moves_relocate, int(BATCH_SIZE * 0.60)))
            candidates.extend(sample_moves(moves_swap, int(BATCH_SIZE * 0.30)))
            candidates.extend(sample_moves(moves_add, int(BATCH_SIZE * 0.05)))
            candidates.extend(sample_moves(moves_remove, int(BATCH_SIZE * 0.05)))
            
            # 2. Evaluate Candidates
            best_move = None
            best_move_makespan = float('inf')
            best_move_sol = None
            

            
            for move in candidates:
                # Apply move
                neighbor_sol = self.neighborhood.apply_move(self.current_solution, move)
                
                # Check feasibility
                is_feasible, _ = neighbor_sol.is_feasible()
                if not is_feasible:
                    continue
                    
                makespan = neighbor_sol.calculate_makespan()
                
                # Check Tabu & Aspiration
                move_sig = self.get_move_signature(move)
                is_tabu = False
                if move_sig in self.tabu_list:
                    if self.tabu_list[move_sig] > iteration:
                        is_tabu = True
                
                # Aspiration: Nếu tốt hơn Global Best -> override tabu
                if is_tabu and makespan < best_makespan:
                    is_tabu = False
                    
                if not is_tabu:
                    if makespan < best_move_makespan:
                        best_move_makespan = makespan
                        best_move = move
                        best_move_sol = neighbor_sol
            
            # 3. Apply Best Move
            if best_move:
                self.current_solution = best_move_sol
                
                # Update Best Global
                if best_move_makespan < best_makespan:
                    self.best_solution = best_move_sol.copy()
                    best_makespan = best_move_makespan
                    print(f"[TabuSearch] Iter {iteration}: New Best Found! Makespan = {best_makespan:.2f} (Move: {best_move[0]})")
                else:
                    # Log progress occasionally
                    if iteration % 10 == 0:
                        print(f"[TabuSearch] Iter {iteration}: Best Move {best_move_makespan:.2f} (Global Best: {best_makespan:.2f})")
                self.tabu_list[self.get_move_signature(best_move)] = iteration + tabu_tenure
            else:
                print(f"[TabuSearch] Iter {iteration}: No valid non-tabu moves found.")
                break
                
        print(f"[TabuSearch] Finished. Final Makespan: {best_makespan:.2f}")
        return self.best_solution

    def solve4bench(self, max_iterations=50, tabu_tenure=10):
        iteration = 0
        best_makespan = self.best_solution.calculate_makespan()
        
        # Initial validation
        valid, violations = self.best_solution.is_feasible()
        if not valid:
            print(f"[TabuSearch] WARNING: Initial solution is infeasible! {violations[:2]}...")
            best_makespan = float('inf')

        while iteration < max_iterations:
            iteration += 1
            
            # 1. Generate Neighborhood with Ratios
            # User request: 60% Relocate, 30% Swap, 5% Add Drone, 5% Remove Drone
            # Assumed batch size: 100 candidates per iteration
            BATCH_SIZE = 1000
            
            moves_relocate = self.neighborhood.get_relocate_moves(self.current_solution)
            moves_swap = self.neighborhood.get_swap_moves(self.current_solution)
            moves_add = self.neighborhood.get_add_drone_package_moves(self.current_solution)
            moves_remove = self.neighborhood.get_remove_drone_package_moves(self.current_solution)
            
            import random
            
            # Helper to sample
            def sample_moves(moves, count):
                if len(moves) > count:
                    return random.sample(moves, count)
                return moves

            candidates = []
            candidates.extend(sample_moves(moves_relocate, int(BATCH_SIZE * 0.60)))
            candidates.extend(sample_moves(moves_swap, int(BATCH_SIZE * 0.30)))
            candidates.extend(sample_moves(moves_add, int(BATCH_SIZE * 0.05)))
            candidates.extend(sample_moves(moves_remove, int(BATCH_SIZE * 0.05)))
            
            # 2. Evaluate Candidates
            best_move = None
            best_move_makespan = float('inf')
            best_move_sol = None
            

            
            for move in candidates:
                # Apply move
                neighbor_sol = self.neighborhood.apply_move(self.current_solution, move)
                
                # Check feasibility
                is_feasible, _ = neighbor_sol.is_feasible()
                if not is_feasible:
                    continue
                    
                makespan = neighbor_sol.calculate_makespan()
                
                # Check Tabu & Aspiration
                move_sig = self.get_move_signature(move)
                is_tabu = False
                if move_sig in self.tabu_list:
                    if self.tabu_list[move_sig] > iteration:
                        is_tabu = True
                
                # Aspiration: Nếu tốt hơn Global Best -> override tabu
                if is_tabu and makespan < best_makespan:
                    is_tabu = False
                    
                if not is_tabu:
                    if makespan < best_move_makespan:
                        best_move_makespan = makespan
                        best_move = move
                        best_move_sol = neighbor_sol
            
            # 3. Apply Best Move
            if best_move:
                self.current_solution = best_move_sol
                
                # Update Best Global
                if best_move_makespan < best_makespan:
                    self.best_solution = best_move_sol.copy()
                    best_makespan = best_move_makespan
                self.tabu_list[self.get_move_signature(best_move)] = iteration + tabu_tenure
            else:
                break
                
        return self.best_solution