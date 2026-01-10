import os
import sys
import glob
import time
import csv
from typing import List

# Setup path to import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from models import load_problem_no_C2
from initializer import SolutionInitializer
from optimization import TabuSearch
from config import print_config

def run_benchmark(data_dir: str):
    """
    Run benchmark on all .txt files in data_dir
    """
    # Find all txt files
    files = sorted(glob.glob(os.path.join(data_dir, "*.txt")))
    
    if not files:
        print(f"No files found in {data_dir}")
        return

    results = []
    
    print(f"Starting benchmark on {len(files)} instances in {data_dir}...")
    print("-" * 100)
    print(f"{'Instance':<20} | {'Init Makespan':<15} | {'Best Makespan':<15} | {'Gap (%)':<10} | {'Time (s)':<10}")
    print("-" * 100)

    total_start_time = time.time()

    for filepath in files:
        filename = os.path.basename(filepath)
        
        try:
            # 1. Load Problem
            problem = load_problem_no_C2(filepath)
            
            # 2. Initialize
            initializer = SolutionInitializer(problem)
            init_sol = initializer.initialize4bench()
            init_makespan = init_sol.calculate_makespan()
            
            # 3. Optimize
            start_time = time.time()
            tabu = TabuSearch(problem, init_sol)
            # Use same settings as main.py
            best_sol = tabu.solve4bench(max_iterations=300, tabu_tenure=20)
            end_time = time.time()
            
            best_makespan = best_sol.calculate_makespan()
            duration = end_time - start_time
            
            gap = ((init_makespan - best_makespan) / init_makespan) * 100
            
            print(f"{filename:<20} | {init_makespan:<15.2f} | {best_makespan:<15.2f} | {gap:<10.2f} | {duration:<10.2f}")
            
            results.append({
                'Instance': filename,
                'Init Makespan': init_makespan,
                'Best Makespan': best_makespan,
                'Gap (%)': gap,
                'Time (s)': duration
            })
            
        except Exception as e:
            print(f"{filename:<20} | ERROR: {str(e)}")

    print("-" * 100)
    total_duration = time.time() - total_start_time
    print(f"Benchmark completed in {total_duration:.2f} seconds.")
    
    if results:
        # Calculate stats manually
        avg_init = sum(r['Init Makespan'] for r in results) / len(results)
        avg_best = sum(r['Best Makespan'] for r in results) / len(results)
        avg_gap = sum(r['Gap (%)'] for r in results) / len(results)
        avg_time = sum(r['Time (s)'] for r in results) / len(results)
        
        print("\nSummary Statistics (Average):")
        print(f"Init Makespan: {avg_init:.2f}")
        print(f"Best Makespan: {avg_best:.2f}")
        print(f"Gap (%):       {avg_gap:.2f}%")
        print(f"Time (s):      {avg_time:.2f}s")

        # Save to CSV
        import csv
        output_file = "./data/sample_output/benchmark_results.csv"
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['Instance', 'Init Makespan', 'Best Makespan', 'Gap (%)', 'Time (s)'])
            writer.writeheader()
            writer.writerows(results)
        print(f"\nResults saved to {output_file}")

if __name__ == "__main__":
    data_folder = "./data/10_instances"
    run_benchmark(data_folder)
