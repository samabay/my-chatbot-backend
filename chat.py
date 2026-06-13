from flask import Flask, request, jsonify
from flask_cors import CORS
from typing import Any
import random
import torch
import json
import csv
import os
import re
from datetime import datetime, timedelta
import pickle
import pandas as pd
from model import NeuralNet
from nltk_utils import bag_of_words, tokenize, correct_spelling

app = Flask(__name__)
CORS(app)

# Get the directory where chat.py is located
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def get_path(filename):
    return os.path.join(BASE_DIR, filename)

# Setup device
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Load model data
FILE = get_path("data.pth")
all_words = []
tags = []
model = None

if os.path.exists(FILE):
    data = torch.load(FILE)
    input_size = data["input_size"]
    hidden_size = data["hidden_size"]
    output_size = data["output_size"]
    all_words = data["all_words"]
    tags = data["tags"]
    model_state = data["model_state"]
    model = NeuralNet(input_size, hidden_size, output_size).to(device)
    model.load_state_dict(model_state)
    model.eval()
else:
    print("Warning: data.pth not found. Please run train.py first.")

# Load intents.json
intents = {"intents": []}
INTENTS_PATH = get_path('intents.json')
if os.path.exists(INTENTS_PATH):
    with open(INTENTS_PATH, 'r', encoding='utf-8') as json_data:
        intents = json.load(json_data)

DATA_CSV = get_path("data.csv")

