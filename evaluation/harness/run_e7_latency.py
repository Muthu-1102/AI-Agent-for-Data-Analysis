"""
Experiment E7: Latency Scaling, Stage Profiling, and Concurrency Stress Test
Measures:
1. Local execution scaling across dataset sizes (1k, 10k, 50k, 100k, 250k rows)
2. Stage-level latency decomposition (Local vs Network LLM)
3. Concurrency phenomena: event loop blocking, file cross-talk, stdout contention
"""

import os
import sys
import json
import time
import asyncio
import subprocess
import requests
import numpy as np
import pandas as pd
from typing import Dict, Any, List

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath("backend"))
sys.path.insert(0, os.path.abspath("."))

from agents.schema_agent import SchemaAgent
from agents.execution_agent import ExecutionAgent

def generate_scaling_csv(num_rows: int, filename: str) -> str:
    os.makedirs("data", exist_ok=True)
    filepath = os.path.join("data", filename)
    if os.path.exists(filepath):
        # Check line count
        with open(filepath, "r", encoding="utf-8") as f:
            count = sum(1 for _ in f) - 1
            if count == num_rows:
                return filepath

    print(f"Generating scaling dataset ({num_rows:,} rows) -> {filepath}...")
    np.random.seed(42)
    categories = ["Electronics", "Furniture", "Office Supplies", "Apparel", "Industrial"]
    regions = ["North", "South", "East", "West", "Central"]
    
    df = pd.DataFrame({
        "order_id": [f"ORD-{i:07d}" for i in range(1, num_rows + 1)],
        "category": np.random.choice(categories, size=num_rows),
        "region": np.random.choice(regions, size=num_rows),
        "sales_amount": np.round(np.random.uniform(5.0, 1500.0, size=num_rows), 2),
        "quantity": np.random.randint(1, 20, size=num_rows),
        "discount": np.round(np.random.choice([0.0, 0.05, 0.1, 0.15, 0.25], size=num_rows), 2)
    })
    df.to_csv(filepath, index=False)
    return filepath

def benchmark_local_scaling(sizes: List[int], repetitions: int = 5, output_jsonl: str = "evaluation/results/baseline/e7_scaling_raw.jsonl"):
    print("\n=== Benchmarking Local Compute Scaling Across Dataset Sizes ===")
    schema_agent = SchemaAgent()
    exec_agent = ExecutionAgent()
    
    test_code = (
        "summary = df.groupby('category').agg({'sales_amount': 'sum', 'quantity': 'mean'})\n"
        "top_cat = summary['sales_amount'].idxmax()\n"
        "print(f'Top category: {top_cat}')\n"
    )
    
    records = []
    for sz in sizes:
        fname = f"scaling_{sz}.csv"
        csv_path = generate_scaling_csv(sz, fname)
        file_id = fname
        
        schema_times = []
        exec_times = []
        
        for rep in range(repetitions):
            # 1. Schema loading latency
            t0 = time.perf_counter()
            state = {"file_id": file_id}
            loop = asyncio.new_event_loop()
            res_schema = loop.run_until_complete(schema_agent.process(state))
            t_schema = time.perf_counter() - t0
            schema_times.append(t_schema)
            
            # 2. ExecutionAgent latency
            t1 = time.perf_counter()
            state["generated_code"] = test_code
            res_exec = loop.run_until_complete(exec_agent.process(state))
            t_exec = time.perf_counter() - t1
            exec_times.append(t_exec)
            loop.close()
            
        row = {
            "experiment_id": "E7_scaling",
            "row_count": sz,
            "repetitions": repetitions,
            "schema_latency_p50": round(float(np.median(schema_times)), 5),
            "schema_latency_mean": round(float(np.mean(schema_times)), 5),
            "exec_latency_p50": round(float(np.median(exec_times)), 5),
            "exec_latency_mean": round(float(np.mean(exec_times)), 5),
            "exec_latency_max": round(float(np.max(exec_times)), 5)
        }
        records.append(row)
        print(f"Size {sz:>7,} rows | Schema p50: {row['schema_latency_p50']*1000:6.2f}ms | Exec p50: {row['exec_latency_p50']*1000:6.2f}ms")
        
    os.makedirs(os.path.dirname(output_jsonl), exist_ok=True)
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"Saved local scaling benchmarks to {output_jsonl}")

