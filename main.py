import sys
import os
import random

# Set seed for reproducibility
random.seed(65)

# Thêm thư mục src vào path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models import load_problem, load_problem_no_C2, CustomerType
from initializer import SolutionInitializer


def print_problem_info(problem):
    """In thông tin bài toán"""
    print("=" * 60)
    print("                 PROBLEM INFORMATION                 ")
    print("=" * 60)
    print(f"Depot: {problem.depot}")
    print(f"Total customers: {len(problem.customers)}")
    print(f"C1 customers (Delivery from depot): {len(problem.c1_customers)}")
    print(f"C2 pairs (Pickup-Delivery): {len(problem.c2_pairs)}")

    print("\n--- C1 Customers (type=D) ---")
    for cid in problem.c1_customers:
        c = problem.get_customer(cid)
        print(f"  Customer {cid}: pos=({c.x:.2f}, {c.y:.2f}), ready_time={c.ready_time}")

    print("\n--- C2 Pairs (Pickup → Delivery) ---")
    for pickup_id, delivery_id in problem.c2_pairs:
        p = problem.get_customer(pickup_id)
        d = problem.get_customer(delivery_id)
        print(f"  Pair {p.pair_id}: {pickup_id}(P) at ({p.x:.2f}, {p.y:.2f}) → {delivery_id}(DL) at ({d.x:.2f}, {d.y:.2f})")

    print("=" * 60)


