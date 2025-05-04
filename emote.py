import sqlite3
import csv
import os

# Set up paths
db_path = os.path.join("data", "emotions.db")
export_path = os.path.join("data", "emotions_export.csv")

def db_to_csv():
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Read all the data
    cursor.execute("SELECT * FROM emotions")
    rows = cursor.fetchall()

    # Get column names
    column_names = [description[0] for description in cursor.description]

    # Write to CSV
    with open(export_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(column_names)  # Header
        writer.writerows(rows)

    print(f"✓ Exported {len(rows)} rows to {export_path}!")

def csv_to_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create the emotions table with new columns
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS emotions (
        timestamp TEXT,
        happy REAL, sad REAL, mad REAL,
        silly REAL, devious REAL, sanity REAL,
        energy REAL, hunger REAL
    )
    ''')

    # Open the CSV file
    csv_file = export_path
    with open(csv_file, "r", encoding="utf-8") as f:
        csv_reader = csv.reader(f)
        header = next(csv_reader)  # Skip the header row

        # Overwrite the existing data
        cursor.execute("DELETE FROM emotions")

        # Insert each row with 9 values
        for row in csv_reader:
            if len(row) == 9:
                cursor.execute('''
                    INSERT INTO emotions (
                        timestamp, happy, sad, mad,
                        silly, devious, sanity,
                        energy, hunger
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', row)
            else:
                print(f"(⚠️) Skipping malformed row: {row}")

    # Commit and close
    conn.commit()
    conn.close()

    print("✓ CSV data imported & database overwritten with energy + hunger included!")

# User input to select action
def main():
    action = input("Choose an action: \n1. Export .db to .csv \n2. Import .csv to .db (overwrite data)\nYour choice (1/2): ").strip()

    if action == "1":
        db_to_csv()
    elif action == "2":
        csv_to_db()
    else:
        print("⚠️ Invalid choice. Please select 1 or 2.")

if __name__ == "__main__":
    main()
