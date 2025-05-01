from flask import Flask, render_template, request, jsonify
from foot_traffic_analysis import extract_osm_foot_traffic_indicators

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json
    lat = float(data['lat'])
    lon = float(data['lon'])
    
    try:
        results = extract_osm_foot_traffic_indicators(lat, lon)
        return jsonify(results.to_dict('records')[0])
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True) 