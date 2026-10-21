"""
Deterministic Synthetic Dataset Generator
Generates reproducible, seeded synthetic CSVs for analytical evaluation.
No real, personal, or proprietary data is used.
"""

import os
import random
import numpy as np
import pandas as pd

RANDOM_SEED = 42

def generate_all(output_dir="data"):
    os.makedirs(output_dir, exist_ok=True)
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    # 1. Sales & Orders Dataset (1,000 rows)
    n_sales = 1000
    regions = ["North", "South", "East", "West"]
    categories = ["Electronics", "Furniture", "Office Supplies", "Clothing"]
    
    dates = pd.date_range("2023-01-01", periods=n_sales, freq="8h").strftime("%Y-%m-%d").tolist()
    sales_df = pd.DataFrame({
        "order_id": np.arange(1001, 1001 + n_sales),
        "order_date": dates,
        "region": np.random.choice(regions, size=n_sales, p=[0.30, 0.25, 0.25, 0.20]),
        "product_category": np.random.choice(categories, size=n_sales, p=[0.35, 0.25, 0.20, 0.20]),
        "sales_amount": np.round(np.random.uniform(10.0, 1500.0, size=n_sales), 2),
        "quantity": np.random.randint(1, 15, size=n_sales),
        "discount": np.round(np.random.choice([0.0, 0.05, 0.10, 0.15, 0.20], size=n_sales), 2),
    })
    sales_df["profit"] = np.round(sales_df["sales_amount"] * (1 - sales_df["discount"]) * 0.25 - np.random.uniform(0, 10, size=n_sales), 2)
    sales_path = os.path.join(output_dir, "synthetic_sales.csv")
    sales_df.to_csv(sales_path, index=False)
    print(f"Generated {sales_path}: {len(sales_df)} rows")

    # 2. HR & Employee Dataset (500 rows)
    n_hr = 500
    departments = ["Engineering", "Sales", "Marketing", "Finance", "Human Resources"]
    roles = {
        "Engineering": ["Software Engineer", "DevOps Engineer", "QA Engineer", "Engineering Manager"],
        "Sales": ["Account Executive", "Sales Representative", "Sales Lead"],
        "Marketing": ["Marketing Specialist", "Content Writer", "SEO Lead"],
        "Finance": ["Financial Analyst", "Accountant", "Finance Manager"],
        "Human Resources": ["HR Generalist", "Recruiter", "HR Director"],
    }
    dept_choices = np.random.choice(departments, size=n_hr, p=[0.40, 0.25, 0.15, 0.12, 0.08])
    role_choices = [np.random.choice(roles[d]) for d in dept_choices]
    tenure = np.random.randint(1, 15, size=n_hr)
    base_salary = {
        "Engineering": 105000,
        "Sales": 75000,
        "Marketing": 70000,
        "Finance": 85000,
        "Human Resources": 65000,
    }
    salaries = [
        int(base_salary[dept_choices[i]] + tenure[i] * 3500 + np.random.normal(0, 5000))
        for i in range(n_hr)
    ]
    ratings = np.random.choice([1, 2, 3, 4, 5], size=n_hr, p=[0.05, 0.15, 0.50, 0.20, 0.10])
    attrition = ["Yes" if (r <= 2 and t < 3) or (np.random.rand() < 0.08) else "No" for r, t in zip(ratings, tenure)]

    hr_df = pd.DataFrame({
        "employee_id": np.arange(5001, 5001 + n_hr),
        "department": dept_choices,
        "job_title": role_choices,
        "tenure_years": tenure,
        "salary": salaries,
        "performance_rating": ratings,
        "attrition": attrition,
    })
    hr_path = os.path.join(output_dir, "synthetic_hr.csv")
    hr_df.to_csv(hr_path, index=False)
    print(f"Generated {hr_path}: {len(hr_df)} rows")

    # 3. Sensor & Time-Series Dataset (2,000 rows)
    n_sensor = 2000
    sensor_ids = ["SENSOR-A", "SENSOR-B", "SENSOR-C", "SENSOR-D"]
    timestamps = pd.date_range("2024-01-01 00:00:00", periods=n_sensor, freq="15min")
    temp_base = {"SENSOR-A": 65.0, "SENSOR-B": 72.0, "SENSOR-C": 58.0, "SENSOR-D": 80.0}
    
    s_assign = np.random.choice(sensor_ids, size=n_sensor)
    temperatures = np.round([temp_base[s] + np.random.normal(0, 4.5) for s in s_assign], 2)
    pressure = np.round(101.3 + np.random.normal(0, 2.0, size=n_sensor), 2)
    vibration = np.round(np.abs(np.random.normal(0.05, 0.02, size=n_sensor)), 4)
    status = []
    for t in temperatures:
        if t > 85.0:
            status.append("Critical")
        elif t > 76.0:
            status.append("Warning")
        else:
            status.append("Normal")

    sensor_df = pd.DataFrame({
        "timestamp": timestamps.strftime("%Y-%m-%d %H:%M:%S"),
        "sensor_id": s_assign,
        "temperature_c": temperatures,
        "pressure_kpa": pressure,
        "vibration_g": vibration,
        "status": status,
    })
    sensor_path = os.path.join(output_dir, "synthetic_sensor.csv")
    sensor_df.to_csv(sensor_path, index=False)
    print(f"Generated {sensor_path}: {len(sensor_df)} rows")

    # 4. Messy Real-World Style Dataset (300 rows)
    n_messy = 300
    dirty_prices = []
    dirty_names = []
    dirty_categories = []
    dirty_units = []
    
    for i in range(n_messy):
        # dirty price: e.g. "$ 45.20", "120.0", " $15.5 ", "missing"
        if i % 25 == 0:
            dirty_prices.append(None)
        elif i % 17 == 0:
            dirty_prices.append("N/A")
        elif i % 7 == 0:
            dirty_prices.append(f"$ {round(random.uniform(5, 200), 2)}")
        else:
            dirty_prices.append(str(round(random.uniform(5, 200), 2)))

        # dirty name with spaces
        name = f" Item_{i+1} " if i % 3 == 0 else f"Item_{i+1}"
        dirty_names.append(name)

        # category with NaNs
        if i % 15 == 0:
            dirty_categories.append(None)
        else:
            dirty_categories.append(random.choice(["Hardware", "Software", "Cloud", "Support"]))

        # units with NaNs
        if i % 20 == 0:
            dirty_units.append(np.nan)
        else:
            dirty_units.append(float(random.randint(1, 50)))

    messy_df = pd.DataFrame({
        "item_id": np.arange(101, 101 + n_messy),
        "item_name": dirty_names,
        "raw_price": dirty_prices,
        "units_sold": dirty_units,
        "category": dirty_categories,
    })
    messy_path = os.path.join(output_dir, "synthetic_messy.csv")
    messy_df.to_csv(messy_path, index=False)
    print(f"Generated {messy_path}: {len(messy_df)} rows")

if __name__ == "__main__":
    generate_all()
