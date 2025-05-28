from flask import Flask, render_template, request, jsonify, session, send_file
from flask_cors import CORS
from foot_traffic_analysis import extract_osm_foot_traffic_indicators
from pdf_report_generator import LocationViabilityReportGenerator
import json
from datetime import datetime
import os
import requests
import traceback
from functools import wraps
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('app.log')  # File output
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.secret_key = os.urandom(24)  # Required for session

logger.info("Flask application starting up...")

# Simple in-memory storage for demo (replace with a database in production)
last_searches = {}

def get_client_ip():
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

# Create directories if they don't exist
for directory in ['analyses_new', 'reports']:
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Created {directory} directory")

def get_location_name(lat, lon):
    try:
        logger.info(f"Fetching location name for coordinates: {lat}, {lon}")
        response = requests.get(f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json")
        data = response.json()
        road = data.get('address', {}).get('road', '')
        suburb = data.get('address', {}).get('suburb', '')
        city = data.get('address', {}).get('city', '')
        location_name = road if road else f"{suburb}, {city}"
        logger.info(f"Location name resolved: {location_name}")
        return location_name
    except Exception as e:
        logger.error(f"Error getting location name: {str(e)}")
        return "unknown_location"

@app.route('/')
def index():
    logger.info(f"Index page requested from {get_client_ip()}")
    return render_template('index.html')

@app.route('/api/last-search', methods=['GET'])
def get_last_search():
    try:
        client_ip = get_client_ip()
        logger.info(f"Last search requested from {client_ip}")
        last_search = last_searches.get(client_ip)
        if last_search:
            logger.info(f"Returning last search for {client_ip}: {last_search}")
            return jsonify({
                'success': True,
                'lat': last_search['lat'],
                'lon': last_search['lon'],
                'radius': last_search['radius']
            })
        logger.info(f"No previous search found for {client_ip}")
        return jsonify({'success': False, 'message': 'No previous search found'}), 404
    except Exception as e:
        logger.error(f"Error in get_last_search: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download-report/<filename>')
def download_report(filename):
    """Download PDF report"""
    try:
        report_path = os.path.join('reports', filename)
        if os.path.exists(report_path):
            logger.info(f"Serving report download: {filename}")
            return send_file(report_path, as_attachment=True, download_name=filename)
        else:
            logger.error(f"Report file not found: {filename}")
            return jsonify({'error': 'Report not found'}), 404
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        client_ip = get_client_ip()
        logger.info(f"=== ANALYSIS REQUEST START === from {client_ip}")
        
        # Parse request data
        data = request.json
        logger.info(f"Request data: {data}")
        
        lat = float(data['lat'])
        lon = float(data['lon'])
        radius = int(data.get('radius', 300))  # Default to 300m if not specified
        
        logger.info(f"Parsed coordinates: lat={lat}, lon={lon}, radius={radius}m")
        
        # Store the search in session
        last_searches[client_ip] = {
            'lat': lat,
            'lon': lon,
            'radius': radius,
            'timestamp': datetime.now().isoformat()
        }
        logger.info(f"Stored search in session for {client_ip}")
        
        # Get analysis results
        logger.info("Starting OSM data extraction...")
        results, analysis = extract_osm_foot_traffic_indicators(lat, lon, radius_m=radius)
        logger.info("OSM data extraction completed")
        
        analysis_data = results.to_dict('records')[0]
        logger.info(f"Analysis data keys: {list(analysis_data.keys())}")
        
        # Get location name for the file
        location_name = get_location_name(lat, lon)
        safe_location_name = "".join(x for x in location_name if x.isalnum() or x in [' ', '_']).strip()
        
        # Create filename with timestamp and location
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"analysis_{timestamp}_{safe_location_name}_{radius}m.json"
        json_filepath = f"analyses_new/{filename}"
        
        # Save analysis to file
        logger.info(f"Saving analysis to file: {json_filepath}")
        with open(json_filepath, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'location_name': location_name,
                'latitude': lat,
                'longitude': lon,
                'radius_meters': radius,
                'analysis': analysis
            }, f, indent=2)
            
        logger.info(f"Analysis saved successfully to: {json_filepath}")
        
        # Generate PDF Report
        logger.info("Generating PDF viability report...")
        try:
            report_generator = LocationViabilityReportGenerator()
            pdf_filename = f"viability_report_{timestamp}_{safe_location_name}_{radius}m.pdf"
            pdf_filepath = f"reports/{pdf_filename}"
            
            # Generate the report and get summary data
            report_data = report_generator.generate_report(
                analysis, location_name, lat, lon, radius, pdf_filepath
            )
            
            logger.info(f"PDF report generated successfully: {pdf_filepath}")
            
            # Add report data to response
            analysis_data.update(analysis)  # Include detailed place information
            analysis_data['saved_file'] = json_filepath
            analysis_data['radius_meters'] = radius
            analysis_data['pdf_report'] = pdf_filename
            analysis_data['viability_score'] = report_data['viability_percentage']
            analysis_data['viability_rating'] = report_data['rating']
            analysis_data['viability_summary'] = report_data['summary']
            
        except Exception as e:
            logger.error(f"Error generating PDF report: {str(e)}")
            # Continue without PDF if generation fails
            analysis_data.update(analysis)
            analysis_data['saved_file'] = json_filepath
            analysis_data['radius_meters'] = radius
            analysis_data['pdf_report'] = None
            analysis_data['viability_score'] = None
            analysis_data['viability_rating'] = None
            analysis_data['viability_summary'] = "PDF report generation failed"
        
        # Ensure consistent property names with frontend
        response_data = analysis_data.copy()
        response_data['lat'] = lat
        response_data['lon'] = lon
        
        logger.info(f"Returning response with keys: {list(response_data.keys())}")
        logger.info("=== ANALYSIS REQUEST SUCCESS ===")
        
        return jsonify(response_data)
    except Exception as e:
        error_msg = f"Error during analysis: {str(e)}"
        logger.error(f"=== ANALYSIS REQUEST FAILED ===")
        logger.error(f"{error_msg}\n{traceback.format_exc()}")
        return jsonify({'error': error_msg}), 400

if __name__ == '__main__':
    logger.info("Starting Flask development server on port 10101...")
    app.run(debug=True, host='0.0.0.0', port=10101) 