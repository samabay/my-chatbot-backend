import csv
import os

def prepare_data():
    # Use relative paths for portability
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = r'c:\Users\User\OneDrive\Desktop\project' # Source CSVs remain on Desktop
    target_path = script_dir # Output data.csv in the same folder as this script
    
    # 1. Load Stations
    stations = {}
    with open(os.path.join(base_path, 'Station.csv'), 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            stations[row['StationID'].strip()] = row['StationName'].strip()

    # 2. Load Trains
    trains = {}
    with open(os.path.join(base_path, 'Train.csv'), 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trains[row['Train_ID'].strip()] = row

    # 3. Load Trip Timing (tripdep.csv)
    times = {}
    with open(os.path.join(base_path, 'tripdep.csv'), 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trip_id = row['Trip_ID'].strip()
            if trip_id not in times:
                times[trip_id] = {}
            times[trip_id][row['StationID'].strip()] = {
                'Arrival': row['ArrivalTime'],
                'Departure': row['DepartureTime']
            }

    # 4. Load Intermediate Stops (TripStops.csv)
    stops = {}
    with open(os.path.join(base_path, 'TripStops.csv'), 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trip_id = row['Trip_ID'].strip()
            if trip_id not in stops:
                stops[trip_id] = []
            station_name = stations.get(row['StationID'].strip(), f"Station {row['StationID']}")
            stops[trip_id].append({
                'Order': int(row['Stop_Order']),
                'Station': station_name,
                'Arrival': row['Arrival_Time'],
                'Departure': row['Departure_Time']
            })

    # 5. Load Carriage Pricing (CarriageType.csv)
    carriage_types = {}
    with open(os.path.join(base_path, 'CarriageType.csv'), 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            carriage_types[row['TypeID'].strip()] = {
                'Price': row['Seat_Price'],
                'Seats': row['NumberOfSeats']
            }

    # 6. Load Carriages (Carriage.csv)
    train_carriages = {}
    with open(os.path.join(base_path, 'Carriage.csv'), 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            t_id = row['Train_ID'].strip()
            if t_id not in train_carriages:
                train_carriages[t_id] = []
            
            c_type_info = carriage_types.get(row['TypeID'].strip(), {'Price': '100', 'Seats': '0'})
            train_carriages[t_id].append({
                'Class': row['Class_Type'],
                'Available': row['Available_Seats'],
                'TotalSeats': c_type_info['Seats'],
                'Price': c_type_info['Price']
            })

    # 7. Consolidated Data
    consolidated_data = []
    trips_with_stops = 0

    with open(os.path.join(base_path, 'trip.csv'), 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trip_id = row['Trip_ID'].strip()
            train_id = row['Train_ID'].strip()
            
            train_info = trains.get(train_id, {'Train_Name': 'Unknown', 'Train_Type': 'Unknown'})
            trip_times = times.get(trip_id, {})
            trip_stops = sorted(stops.get(trip_id, []), key=lambda x: x['Order'])
            if trip_stops:
                trips_with_stops += 1
                
            carriages = train_carriages.get(train_id, [])

            # Formatting Stops
            stops_str = " -> ".join([f"{s['Station']} ({s['Arrival']})" for s in trip_stops])
            
            # Formatting Carriages and finding a base price
            c_details = []
            base_price = "100"
            for c in carriages:
                c_details.append(f"{c['Class']}: {c['Price']} EGP ({c['Available']}/{c['TotalSeats']} seats)")
                if 'first' in c['Class'].lower() or 'ac' in c['Class'].lower():
                    base_price = c['Price']
            
            carriages_str = " | ".join(c_details)

            # Determine times
            from_time = "N/A"
            to_time = "N/A"
            if trip_times:
                # Find any departure for the 'From' station or just pick first
                times_list = list(trip_times.values())
                from_time = times_list[0]['Departure']
                to_time = times_list[-1]['Arrival']

            consolidated_data.append({
                'Trip_ID': trip_id,
                'Train_Name': train_info.get('Train_Name', 'Unknown'),
                'Train_Type': train_info.get('Train_Type', 'Unknown'),
                'From': row['From'],
                'To': row['To'],
                'Date': row['Date'],
                'DepartureTime': from_time,
                'ArrivalTime': to_time,
                'Seat_Price': base_price,
                'IntermediateStops': stops_str,
                'CarriageDetails': carriages_str
            })

    # Write to data.csv
    headers = ['Trip_ID', 'Train_Name', 'Train_Type', 'From', 'To', 'Date', 'DepartureTime', 'ArrivalTime', 'Seat_Price', 'IntermediateStops', 'CarriageDetails']
    with open(os.path.join(target_path, 'data.csv'), 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(consolidated_data)
    print(f"data.csv created successfully with {len(consolidated_data)} records.")
    print(f"Trips with intermediate stops found: {trips_with_stops}")

if __name__ == "__main__":
    prepare_data()
