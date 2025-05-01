from flask import Flask, render_template, request, jsonify
from foot_traffic_analysis import extract_osm_foot_traffic_indicators
import json
from datetime import datetime
import os
import requests
import traceback

app = Flask(__name__)

# Create analyses directory if it doesn't exist
if not os.path.exists('analyses'):
    os.makedirs('analyses')

def get_location_name(lat, lon):
    try:
        response = requests.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json")
        data = response.json()
        road = data.get('address', {}).get('road', '')
        suburb = data.get('address', {}).get('suburb', '')
        city = data.get('address', {}).get('city', '')
        return road if road else f"{suburb}, {city}"
    except Exception as e:
        print(f"Error getting location name: {str(e)}")
        return "unknown_location"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.json
        lat = float(data['lat'])
        lon = float(data['lon'])
        radius = int(data.get('radius', 300))  # Default to 300m if not specified
        
        print(f"\nAnalyzing location: lat={lat}, lon={lon}, radius={radius}m")
        
        # Get analysis results
        results, analysis = extract_osm_foot_traffic_indicators(lat, lon, radius_m=radius)
        analysis_data = results.to_dict('records')[0]
        
        # Get location name for the file
        location_name = get_location_name(lat, lon)
        safe_location_name = "".join(x for x in location_name if x.isalnum() or x in [' ', '_']).strip()
        
        # Create filename with timestamp and location
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"analyses/analysis_{timestamp}_{safe_location_name}_{radius}m.json"
        
        # Save analysis to file
        with open(filename, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'location_name': location_name,
                'latitude': lat,
                'longitude': lon,
                'radius_meters': radius,
                'analysis': analysis
            }, f, indent=2)
            
        print(f"Analysis saved to: {filename}")
        
        # Add filename and radius to response
        analysis_data.update(analysis)  # Include detailed place information
        analysis_data['saved_file'] = filename
        analysis_data['radius_meters'] = radius
        
        return jsonify(analysis_data)
    except Exception as e:
        error_msg = f"Error during analysis: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        return jsonify({'error': error_msg}), 400

if __name__ == '__main__':
    app.run(debug=True) 