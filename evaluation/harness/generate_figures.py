"""
Automated Figure Generator for Evaluation Report
Reads evaluation/results/baseline/ and generates publication-grade figures:
1. fig1_accuracy_by_category.png: Computation correctness by analytical query category
2. fig2_failure_taxonomy.png: Distribution of pipeline failure modes
3. fig3_latency_breakdown.png: Per-stage latency decomposition (LLM vs Local)
4. fig4_security_matrix.png: Malicious block rate vs Benign false positive rate
"""

import os
import sys
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def load_jsonl(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]

def generate_all_figures():
    os.makedirs("evaluation/figures", exist_ok=True)
    summary_path = "evaluation/results/baseline/baseline_summary.json"
    e1_path = "evaluation/results/baseline/e1_heldout_raw.jsonl"
    e4_path = "evaluation/results/baseline/e4_security_raw.jsonl"
    
    if not os.path.exists(e1_path):
        print(f"Waiting for {e1_path} to finish...")
        return
        
    e1_records = load_jsonl(e1_path)
    if not e1_records:
        return
        
    print(f"Generating figures from {len(e1_records)} held-out evaluation records...")
    
    # ----------------------------------------------------
    # FIG 1: Accuracy by Question Category
    # ----------------------------------------------------
    cats = {}
    for r in e1_records:
        c = r.get("category", "General")
        cats.setdefault(c, [0, 0])
        cats[c][0] += 1
        if r.get("computation_correct"):
            cats[c][1] += 1
            
    cat_names = sorted(cats.keys())
    cat_rates = [cats[k][1] / cats[k][0] * 100 for k in cat_names]
    cat_counts = [f"n={cats[k][0]}" for k in cat_names]
    
    plt.figure(figsize=(10, 5))
    bars = plt.barh(cat_names, cat_rates, color="#2563EB", edgecolor="#1E40AF", height=0.6)
    plt.xlim(0, 105)
    plt.xlabel("Computation Correctness (%)", fontsize=11, fontweight="bold")
    plt.title("Baseline Accuracy by Analytical Query Category (Held-Out, 3 Reps)", fontsize=13, fontweight="bold", pad=12)
    plt.grid(axis="x", linestyle="--", alpha=0.5)
    
    for bar, rate, count in zip(bars, cat_rates, cat_counts):
        plt.text(bar.get_width() + 1.5, bar.get_y() + bar.get_height()/2, f"{rate:.1f}% ({count})", 
                 va="center", fontsize=9, fontweight="bold", color="#1E293B")
                 
    plt.tight_layout()
    plt.savefig("evaluation/figures/fig1_accuracy_by_category.png", dpi=200)
    plt.close()
    print("Saved evaluation/figures/fig1_accuracy_by_category.png")
    
    # ----------------------------------------------------
    # FIG 2: Failure Taxonomy Distribution
    # ----------------------------------------------------
    taxonomy = {}
    for r in e1_records:
        out = r.get("outcome_classification", "UNCLASSIFIED")
        if out not in ("CORRECT", "SUCCESS_BOTH"):
            taxonomy[out] = taxonomy.get(out, 0) + 1
            
    if taxonomy:
        labels = list(taxonomy.keys())
        sizes = list(taxonomy.values())
        colors = ["#EF4444", "#F59E0B", "#8B5CF6", "#EC4899", "#3B82F6", "#64748B"][:len(labels)]
        
        plt.figure(figsize=(8, 6))
        wedges, texts, autotexts = plt.pie(
            sizes, labels=labels, autopct="%1.1f%%", startangle=140, 
            colors=colors, wedgeprops=dict(width=0.4, edgecolor="w")
        )
        for at in autotexts:
            at.set_color("white")
            at.set_fontweight("bold")
        plt.title("Distribution of Pipeline Failure Modes (E2 Taxonomy)", fontsize=13, fontweight="bold")
        plt.tight_layout()
        plt.savefig("evaluation/figures/fig2_failure_taxonomy.png", dpi=200)
        plt.close()
        print("Saved evaluation/figures/fig2_failure_taxonomy.png")
        
    # ----------------------------------------------------
    # FIG 3: Latency Decomposition (Stage Breakdown)
    # ----------------------------------------------------
    stage_lat = {}
    for r in e1_records:
        sl = r.get("stage_latencies", {})
        for stg, lat in sl.items():
            stage_lat.setdefault(stg, []).append(lat)
            
    if stage_lat:
        stage_names = ["SchemaAgent", "PromptAgent", "CodeAgent", "ValidationAgent", "ExecutionAgent", "ReportAgent"]
        stage_names = [s for s in stage_names if s in stage_lat]
        means = [np.mean(stage_lat[s]) for s in stage_names]
        stds = [np.std(stage_lat[s]) for s in stage_names]
        
        plt.figure(figsize=(9, 5))
        x_pos = np.arange(len(stage_names))
        colors = ["#94A3B8", "#CBD5E1", "#3B82F6", "#F59E0B", "#10B981", "#8B5CF6"][:len(stage_names)]
        plt.bar(x_pos, means, yerr=stds, align="center", alpha=0.85, color=colors, capsize=6, edgecolor="#334155")
        plt.xticks(x_pos, [s.replace("Agent", "") for s in stage_names], fontsize=10, fontweight="bold")
        plt.ylabel("Latency (Seconds)", fontsize=11, fontweight="bold")
        plt.title("Per-Stage Mean Latency Decomposition (with std dev)", fontsize=13, fontweight="bold", pad=12)
        plt.grid(axis="y", linestyle="--", alpha=0.5)
        
        for i, m in enumerate(means):
            plt.text(i, m + (stds[i] if stds[i] else 0.05) + 0.05, f"{m:.2f}s", ha="center", fontsize=9, fontweight="bold")
            
        plt.tight_layout()
        plt.savefig("evaluation/figures/fig3_latency_breakdown.png", dpi=200)
        plt.close()
        print("Saved evaluation/figures/fig3_latency_breakdown.png")
        
    # ----------------------------------------------------
    # FIG 4: Security Matrix (Malicious Block vs Benign FP)
    # ----------------------------------------------------
    e4_records = load_jsonl(e4_path)
    if e4_records:
        mal = [r for r in e4_records if r.get("probe_type") == "MALICIOUS"]
        ben = [r for r in e4_records if r.get("probe_type") == "BENIGN"]
        
        val_mal = sum(1 for r in mal if r.get("validation_agent_blocked")) / len(mal) * 100
        sand_mal = sum(1 for r in mal if r.get("sandbox_blocked")) / len(mal) * 100
        e2e_mal = sum(1 for r in mal if r.get("end_to_end_blocked")) / len(mal) * 100
        
        val_ben = sum(1 for r in ben if r.get("validation_agent_blocked")) / len(ben) * 100
        sand_ben = sum(1 for r in ben if r.get("sandbox_blocked")) / len(ben) * 100
        e2e_ben = sum(1 for r in ben if r.get("end_to_end_blocked")) / len(ben) * 100
        
        layers = ["ValidationAgent\n(AST)", "Sandbox\n(Substring)", "End-to-End\n(Ensemble)"]
        x = np.arange(len(layers))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(8, 5))
        rects1 = ax.bar(x - width/2, [val_mal, sand_mal, e2e_mal], width, label="Malicious Block Rate (%)", color="#10B981")
        rects2 = ax.bar(x + width/2, [val_ben, sand_ben, e2e_ben], width, label="Benign False Positive Rate (%)", color="#EF4444")
        
        ax.set_ylabel("Rate (%)", fontsize=11, fontweight="bold")
        ax.set_title("Security Architecture Comparison: Block vs False Positive", fontsize=13, fontweight="bold", pad=12)
        ax.set_xticks(x)
        ax.set_xticklabels(layers, fontsize=10, fontweight="bold")
        ax.legend(frameon=True)
        ax.set_ylim(0, 110)
        ax.grid(axis="y", linestyle="--", alpha=0.5)
        
        for bar in rects1:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"{bar.get_height():.1f}%", ha="center", fontsize=9, fontweight="bold")
        for bar in rects2:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2, f"{bar.get_height():.1f}%", ha="center", fontsize=9, fontweight="bold")
            
        plt.tight_layout()
        plt.savefig("evaluation/figures/fig4_security_matrix.png", dpi=200)
        plt.close()
        print("Saved evaluation/figures/fig4_security_matrix.png")

if __name__ == "__main__":
    generate_all_figures()
