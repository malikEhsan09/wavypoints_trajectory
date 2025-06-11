from flask import Flask, request, jsonify, render_template
import serial
import json
import heapq
import time

app = Flask(__name__)

# Serial configuration (adjust port and baudrate)
SERIAL_PORT = 'COM4'  # Change this to your ground ESP32's port
BAUDRATE = 115200

# Map configuration
START_LOCATION = (33.6844, 73.0479, 100)  # Default start location with altitude
ZOOM_START = 14

# Waypoints list
waypoints = []

# Initialize serial connection
ser = None
def init_serial():
    global ser
    try:
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
        print(f"Successfully connected to {SERIAL_PORT}")
        return True
    except serial.SerialException as e:
        print(f"Failed to connect to {SERIAL_PORT}: {e}")
        return False

# Try to initialize serial connection
init_serial()

@app.route('/')
def map_view():
    return render_template('index.html')  # Renders the external HTML file

@app.route('/send_waypoints', methods=['POST'])
def receive_waypoints():
    global waypoints
    data = request.get_json()
    if not data or 'waypoints' not in data:
        return jsonify({'error': 'Invalid data format, expected waypoints list'}), 400
    
    try:
        waypoints = []
        for wp in data['waypoints']:
            lat = wp.get('lat')
            lng = wp.get('lng')
            alt = wp.get('altitude', 50)  # Default altitude to 100m if not provided
            
            if lat is None or lng is None:
                return jsonify({'error': 'Invalid waypoint format, missing lat/lng'}), 400
            
            waypoints.append((lat, lng, alt))
    except Exception as e:
        return jsonify({'error': f'Error processing waypoints: {str(e)}'}), 400
    
    if not waypoints:
        return jsonify({'error': 'No valid waypoints received'}), 400
    
    # Apply A* Pathfinding including altitude
    optimized_path = a_star_pathfinding(START_LOCATION, waypoints)
    
    # Send optimized waypoints to ESP32
    send_waypoints_to_esp32(optimized_path)
    
    return jsonify({'message': 'Waypoints sent successfully!', 'waypoints': optimized_path})

# A* Pathfinding Algorithm

def a_star_pathfinding(start, waypoints):
    def heuristic(a, b):
        return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5

    open_list = [(0, start)]
    heapq.heapify(open_list)
    came_from = {}
    g_score = {start: 0}

    optimized_path = []

    while open_list:
        _, current = heapq.heappop(open_list)

        if current in waypoints:
            optimized_path.append(current)
            waypoints.remove(current)

        for neighbor in waypoints:
            temp_g_score = g_score[current] + heuristic(current, neighbor)
            if neighbor not in g_score or temp_g_score < g_score[neighbor]:
                g_score[neighbor] = temp_g_score
                priority = temp_g_score + heuristic(neighbor, waypoints[0])
                heapq.heappush(open_list, (priority, neighbor))
                came_from[neighbor] = current

    return optimized_path

# Function to send waypoints to ground ESP32

def send_waypoints_to_esp32(waypoints):
    global ser
    if ser is None:
        print("Serial connection not available. Attempting to reconnect...")
        if not init_serial():
            print("Failed to establish serial connection")
            return False
    
    try:
        data = json.dumps({'waypoints': waypoints})
        ser.write(data.encode('utf-8'))
        print(f"Waypoints sent: {data}")
        return True
    except serial.SerialException as e:
        print(f"Serial error: {e}")
        ser = None  # Reset serial connection
        return False

if __name__ == '__main__':
    app.run(debug=False)
