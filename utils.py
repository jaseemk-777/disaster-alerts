# utils.py - Flexible Disaster Folder Creation (Updated)
import os
import argparse
from datetime import datetime
import calendar

def create_folders(hazard_name="Monsoon"):
    """
    Create folder structure for disaster news data storage.
    
    Args:
        hazard_name: Name of the hazard/disaster (default: "Monsoon" for backward compatibility)
    """
    base_path = 'data'
    
    # Indian states
    states = [
        "andhra-pradesh", "arunachal-pradesh", "assam", "bihar", 
        "chhattisgarh", "goa", "gujarat", "haryana", "himachal-pradesh", 
        "jharkhand", "karnataka", "kerala", "madhya-pradesh", "maharashtra", 
        "manipur", "meghalaya", "mizoram", "nagaland", "odisha", "punjab", 
        "rajasthan", "sikkim", "tamil-nadu", "telangana", "tripura", 
        "uttar-pradesh", "uttarakhand", "west-bengal"
    ]
    
    # Union territories
    union_territories = [
        "andaman-and-nicobar-islands", "chandigarh", 
        "dadra-and-nagar-haveli-and-daman-and-diu", "lakshadweep", "delhi", 
        "puducherry", "jammu-and-kashmir", "ladakh"
    ]
    
    # Use specified hazard name or default to Monsoon
    climate_events = [hazard_name]
    year = datetime.now().year
    
    print(f"📁 Creating folder structure for {hazard_name} in {year}...")
    
    # Create subfolders for each state/UT, hazard event, year, month, day
    folder_count = 0
    
    for state in states:
        for event in climate_events:
            for month in range(1, 13):
                days_in_month = calendar.monthrange(year, month)[1]
                for day in range(1, days_in_month + 1):
                    folder_path = f"{base_path}/states/{state}/{event}/{year}/{month:02d}/{day:02d}"
                    os.makedirs(folder_path, exist_ok=True)
                    folder_count += 1
    
    for ut in union_territories:
        for event in climate_events:
            for month in range(1, 13):
                days_in_month = calendar.monthrange(year, month)[1]
                for day in range(1, days_in_month + 1):
                    folder_path = f"{base_path}/union-territories/{ut}/{event}/{year}/{month:02d}/{day:02d}"
                    os.makedirs(folder_path, exist_ok=True)
                    folder_count += 1
    
    # Create national folder structure
    for event in climate_events:
        for month in range(1, 13):
            days_in_month = calendar.monthrange(year, month)[1]
            for day in range(1, days_in_month + 1):
                folder_path = f"{base_path}/national/all/{event}/{year}/{month:02d}/{day:02d}"
                os.makedirs(folder_path, exist_ok=True)
                folder_count += 1
    
    # Create JSON output folders
    json_output_dirs = ["JSON Output", "JSON Output Spare"]
    for json_dir in json_output_dirs:
        os.makedirs(json_dir, exist_ok=True)
    
    print(f"✅ Created {folder_count} {hazard_name} data folders")
    print(f"✅ Created JSON output directories")
    print(f"📊 Structure: {len(states)} states + {len(union_territories)} UTs + national")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Create folder structure for disaster news storage')
    parser.add_argument('--hazard-name', type=str, default='Monsoon',
                      help='Name of the hazard/disaster (default: Monsoon)')
    
    args = parser.parse_args()
    
    create_folders(hazard_name=args.hazard_name)