def load_train_data():
    data = []
    if os.path.exists(DATA_CSV):
        with open(DATA_CSV, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    return data

TRAIN_DATA: list[dict] = load_train_data()

def calculate_time_diff(start, end):
    try:
        fmt = '%H:%M:%S'
        tdelta = datetime.strptime(end, fmt) - datetime.strptime(start, fmt)
        return str(tdelta)
    except:
        return "Unknown"

def extract_date(message):
    message = message.lower()
    today = datetime.now()
    
    # 1. Check relative keywords
    if "today" in message or "اليوم" in message:
        return today.strftime('%Y-%m-%d')
    if "tomorrow" in message or "غداً" in message or "غدا" in message:
        return (today + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # 2. Check for date patterns (YYYY-MM-DD)
    match_iso = re.search(r'\d{4}-\d{2}-\d{2}', message)
    if match_iso:
        return match_iso.group()
        
    # 3. Check for DD-MM-YYYY or DD/MM/YYYY
    match_eu = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', message)
    if match_eu:
        day, month, year = match_eu.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    return None

@app.route('/chat', methods=['POST'])
def chat():
    req_data = request.get_json()
    if not req_data or 'message' not in req_data:
        return jsonify({"error": "No message provided."}), 400

    sentence = req_data['message']
    user_email = req_data.get('email', 'unknown@example.com')
    
    if model is None:
        return jsonify({"response": "The main NLP model is not loaded. Please contact support."}), 500

    
    tokens = tokenize(sentence)
    tokens = correct_spelling(tokens) # spell correction
    X = bag_of_words(tokens, all_words)
    X = X.reshape(1, X.shape[0])
    X = torch.from_numpy(X).float().to(device)

    output = model(X)
    _, predicted = torch.max(output, dim=1)
    probs = torch.softmax(output, dim=1)
    prob = probs[0][predicted.item()]
    
    tag = tags[predicted.item()]

    # Check if confidence is high enough and it's not a 'noanswer' tag
    if prob.item() > 0.75 and tag != "noanswer":
        response = "I'm sorry, I don't understand that."
        for intent in intents['intents']:
            if intent['tag'] == tag:
                response = random.choice(intent['responses'])
                break
    else:
        # User requested fallback message
        return jsonify({"response": "It is not within my role. I am here to assist with train-related queries. Please ask me about train schedules, fares, routes or related information."})

    # Dynamic Logic based on Tags
    if tag == "available_trains":
        target_date = extract_date(sentence)
        # Check if the user is asking about specific trips or timeframes
        is_trip_query = any(kw in sentence.lower() for kw in ["trip", "today", "tomorrow", "غداً", "اليوم", "رحلة", "رحلات"])
        
        if target_date:
            filtered_trips = [t for t in TRAIN_DATA if t.get('Date') == target_date]
            msg_prefix = f"\nHere are the available trips on {target_date}:\n"
            no_trips_msg = f"\nNo trips found for {target_date}."
        else:
            filtered_trips = TRAIN_DATA
            msg_prefix = "\nHere are the types of trains available in our system:\n"
            no_trips_msg = "\nNo train or trip information found."

        # Show detailed trip list if 'trip' or a date was mentioned
        if is_trip_query or target_date:
            if filtered_trips:
                # Limit display to avoid overwhelming the user
                display_limit = 10
                trips_to_show = filtered_trips[:display_limit]
                
                trip_list = []
                for t in trips_to_show:
                    trip_list.append(
                        f"• Trip {t.get('Trip_ID')}, From: {t.get('From')}, To: {t.get('To')}, Departure Time: {t.get('DepartureTime')}"
                    )
                
                response = "The available trips are:\n" + "\n".join(trip_list)
            else:

                response = no_trips_msg
        else:
            # Show train names list
            unique_trains = sorted(list(set(t.get('Train_Name', 'Unknown') for t in filtered_trips)))
            if unique_trains:
                trains_display = "\n".join([f"- {name}" for name in unique_trains])
                response += msg_prefix + trains_display
            else:
                response += no_trips_msg


    elif tag == "seat_prices":
        class_prices = {}
        for t in TRAIN_DATA:
            t_details = str(t.get('CarriageDetails', '')).strip()
            # Extract class name and price using regex
            # Format: "first class: 250 EGP (145/145 seats)"
            matches = re.finditer(r'([\w\s]+):\s*(\d+)\s*EGP', t_details)
            for m in matches:
                cls_name = m.group(1).strip()
                price = int(m.group(2))
                if cls_name not in class_prices:
                    class_prices[cls_name] = []
                class_prices[cls_name].append(price)
        
        if class_prices:
            range_lines = []
            # Sort class names for consistent output
            for cls in sorted(class_prices.keys()):
                prices = class_prices[cls]
                min_p = min(prices)
                max_p = max(prices)
                if min_p == max_p:
                    range_lines.append(f"- {cls}: {min_p} EGP")
                else:
                    range_lines.append(f"- {cls}: {min_p}-{max_p} EGP")
            
            response += "\nCurrent ticket price ranges:\n" + "\n".join(range_lines)
        else:
            response += "\nNo seat price information available."

    elif tag == "schedule_info":
        words = sentence.split()
        trip_id = next((w for w in words if w.isdigit()), None)
        if trip_id:
            trip = next((t for t in TRAIN_DATA if t['Trip_ID'] == trip_id), None)
            if trip:
                response = f"Trip {trip_id} Route Details:\n"
                response += f"- Starts: {trip['From']} at {trip['DepartureTime']}\n"
                if trip['IntermediateStops']:
                    response += f"- Intermediate Stops (Estimated Arrival): {trip['IntermediateStops']}\n"
                response += f"- Estimated Arrival at {trip['To']}: {trip['ArrivalTime']}"
            else:
                response = f"Sorry, I couldn't find details for Trip {trip_id}."

    elif tag == "travel_time":
        words = sentence.split()
        trip_id = next((w for w in words if w.isdigit()), None)
        if trip_id:
            trip = next((t for t in TRAIN_DATA if t['Trip_ID'] == trip_id), None)
            if trip:
                duration = calculate_time_diff(trip['DepartureTime'], trip['ArrivalTime'])
                response = f"Trip {trip_id} Estimated Arrival:\n"
                response += f"- Travel Duration (Time it takes): {duration}\n"
                response += f"- Arrives at {trip['To']} (Time it will arrive): {trip['ArrivalTime']}"

    return jsonify({"response": response})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5004, debug=True)