async def run_concurrent_requests(base_url: str, concurrency_level: int, file_id: str) -> Dict[str, Any]:
    import httpx
    
    # We test concurrent queries where two try to generate plots
    queries = [
        "Plot a bar chart of total sales by region and print total West sales.",
        "Plot a bar chart of total sales by category and print total Electronics sales.",
        "What is the average sales amount per order?",
        "What is the maximum quantity ordered in a single transaction?"
    ][:concurrency_level]
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        start_time = time.perf_counter()
        
        async def send_req(q_idx: int, q_text: str):
            t_req = time.perf_counter()
            try:
                resp = await client.post(
                    f"{base_url}/api/v1/query",
                    json={"query": q_text, "file_id": file_id}
                )
                dur = time.perf_counter() - t_req
                return {
                    "idx": q_idx,
                    "query": q_text,
                    "status_code": resp.status_code,
                    "latency": round(dur, 4),
                    "data": resp.json() if resp.status_code == 200 else resp.text
                }
            except Exception as e:
                dur = time.perf_counter() - t_req
                return {
                    "idx": q_idx,
                    "query": q_text,
                    "status_code": 0,
                    "latency": round(dur, 4),
                    "error": str(e)
                }
                
        tasks = [send_req(i, q) for i, q in enumerate(queries)]
        results = await asyncio.gather(*tasks)
        wall_time = round(time.perf_counter() - start_time, 4)
        
    sum_individual = sum(r["latency"] for r in results)
    return {
        "concurrency_level": concurrency_level,
        "wall_time": wall_time,
        "sum_individual_latencies": round(sum_individual, 4),
        "speedup_factor": round(sum_individual / wall_time, 2) if wall_time > 0 else 1.0,
        "results": results
    }

def benchmark_concurrency(base_url: str = "http://127.0.0.1:8000", output_jsonl: str = "evaluation/results/baseline/e7_concurrency_raw.jsonl"):
    print("\n=== Benchmarking Concurrency & Event Loop Contention ===")
    
    # Verify health
    try:
        r = requests.get(f"{base_url}/health", timeout=5.0)
        if r.status_code != 200:
            print(f"Server health check failed: {r.status_code}")
            return
    except Exception as e:
        print(f"Server not running at {base_url}: {e}")
        return
        
    levels = [1, 2, 4]
    records = []
    file_id = "synthetic_sales.csv"
    
    for lvl in levels:
        print(f"Testing Concurrency = {lvl} simultaneous requests...")
        res = asyncio.run(run_concurrent_requests(base_url, lvl, file_id))
        print(f"  Wall time: {res['wall_time']}s | Sum of latencies: {res['sum_individual_latencies']}s | Speedup: {res['speedup_factor']}x")
        
        # Check for cross-talk / plot issues
        for item in res["results"]:
            data = item.get("data")
            if isinstance(data, dict):
                has_chart = "output_plot.png" in str(data.get("generated_code", ""))
                print(f"   Req {item['idx']}: HTTP {item['status_code']} | Lat: {item['latency']}s | PlotRequested: {has_chart}")
                
        records.append({
            "experiment_id": "E7_concurrency",
            "concurrency_level": lvl,
            "wall_clock_seconds": res["wall_time"],
            "sum_individual_latencies": res["sum_individual_latencies"],
            "speedup_factor": res["speedup_factor"],
            "details": res["results"]
        })
        time.sleep(2.0)
        
    os.makedirs(os.path.dirname(output_jsonl), exist_ok=True)
    with open(output_jsonl, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"Saved concurrency benchmarks to {output_jsonl}")

if __name__ == "__main__":
    # 1. Local scaling test (1k to 250k rows)
    sizes = [1_000, 10_000, 50_000, 100_000, 250_000]
    benchmark_local_scaling(sizes, repetitions=5)
    
    # 2. Concurrency test against live server
    benchmark_concurrency(base_url="http://127.0.0.1:8000")
