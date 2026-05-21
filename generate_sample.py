import csv
import random

# Define possible values
departments = ['Engineering', 'Sales', 'Marketing', 'HR', 'Finance', 'Operations']
cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix', 'Philadelphia', 'San Antonio', 'San Diego', 'Dallas', 'San Jose']
genders = ['Male', 'Female', 'Other']
first_names = ['John', 'Jane', 'Alex', 'Emily', 'Michael', 'Sarah', 'David', 'Laura', 'Chris', 'Anna']
last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']

# Open CSV file
with open('data/sample.csv', 'w', newline='') as csvfile:
    writer = csv.writer(csvfile)
    # Write header
    writer.writerow(['id', 'name', 'age', 'gender', 'department', 'salary', 'city'])
    
    # Generate 1000 records
    for i in range(1, 1001):
        id = i
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        name = f"{first_name} {last_name}"
        age = random.randint(20, 65)
        gender = random.choice(genders)
        department = random.choice(departments)
        salary = random.randint(30000, 150000)
        city = random.choice(cities)
        
        writer.writerow([id, name, age, gender, department, salary, city])

print("sample.csv generated with 1000 records.")