def visualize_solution(solution, filename="solution.svg"):
    """
    Vẽ lời giải ra file SVG (Dependency-free).
    """
    try:
        if not filename.endswith('.svg'):
            filename = filename.rsplit('.', 1)[0] + '.svg'

        problem = solution.problem
        depot_x, depot_y = problem.depot

        # 1. Calculate Bounding Box
        min_x, max_x = depot_x, depot_x
        min_y, max_y = depot_y, depot_y

        for c in problem.customers.values():
            min_x = min(min_x, c.x)
            max_x = max(max_x, c.x)
            min_y = min(min_y, c.y)
            max_y = max(max_y, c.y)

        # Padding
        padding_pct = 0.1
        width_span = max_x - min_x
        height_span = max_y - min_y
        
        # Avoid division by zero if single point
        if width_span == 0: width_span = 10
        if height_span == 0: height_span = 10

        min_x -= width_span * padding_pct
        max_x += width_span * padding_pct
        min_y -= height_span * padding_pct
        max_y += height_span * padding_pct

        # Canvas Size
        svg_width = 800
        svg_height = 800 * (max_y - min_y) / (max_x - min_x)
        if svg_height > 1000: svg_height = 1000
        if svg_height < 400: svg_height = 400

        def to_svg_coord(x, y):
            # Map x from [min_x, max_x] to [0, svg_width]
            # Map y from [min_y, max_y] to [svg_height, 0] (flip Y)
            sx = (x - min_x) / (max_x - min_x) * svg_width
            sy = svg_height - (y - min_y) / (max_y - min_y) * svg_height
            return sx, sy

        # Colors
        truck_colors = ['#1f77b4', '#2ca02c', '#ff7f0e', '#9467bd', '#8c564b']
        drone_colors = ['#d62728', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        svg_content = []
        svg_content.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" style="background-color: white;">')
        
        # Grid (Optional)
        svg_content.append('<style>.txt { font-family: sans-serif; font-size: 12px; } .label { font-weight: bold; font-size: 10px; }</style>')

        # 2. Draw Drone Missions (Curved lines)
        import math
        for drone in solution.drones:
            color = drone_colors[drone.drone_id % len(drone_colors)]
            for mission in drone.missions:
                d_sx, d_sy = to_svg_coord(depot_x, depot_y)
                m_sx, m_sy = to_svg_coord(*problem.get_position(mission.meet_point))
                
                # Math for Control Point (Curve)
                # Midpoint
                mx, my = (d_sx + m_sx) / 2, (d_sy + m_sy) / 2
                
                # Vector from Depot to Meet
                dx, dy = m_sx - d_sx, m_sy - d_sy
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist == 0: continue

                # Normal vector (perpendicular)
                # (-dy, dx)
                nx, ny = -dy, dx
                
                # Normalize and scale
                # Curve magnitude depends on distance (e.g., 20% of distance)
                offset = dist * 0.2
                
                # Control point
                cx = mx + (nx / dist) * offset
                cy = my + (ny / dist) * offset
                
                # Draw Curve (Path with Quadratic Bezier)
                # M start Q control end
                path_d = f"M {d_sx},{d_sy} Q {cx},{cy} {m_sx},{m_sy}"
                
                svg_content.append(f'<path d="{path_d}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="5,5" opacity="0.8" />')
                
                # Label for Drone (at control point/mid curve)
                svg_content.append(f'<text x="{cx}" y="{cy}" fill="{color}" class="txt" font-weight="bold">D{drone.drone_id}</text>')

        # 3. Draw Truck Routes (Solid lines)
        for truck in solution.trucks:
            color = truck_colors[truck.truck_id % len(truck_colors)]
            for trip in truck.trips:
                if trip.is_empty(): continue
                
                points = []
                for cid in trip.route:
                    points.append(to_svg_coord(*problem.get_position(cid)))
                
                polyline_points = " ".join([f"{p[0]},{p[1]}" for p in points])
                svg_content.append(f'<polyline points="{polyline_points}" fill="none" stroke="{color}" stroke-width="2" />')
                
                # Arrows
                for i in range(len(points) - 1):
                    p1 = points[i]
                    p2 = points[i+1]
                    # Midpoint
                    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
                    # Small circle as arrow head marker (simplified)
                    svg_content.append(f'<circle cx="{mx}" cy="{my}" r="2" fill="{color}" />')
                    
                    if i == 0:
                         svg_content.append(f'<text x="{mx}" y="{my-5}" fill="{color}" class="txt" font-weight="bold">T{truck.truck_id}</text>')

        # 4. Draw Locations
        
        # Depot
        dx, dy = to_svg_coord(depot_x, depot_y)
        svg_content.append(f'<rect x="{dx-10}" y="{dy-10}" width="20" height="20" fill="black" />')
        svg_content.append(f'<text x="{dx}" y="{dy-15}" text-anchor="middle" class="label">DEPOT</text>')

        # Customers
        for cid, customer in problem.customers.items():
            cx, cy = to_svg_coord(customer.x, customer.y)
            
            fill = "gray"
            shape = "circle" # default
            
            if customer.ctype == CustomerType.D:
                fill = "lightblue"
                shape = "circle"
            elif customer.ctype == CustomerType.P:
                fill = "lightgreen" # Pickup
                shape = "rect"
            elif customer.ctype == CustomerType.DL:
                fill = "lightyellow" # Delivery of Pair
                shape = "triangle"
            
            stroke = "black"
            
            if shape == "circle":
                svg_content.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
            elif shape == "rect":
                svg_content.append(f'<rect x="{cx-6}" y="{cy-6}" width="12" height="12" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
            elif shape == "triangle":
                # Inverted triangle
                pts = f"{cx},{cy+6} {cx-6},{cy-6} {cx+6},{cy-6}"
                svg_content.append(f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')

            # Label
            svg_content.append(f'<text x="{cx}" y="{cy-8}" text-anchor="middle" class="label">{cid}</text>')

        # Legend
        svg_content.append(f'<rect x="10" y="10" width="150" height="90" fill="white" stroke="black" opacity="0.8"/>')
        svg_content.append(f'<text x="20" y="30" class="txt">Depot (Square)</text>')
        svg_content.append(f'<text x="20" y="50" class="txt"><tspan fill="lightblue">●</tspan> C1 Customer</text>')
        svg_content.append(f'<text x="20" y="70" class="txt"><tspan fill="lightgreen">■</tspan> Pickup (C2)</text>')
        svg_content.append(f'<text x="20" y="90" class="txt"><tspan fill="lightyellow">▼</tspan> Delivery (C2)</text>')

        svg_content.append('</svg>')
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(svg_content))
            
        print(f"\n[Visualization] Saved solution to {filename}")

    except Exception as e:
        print(f"\n[Visualization] Error generating SVG: {e}")
        import traceback
        traceback.print_exc()

def main():
    # Đường dẫn file dữ liệ
    import argparse
    parser = argparse.ArgumentParser(description='Drone Resupply VRP')
    parser.add_argument('--input', type=str, default="./data/0130/20_instances/U_20_0.5_Num_1_pd.txt", help='Path to input data file')
    args = parser.parse_args()
    data_file = args.input

    print("\n" + "=" * 60)
    print("   DRONE RESUPPLY PICK-UP DELIVERY - SOLUTION INITIALIZER")
    print("=" * 60)

    # 1. Load problem
    print(f"\n[Step 1] Loading problem from: {data_file}")
    problem = load_problem(data_file)
    print_problem_info(problem)

    # 2. Initialize solution
    print("\n[Step 2] Initializing solution...")
    initializer = SolutionInitializer(problem)
    solution = initializer.initialize()

    # 3. Print initial solution
    print("\n[Step 3] Initial Solution details:")
    solution.print_solution()

    # 4. Optimize with Tabu Search
    print("\n[Step 4] Running Tabu Search Optimization...")
    from optimization import TabuSearch
    tabu = TabuSearch(problem, solution)
    optimized_solution = tabu.solve(max_iterations=200, tabu_tenure=20)

    print("\n[Step 5] Optimized Solution details:")
    optimized_solution.print_solution()

    # 5. Visualize (optional)
    print("\n[Step 6] Visualization...")
    visualize_solution(optimized_solution)

if __name__ == "__main__":
    solution = main()
