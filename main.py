"""
Main - Chạy khởi tạo nghiệm cho bài toán Drone Resupply Pick-up Delivery
"""
import sys
import os

# Thêm thư mục src vào path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models import load_problem, CustomerType
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


def visualize_solution(solution, filename="solution.png"):
    """Vẽ lời giải (nếu có matplotlib)"""
    try:
        import matplotlib
        matplotlib.use('Agg')  # Non-interactive backend
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(1, 1, figsize=(12, 10))

        problem = solution.problem
        depot_x, depot_y = problem.depot

        # Vẽ depot
        ax.plot(depot_x, depot_y, 's', color='black', markersize=15, label='Depot', zorder=5)
        ax.annotate('Depot', (depot_x, depot_y), textcoords="offset points",
                    xytext=(0, 10), ha='center', fontsize=10, fontweight='bold')

        # Màu cho trucks và drones
        truck_colors = ['blue', 'green', 'orange', 'purple']
        drone_colors = ['red', 'magenta']

        # Vẽ truck routes
        for truck in solution.trucks:
            color = truck_colors[truck.truck_id % len(truck_colors)]
            for trip in truck.trips:
                if trip.is_empty():
                    continue

                # Lấy tọa độ các điểm
                x_coords = []
                y_coords = []
                for cid in trip.route:
                    pos = problem.get_position(cid)
                    x_coords.append(pos[0])
                    y_coords.append(pos[1])

                # Vẽ đường đi
                ax.plot(x_coords, y_coords, '-', color=color, linewidth=2,
                        label=f'Truck {truck.truck_id}' if trip == truck.trips[0] else '')

                # Vẽ mũi tên chỉ hướng
                for i in range(len(x_coords) - 1):
                    mid_x = (x_coords[i] + x_coords[i+1]) / 2
                    mid_y = (y_coords[i] + y_coords[i+1]) / 2
                    dx = x_coords[i+1] - x_coords[i]
                    dy = y_coords[i+1] - y_coords[i]
                    ax.annotate('', xy=(mid_x + dx*0.1, mid_y + dy*0.1),
                               xytext=(mid_x - dx*0.1, mid_y - dy*0.1),
                               arrowprops=dict(arrowstyle='->', color=color, lw=1.5))

        # Vẽ drone missions
        for drone in solution.drones:
            color = drone_colors[drone.drone_id % len(drone_colors)]
            for mission in drone.missions:
                meet_pos = problem.get_position(mission.meet_point)
                # Vẽ đường bay (nét đứt)
                ax.plot([depot_x, meet_pos[0]], [depot_y, meet_pos[1]],
                        '--', color=color, linewidth=1.5, alpha=0.7,
                        label=f'Drone {drone.drone_id}' if mission == drone.missions[0] else '')

        # Vẽ customers
        for cid, customer in problem.customers.items():
            if customer.ctype == CustomerType.D:
                marker = 'o'
                color = 'lightblue'
                label = f'{cid}'
            elif customer.ctype == CustomerType.P:
                marker = '^'
                color = 'lightgreen'
                label = f'{cid}(P)'
            else:  # DL
                marker = 'v'
                color = 'lightyellow'
                label = f'{cid}(DL)'

            ax.plot(customer.x, customer.y, marker, color=color,
                    markersize=12, markeredgecolor='black', zorder=4)
            ax.annotate(label, (customer.x, customer.y),
                       textcoords="offset points", xytext=(5, 5),
                       ha='left', fontsize=8)

        # Legend và labels
        ax.set_xlabel('X (km)')
        ax.set_ylabel('Y (km)')
        ax.set_title('Drone Resupply Pick-up Delivery Solution')
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')

        # plt.savefig(filename, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n[Visualization] Saved to {filename}")

    except ImportError:
        print("\n[Visualization] matplotlib not installed. Skipping visualization.")
        print("  Install with: pip install matplotlib")
    except Exception as e:
        print(f"\n[Visualization] Error: {e}")
        print("  Skipping visualization due to compatibility issue.")


def main():
    # Đường dẫn file dữ liệu
    data_file = "./data/test.txt"

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

    # 3. Print solution
    print("\n[Step 3] Solution details:")
    solution.print_solution()

    # 4. Visualize (optional)
    print("\n[Step 4] Visualization...")
    visualize_solution(solution)

    return solution


if __name__ == "__main__":
    solution = main()
