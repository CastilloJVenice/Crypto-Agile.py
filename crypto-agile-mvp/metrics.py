import time
import psutil
import os
import csv

def now_ms():
    return time.perf_counter() * 1000

def snapshot_cpu_memory():
    p = psutil.Process(os.getpid())
    # Interval=0.0 makes it non-blocking and faster
    cpu = psutil.cpu_percent(interval=0.0)
    mem = p.memory_info().rss / (1024 * 1024)  # in MB
    return cpu, mem

def measure_time(func, *args, **kwargs):
    start_wall = now_ms()
    cpu_before, mem_before = snapshot_cpu_memory()
    result = func(*args, **kwargs)
    cpu_after, mem_after = snapshot_cpu_memory()
    end_wall = now_ms()
    return {
        'result': result,
        'time_ms': end_wall - start_wall,
        'cpu_before': cpu_before,
        'cpu_after': cpu_after,
        'mem_before_mb': mem_before,
        'mem_after_mb': mem_after
    }

def write_results_csv(results, filename="results.csv"):
    if not results:
        print("No results to write.")
        return

    # Use the keys of the first result row as the CSV header
    fieldnames = list(results[0].keys())

    try:
        with open(filename, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()   # <-- Writes the column names
            writer.writerows(results)
        print(f"\n[SUCCESS] Results saved to '{filename}'")
    except Exception as e:
        print(f"\n[ERROR] Could not write CSV: {e}")