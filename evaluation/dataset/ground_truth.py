"""
Deterministic Ground Truth Calculation Engine
Computes exact ground-truth values using pandas/numpy independently of the LLM or application code.
Generates questions_dev.json (12 questions, 20%) and questions_heldout.json (48 questions, 80%).
"""

import json
import os
import hashlib
import numpy as np
import pandas as pd

def compute_ground_truth(data_dir="data", output_dir="evaluation/dataset"):
    os.makedirs(output_dir, exist_ok=True)
    
    sales_path = os.path.join(data_dir, "synthetic_sales.csv")
    hr_path = os.path.join(data_dir, "synthetic_hr.csv")
    sensor_path = os.path.join(data_dir, "synthetic_sensor.csv")
    messy_path = os.path.join(data_dir, "synthetic_messy.csv")

    df_sales = pd.read_csv(sales_path)
    df_hr = pd.read_csv(hr_path)
    df_sensor = pd.read_csv(sensor_path)
    df_messy = pd.read_csv(messy_path)

    # ─────────────────────────────────────────────────────────────
    # DEV QUESTIONS (12 questions, 20% split)
    # ─────────────────────────────────────────────────────────────
    dev_specs = [
        # Sales Dev
        {
            "id": "DEV-01",
            "dataset": "synthetic_sales.csv",
            "category": "simple_aggregate",
            "question": "What is the total sum of sales_amount?",
            "type": "numeric",
            "ground_truth": round(float(df_sales["sales_amount"].sum()), 2),
            "tolerance": 0.01,
        },
        {
            "id": "DEV-02",
            "dataset": "synthetic_sales.csv",
            "category": "groupby",
            "question": "Which region has the highest total profit?",
            "type": "categorical",
            "ground_truth": str(df_sales.groupby("region")["profit"].sum().idxmax()),
        },
        {
            "id": "DEV-03",
            "dataset": "synthetic_sales.csv",
            "category": "filtering",
            "question": "How many orders have a discount greater than 0.15?",
            "type": "numeric",
            "ground_truth": int((df_sales["discount"] > 0.15).sum()),
            "tolerance": 0.0,
        },
        # HR Dev
        {
            "id": "DEV-04",
            "dataset": "synthetic_hr.csv",
            "category": "simple_aggregate",
            "question": "What is the average salary across all employees?",
            "type": "numeric",
            "ground_truth": round(float(df_hr["salary"].mean()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "DEV-05",
            "dataset": "synthetic_hr.csv",
            "category": "top_k",
            "question": "What is the highest tenure_years recorded in the dataset?",
            "type": "numeric",
            "ground_truth": int(df_hr["tenure_years"].max()),
            "tolerance": 0.0,
        },
        {
            "id": "DEV-06",
            "dataset": "synthetic_hr.csv",
            "category": "percentages",
            "question": "What is the overall attrition rate as a percentage of employees with attrition equal to Yes?",
            "type": "numeric",
            "ground_truth": round(float((df_hr["attrition"] == "Yes").mean() * 100), 2),
            "tolerance": 0.1,
        },
        # Sensor Dev
        {
            "id": "DEV-07",
            "dataset": "synthetic_sensor.csv",
            "category": "simple_aggregate",
            "question": "What is the maximum temperature_c recorded across all sensors?",
            "type": "numeric",
            "ground_truth": round(float(df_sensor["temperature_c"].max()), 2),
            "tolerance": 0.01,
        },
        {
            "id": "DEV-08",
            "dataset": "synthetic_sensor.csv",
            "category": "filtering",
            "question": "How many readings have status equal to Critical?",
            "type": "numeric",
            "ground_truth": int((df_sensor["status"] == "Critical").sum()),
            "tolerance": 0.0,
        },
        {
            "id": "DEV-09",
            "dataset": "synthetic_sensor.csv",
            "category": "groupby",
            "question": "What is the average pressure_kpa for sensor SENSOR-A?",
            "type": "numeric",
            "ground_truth": round(float(df_sensor[df_sensor["sensor_id"] == "SENSOR-A"]["pressure_kpa"].mean()), 2),
            "tolerance": 0.05,
        },
        # Messy Dev
        {
            "id": "DEV-10",
            "dataset": "synthetic_messy.csv",
            "category": "missing_values",
            "question": "How many missing or null values are there in the category column?",
            "type": "numeric",
            "ground_truth": int(df_messy["category"].isna().sum()),
            "tolerance": 0.0,
        },
        {
            "id": "DEV-11",
            "dataset": "synthetic_messy.csv",
            "category": "simple_aggregate",
            "question": "What is the total sum of units_sold?",
            "type": "numeric",
            "ground_truth": round(float(df_messy["units_sold"].dropna().sum()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "DEV-12",
            "dataset": "synthetic_sales.csv",
            "category": "chart_request",
            "question": "Plot a bar chart of total sales_amount by region and print the total sales of the West region.",
            "type": "numeric",
            "ground_truth": round(float(df_sales[df_sales["region"] == "West"]["sales_amount"].sum()), 2),
            "tolerance": 0.05,
        },
    ]

    # ─────────────────────────────────────────────────────────────
    # HELD-OUT QUESTIONS (48 questions, 80% split)
    # ─────────────────────────────────────────────────────────────
    heldout_specs = [
        # --- SALES (14 questions) ---
        {
            "id": "HELD-01",
            "dataset": "synthetic_sales.csv",
            "category": "simple_aggregate",
            "question": "What is the average sales_amount per order?",
            "type": "numeric",
            "ground_truth": round(float(df_sales["sales_amount"].mean()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "HELD-02",
            "dataset": "synthetic_sales.csv",
            "category": "simple_aggregate",
            "question": "What is the minimum sales_amount in the dataset?",
            "type": "numeric",
            "ground_truth": round(float(df_sales["sales_amount"].min()), 2),
            "tolerance": 0.01,
        },
        {
            "id": "HELD-03",
            "dataset": "synthetic_sales.csv",
            "category": "simple_aggregate",
            "question": "What is the median profit across all orders?",
            "type": "numeric",
            "ground_truth": round(float(df_sales["profit"].median()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "HELD-04",
            "dataset": "synthetic_sales.csv",
            "category": "simple_aggregate",
            "question": "What is the total quantity of items ordered?",
            "type": "numeric",
            "ground_truth": int(df_sales["quantity"].sum()),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-05",
            "dataset": "synthetic_sales.csv",
            "category": "groupby",
            "question": "What is the total sales_amount for the Electronics category?",
            "type": "numeric",
            "ground_truth": round(float(df_sales[df_sales["product_category"] == "Electronics"]["sales_amount"].sum()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "HELD-06",
            "dataset": "synthetic_sales.csv",
            "category": "groupby",
            "question": "What is the average profit in the North region?",
            "type": "numeric",
            "ground_truth": round(float(df_sales[df_sales["region"] == "North"]["profit"].mean()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "HELD-07",
            "dataset": "synthetic_sales.csv",
            "category": "groupby",
            "question": "Which product_category has the highest total quantity sold?",
            "type": "categorical",
            "ground_truth": str(df_sales.groupby("product_category")["quantity"].sum().idxmax()),
        },
        {
            "id": "HELD-08",
            "dataset": "synthetic_sales.csv",
            "category": "filtering",
            "question": "How many orders had a sales_amount greater than 1000?",
            "type": "numeric",
            "ground_truth": int((df_sales["sales_amount"] > 1000).sum()),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-09",
            "dataset": "synthetic_sales.csv",
            "category": "filtering",
            "question": "What is the total profit for orders in the South region with discount equal to 0.0?",
            "type": "numeric",
            "ground_truth": round(float(df_sales[(df_sales["region"] == "South") & (df_sales["discount"] == 0.0)]["profit"].sum()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "HELD-10",
            "dataset": "synthetic_sales.csv",
            "category": "percentages",
            "question": "What percentage of all orders belong to the Furniture category?",
            "type": "numeric",
            "ground_truth": round(float((df_sales["product_category"] == "Furniture").mean() * 100), 2),
            "tolerance": 0.1,
        },
        {
            "id": "HELD-11",
            "dataset": "synthetic_sales.csv",
            "category": "top_k",
            "question": "What is the order_id of the order with the single highest sales_amount?",
            "type": "numeric",
            "ground_truth": int(df_sales.loc[df_sales["sales_amount"].idxmax()]["order_id"]),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-12",
            "dataset": "synthetic_sales.csv",
            "category": "correlations",
            "question": "What is the Pearson correlation between sales_amount and profit?",
            "type": "numeric",
            "ground_truth": round(float(df_sales["sales_amount"].corr(df_sales["profit"])), 3),
            "tolerance": 0.01,
        },
        {
            "id": "HELD-13",
            "dataset": "synthetic_sales.csv",
            "category": "multi_step",
            "question": "What is the difference between the maximum sales_amount and the minimum sales_amount?",
            "type": "numeric",
            "ground_truth": round(float(df_sales["sales_amount"].max() - df_sales["sales_amount"].min()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "HELD-14",
            "dataset": "synthetic_sales.csv",
            "category": "chart_request",
            "question": "Create a bar chart showing average sales_amount per product_category, and print the average for Clothing.",
            "type": "numeric",
            "ground_truth": round(float(df_sales[df_sales["product_category"] == "Clothing"]["sales_amount"].mean()), 2),
            "tolerance": 0.05,
        },

        # --- HR & EMPLOYEES (14 questions) ---
        {
            "id": "HELD-15",
            "dataset": "synthetic_hr.csv",
            "category": "simple_aggregate",
            "question": "What is the total annual payroll (sum of salary) for all employees?",
            "type": "numeric",
            "ground_truth": int(df_hr["salary"].sum()),
            "tolerance": 1.0,
        },
        {
            "id": "HELD-16",
            "dataset": "synthetic_hr.csv",
            "category": "simple_aggregate",
            "question": "What is the median salary of employees?",
            "type": "numeric",
            "ground_truth": round(float(df_hr["salary"].median()), 2),
            "tolerance": 1.0,
        },
        {
            "id": "HELD-17",
            "dataset": "synthetic_hr.csv",
            "category": "simple_aggregate",
            "question": "What is the average tenure_years across all employees?",
            "type": "numeric",
            "ground_truth": round(float(df_hr["tenure_years"].mean()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "HELD-18",
            "dataset": "synthetic_hr.csv",
            "category": "groupby",
            "question": "Which department has the highest average salary?",
            "type": "categorical",
            "ground_truth": str(df_hr.groupby("department")["salary"].mean().idxmax()),
        },
        {
            "id": "HELD-19",
            "dataset": "synthetic_hr.csv",
            "category": "groupby",
            "question": "What is the total number of employees in the Engineering department?",
            "type": "numeric",
            "ground_truth": int((df_hr["department"] == "Engineering").sum()),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-20",
            "dataset": "synthetic_hr.csv",
            "category": "groupby",
            "question": "What is the average salary in the Sales department?",
            "type": "numeric",
            "ground_truth": round(float(df_hr[df_hr["department"] == "Sales"]["salary"].mean()), 2),
            "tolerance": 1.0,
        },
        {
            "id": "HELD-21",
            "dataset": "synthetic_hr.csv",
            "category": "filtering",
            "question": "How many employees have a performance_rating of 5?",
            "type": "numeric",
            "ground_truth": int((df_hr["performance_rating"] == 5).sum()),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-22",
            "dataset": "synthetic_hr.csv",
            "category": "filtering",
            "question": "How many employees in Finance have tenure_years greater than 5?",
            "type": "numeric",
            "ground_truth": int(((df_hr["department"] == "Finance") & (df_hr["tenure_years"] > 5)).sum()),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-23",
            "dataset": "synthetic_hr.csv",
            "category": "percentages",
            "question": "What percentage of employees in the Engineering department have attrition equal to Yes?",
            "type": "numeric",
            "ground_truth": round(float((df_hr[df_hr["department"] == "Engineering"]["attrition"] == "Yes").mean() * 100), 2),
            "tolerance": 0.1,
        },
        {
            "id": "HELD-24",
            "dataset": "synthetic_hr.csv",
            "category": "top_k",
            "question": "What is the maximum salary recorded in the dataset?",
            "type": "numeric",
            "ground_truth": int(df_hr["salary"].max()),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-25",
            "dataset": "synthetic_hr.csv",
            "category": "correlations",
            "question": "What is the correlation between tenure_years and salary?",
            "type": "numeric",
            "ground_truth": round(float(df_hr["tenure_years"].corr(df_hr["salary"])), 3),
            "tolerance": 0.01,
        },
        {
            "id": "HELD-26",
            "dataset": "synthetic_hr.csv",
            "category": "multi_step",
            "question": "What is the average salary of employees who have both a performance_rating of 4 or 5 and tenure_years greater than 3?",
            "type": "numeric",
            "ground_truth": round(float(df_hr[(df_hr["performance_rating"] >= 4) & (df_hr["tenure_years"] > 3)]["salary"].mean()), 2),
            "tolerance": 1.0,
        },
        {
            "id": "HELD-27",
            "dataset": "synthetic_hr.csv",
            "category": "groupby",
            "question": "What is the minimum salary in the Human Resources department?",
            "type": "numeric",
            "ground_truth": int(df_hr[df_hr["department"] == "Human Resources"]["salary"].min()),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-28",
            "dataset": "synthetic_hr.csv",
            "category": "chart_request",
            "question": "Plot a histogram of employee salaries and print the standard deviation of salary.",
            "type": "numeric",
            "ground_truth": round(float(df_hr["salary"].std()), 2),
            "tolerance": 1.0,
        },

        # --- SENSOR & TIMESERIES (12 questions) ---
        {
            "id": "HELD-29",
            "dataset": "synthetic_sensor.csv",
            "category": "simple_aggregate",
            "question": "What is the overall average temperature_c across all records?",
            "type": "numeric",
            "ground_truth": round(float(df_sensor["temperature_c"].mean()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "HELD-30",
            "dataset": "synthetic_sensor.csv",
            "category": "simple_aggregate",
            "question": "What is the minimum pressure_kpa recorded in the dataset?",
            "type": "numeric",
            "ground_truth": round(float(df_sensor["pressure_kpa"].min()), 2),
            "tolerance": 0.01,
        },
        {
            "id": "HELD-31",
            "dataset": "synthetic_sensor.csv",
            "category": "simple_aggregate",
            "question": "What is the average vibration_g across all sensors?",
            "type": "numeric",
            "ground_truth": round(float(df_sensor["vibration_g"].mean()), 4),
            "tolerance": 0.001,
        },
        {
            "id": "HELD-32",
            "dataset": "synthetic_sensor.csv",
            "category": "groupby",
            "question": "Which sensor_id has the highest average temperature_c?",
            "type": "categorical",
            "ground_truth": str(df_sensor.groupby("sensor_id")["temperature_c"].mean().idxmax()),
        },
        {
            "id": "HELD-33",
            "dataset": "synthetic_sensor.csv",
            "category": "groupby",
            "question": "What is the average temperature_c for sensor SENSOR-D?",
            "type": "numeric",
            "ground_truth": round(float(df_sensor[df_sensor["sensor_id"] == "SENSOR-D"]["temperature_c"].mean()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "HELD-34",
            "dataset": "synthetic_sensor.csv",
            "category": "filtering",
            "question": "How many readings have a vibration_g greater than 0.08?",
            "type": "numeric",
            "ground_truth": int((df_sensor["vibration_g"] > 0.08).sum()),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-35",
            "dataset": "synthetic_sensor.csv",
            "category": "percentages",
            "question": "What percentage of sensor readings have a status equal to Normal?",
            "type": "numeric",
            "ground_truth": round(float((df_sensor["status"] == "Normal").mean() * 100), 2),
            "tolerance": 0.1,
        },
        {
            "id": "HELD-36",
            "dataset": "synthetic_sensor.csv",
            "category": "correlations",
            "question": "What is the correlation between temperature_c and pressure_kpa?",
            "type": "numeric",
            "ground_truth": round(float(df_sensor["temperature_c"].corr(df_sensor["pressure_kpa"])), 3),
            "tolerance": 0.01,
        },
        {
            "id": "HELD-37",
            "dataset": "synthetic_sensor.csv",
            "category": "top_k",
            "question": "What is the maximum pressure_kpa recorded by SENSOR-B?",
            "type": "numeric",
            "ground_truth": round(float(df_sensor[df_sensor["sensor_id"] == "SENSOR-B"]["pressure_kpa"].max()), 2),
            "tolerance": 0.01,
        },
        {
            "id": "HELD-38",
            "dataset": "synthetic_sensor.csv",
            "category": "multi_step",
            "question": "What is the standard deviation of temperature_c for records where status is Critical?",
            "type": "numeric",
            "ground_truth": round(float(df_sensor[df_sensor["status"] == "Critical"]["temperature_c"].std()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "HELD-39",
            "dataset": "synthetic_sensor.csv",
            "category": "filtering",
            "question": "How many records have temperature_c above 75 and pressure_kpa below 101?",
            "type": "numeric",
            "ground_truth": int(((df_sensor["temperature_c"] > 75) & (df_sensor["pressure_kpa"] < 101)).sum()),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-40",
            "dataset": "synthetic_sensor.csv",
            "category": "chart_request",
            "question": "Plot the temperature_c distribution by sensor_id and print the lowest temperature_c for SENSOR-C.",
            "type": "numeric",
            "ground_truth": round(float(df_sensor[df_sensor["sensor_id"] == "SENSOR-C"]["temperature_c"].min()), 2),
            "tolerance": 0.05,
        },

        # --- MESSY DATA (8 questions) ---
        {
            "id": "HELD-41",
            "dataset": "synthetic_messy.csv",
            "category": "missing_values",
            "question": "How many missing or null values exist in the units_sold column?",
            "type": "numeric",
            "ground_truth": int(df_messy["units_sold"].isna().sum()),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-42",
            "dataset": "synthetic_messy.csv",
            "category": "simple_aggregate",
            "question": "What is the average of units_sold for rows that are not null?",
            "type": "numeric",
            "ground_truth": round(float(df_messy["units_sold"].dropna().mean()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "HELD-43",
            "dataset": "synthetic_messy.csv",
            "category": "missing_values",
            "question": "How many total rows are in the dataset?",
            "type": "numeric",
            "ground_truth": int(len(df_messy)),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-44",
            "dataset": "synthetic_messy.csv",
            "category": "groupby",
            "question": "What is the total sum of units_sold in the Hardware category?",
            "type": "numeric",
            "ground_truth": round(float(df_messy[df_messy["category"] == "Hardware"]["units_sold"].dropna().sum()), 2),
            "tolerance": 0.05,
        },
        {
            "id": "HELD-45",
            "dataset": "synthetic_messy.csv",
            "category": "groupby",
            "question": "Which category has the highest number of non-null records?",
            "type": "categorical",
            "ground_truth": str(df_messy["category"].dropna().value_counts().idxmax()),
        },
        {
            "id": "HELD-46",
            "dataset": "synthetic_messy.csv",
            "category": "top_k",
            "question": "What is the maximum units_sold recorded in the dataset?",
            "type": "numeric",
            "ground_truth": round(float(df_messy["units_sold"].dropna().max()), 2),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-47",
            "dataset": "synthetic_messy.csv",
            "category": "filtering",
            "question": "How many rows have units_sold greater than 25?",
            "type": "numeric",
            "ground_truth": int((df_messy["units_sold"] > 25).sum()),
            "tolerance": 0.0,
        },
        {
            "id": "HELD-48",
            "dataset": "synthetic_messy.csv",
            "category": "percentages",
            "question": "What percentage of rows have a missing or null value in the category column?",
            "type": "numeric",
            "ground_truth": round(float(df_messy["category"].isna().mean() * 100), 2),
            "tolerance": 0.1,
        },
    ]

    dev_file = os.path.join(output_dir, "questions_dev.json")
    heldout_file = os.path.join(output_dir, "questions_heldout.json")

    with open(dev_file, "w", encoding="utf-8") as f:
        json.dump(dev_specs, f, indent=2)
    with open(heldout_file, "w", encoding="utf-8") as f:
        json.dump(heldout_specs, f, indent=2)

    # Compute SHA-256 hashes
    def get_sha256(path):
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    print(f"Computed ground truth for {len(dev_specs)} DEV and {len(heldout_specs)} HELD-OUT questions.")
    print(f"DEV questions: {dev_file} (SHA-256: {get_sha256(dev_file)})")
    print(f"HELD-OUT questions: {heldout_file} (SHA-256: {get_sha256(heldout_file)})")

if __name__ == "__main__":
    compute_ground_truth()
