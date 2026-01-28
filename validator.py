import sys
import os
import argparse
from typing import List

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models import load_problem, Solution

def validate_solution(instance_file: str, solution_file: str):
    """
    Validates a solution file against an instance file.
    """
    print(f"Validating solution: {solution_file}")
    print(f"Against instance:  {instance_file}")
    print("-" * 60)

    try:
        # 1. Load Problem
        if not os.path.exists(instance_file):
            print(f"ERROR: Instance file not found: {instance_file}")
            return
        
        problem = load_problem(instance_file)
        print(f"Problem loaded. Customers: {len(problem.customers)}")

        # 2. Load Solution
        if not os.path.exists(solution_file):
            print(f"ERROR: Solution file not found: {solution_file}")
            return

        solution = Solution.load_from_file(solution_file, problem)
        print("Solution structure loaded.")
        print(f"  Trucks: {len(solution.trucks)}")
        print(f"  Drones: {len(solution.drones)}")

        # 3. Check Feasibility
        feasible, violations = solution.is_feasible()
        makespan = solution.calculate_makespan()

        print("-" * 60)
        if feasible:
            print("RESULT: VALID SOLUTION")
            print(f"Objective Value (Makespan): {makespan:.2f}")
        else:
            print("RESULT: INVALID SOLUTION")
            print("Violations:")
            for v in violations:
                print(f"  - {v}")
        print("-" * 60)

    except Exception as e:
        print(f"ERROR during validation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Drone Resupply Solution Validator')
    parser.add_argument('--instance', type=str, default='./data/0130/10_instances/U_10_0.5_Num_1_pd.txt', help='Path to input data file (instance)')
    parser.add_argument('--solution', type=str, default='./output/10I/solutions/U_10_0.5_Num_1_pd_sol.txt', help='Path to solution text file')
    
    args = parser.parse_args()
    
    validate_solution(args.instance, args.solution)
