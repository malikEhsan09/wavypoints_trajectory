from flask import Flask, request, jsonify, render_template
import requests
import time

app = Flask(__name__)

# Map configuration
START_LOCATION = (33.6844, 73.0479, 100)  # Default start location with altitude in meters
ZOOM_START = 14

# Waypoints list
waypoints = []

def get_elevation(lat, lng):
    """Get elevation data from OpenTopography API"""
    try:
        url = f"https://portal.opentopography.org/API/astergdem?demtype=ASTERGDEMV3&south={lat-0.001}&north={lat+0.001}&west={lng-0.001}&east={lng+0.001}&outputFormat=AAIGrid"
        response = requests.get(url)
        if response.status_code == 200:
            # Parse the elevation data from the response
            data = response.text.split('\n')
            if len(data) > 6:  # Check if we have elevation data
                elevation = float(data[6].strip())
                # Add a safety margin of 5 meters to the elevation
                return min(elevation + 5, 100)  # Max 100m height
        return 10  # Default to 10m if elevation data not available
    except Exception as e:
        print(f"Error getting elevation: {e}")
        return 10  # Default to 10m if there's an error

@app.route('/')
def map_view():
    return render_template('index.html')

@app.route('/add_manual_point', methods=['POST'])
def add_manual_point():
    data = request.get_json()
    if not data or 'lat' not in data or 'lng' not in data:
        return jsonify({'error': 'Invalid data format, expected lat and lng'}), 400
    
    try:
        lat = float(data['lat'])
        lng = float(data['lng'])
        
        if not (-90 <= lat <= 90 and -180 <= lng <= 180):
            return jsonify({'error': 'Invalid coordinates'}), 400
        
        # Get elevation for the coordinates
        altitude = get_elevation(lat, lng)
            
        waypoints.append((lat, lng, altitude))
        return jsonify({
            'message': 'Point added successfully',
            'waypoints': waypoints,
            'altitude': altitude
        })
    except ValueError:
        return jsonify({'error': 'Invalid coordinate values'}), 400

if __name__ == '__main__':
    app.run(debug=False)
