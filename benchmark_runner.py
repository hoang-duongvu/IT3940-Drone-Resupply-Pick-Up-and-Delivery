import sys
import os
import time
import glob
import statistics
import csv
from typing import List, Dict
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models import load_problem
from initializer import SolutionInitializer
from optimization import TabuSearch

def run_benchmark(data_folder: str, output_csv: str, solution_output_dir: str, num_rounds: int, num_iters: int):
    """
    Runs benchmark on all .txt files in data_folder.
    Runs each instance num_rounds times.
    """
    
    # Ensure output dirs exist
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    os.makedirs(solution_output_dir, exist_ok=True)
    
    # Identify instance files
    instance_files = sorted(glob.glob(os.path.join(data_folder, "*.txt")))
    
    if not instance_files:
        print(f"No .txt files found in {data_folder}")
        return

    results = []
    
    print(f"Starting benchmark on {len(instance_files)} instances...")
    print(f"{'Instance':<30} | {'Runs':<5} | {'Best':<10} | {'Avg':<10} | {'Time(s)':<10}")
    print("-" * 80)

    for i, filepath in enumerate(instance_files):
        instance_name = os.path.basename(filepath)
        problem = load_problem(filepath)
        
        makespans = []
        runtimes = []
        best_sol_object = None
        best_makespan_instance = float('inf')
        
        # Run multiple times
        for r in range(num_rounds):
            start_t = time.time()
            
            # Init
            initializer = SolutionInitializer(problem)
            init_sol = initializer.initialize4bench()
            
            # Optimization
            tabu = TabuSearch(problem, init_sol)
            final_sol = tabu.solve4bench(max_iterations=num_iters, tabu_tenure=20)
            
            end_t = time.time()
            duration = end_t - start_t
            
            ms = final_sol.calculate_makespan()
            feasible, _ = final_sol.is_feasible()
            
            if not feasible:
                ms = float('inf') # Penalize infeasible
            
            makespans.append(ms)
            runtimes.append(duration)
            
            if ms < best_makespan_instance:
                best_makespan_instance = ms
                best_sol_object = final_sol.copy()
        
        # Stats
        avg_makespan = statistics.mean(makespans)
        avg_runtime = statistics.mean(runtimes)
        
        # Save best solution
        if best_sol_object:
            sol_filename = instance_name.replace(".txt", "_sol.txt")
            sol_path = os.path.join(solution_output_dir, sol_filename)
            best_sol_object.save_to_file(sol_path)
            
        print(f"{instance_name:<30} | {num_rounds:<5} | {best_makespan_instance:<10.2f} | {avg_makespan:<10.2f} | {avg_runtime:<10.2f}")
        
        results.append({
            "Instance": instance_name,
            "Best Objective": best_makespan_instance,
            "Avg Objective": avg_makespan,
            "Avg Time (s)": avg_runtime
        })

    # Summary table
    df = pd.DataFrame(results)
    
    # Calculate averages for columns
    avg_row = {
        "Instance": "AVERAGE",
        "Best Objective": df["Best Objective"].mean(),
        "Avg Objective": df["Avg Objective"].mean(),
        "Avg Time (s)": df["Avg Time (s)"].mean()
    }
    
    df = pd.concat([df, pd.DataFrame([avg_row])], ignore_index=True)
    
    # Save CSV
    df.to_csv(output_csv, index=False)
    print("\nBenchmark completed.")
    print(f"Results saved to {output_csv}")
    print(f"Solutions saved to {solution_output_dir}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Benchmark Runner 10 Runs')
    parser.add_argument('--data', type=str, default='./data', help='Data directory containing instances')
    parser.add_argument('--output', type=str, default='./output/final2/results.csv', help='Output CSV file path')
    parser.add_argument('--sol-dir', type=str, default='./output/final2/solutions', help='Directory to save best solutions')
    parser.add_argument('--rounds', type=int, default=1, help='Number of runs per instance')
    parser.add_argument('--iters', type=int, default=100, help='Number of Tabu Search iterations')
    
    args = parser.parse_args()
    
    run_benchmark(args.data, args.output, args.sol_dir, args.rounds, args.iters)
