# Foot Traffic Analysis Tool

A web-based application for analyzing foot traffic indicators in specific locations using OpenStreetMap data. The tool provides comprehensive analysis of various factors that contribute to pedestrian activity and generates detailed viability reports.

## Features

- **Interactive Map Interface**: Click on any location or search for addresses
- **Comprehensive Analysis**: Analyzes 10+ foot traffic indicators including:
  - Restaurants and cafes
  - Retail shops
  - Schools and universities
  - Healthcare facilities
  - Public transportation
  - Markets and commercial areas
  - Tourist attractions
  - Places of worship
  - Pedestrian infrastructure
  - Road intersections

- **Viability Scoring**: Intelligent scoring system that ranks locations from "Excellent" to "Poor"
- **PDF Reports**: Automatically generated detailed reports with:
  - Executive summary
  - Viability score and rating
  - Indicators ranked by importance
  - Detailed analysis and recommendations
  - Business suitability assessment

- **Network Resilience**: Multiple API endpoints with automatic failover
- **Comprehensive Logging**: Detailed logging for troubleshooting
- **Data Persistence**: Analysis results saved as JSON files

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd foot-traffic-analysis
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python3 app.py
   ```

4. **Access the application**:
   Open your browser and navigate to `http://localhost:10101`

## Usage

1. **Select a Location**:
   - Click anywhere on the map to place a marker, OR
   - Use the search box to find a specific address

2. **Adjust Analysis Radius** (optional):
   - Default: 200 meters
   - Range: 100-2000 meters

3. **Start Analysis**:
   - Click on the pin
   - Confirm when prompted
   - Wait for analysis to complete (1-5 minutes)

4. **View Results**:
   - **Viability Summary**: Overall score and rating
   - **Detailed Indicators**: Table with all metrics
   - **PDF Report**: Download comprehensive analysis report
   - **Raw Data**: JSON file with complete analysis

## Understanding the Results

### Viability Ratings
- **Excellent (80%+)**: Ideal for foot traffic-dependent businesses
- **Good (65-79%)**: Suitable for most commercial activities
- **Moderate (50-64%)**: Requires careful business planning
- **Poor (<50%)**: Limited foot traffic potential

### Key Indicators
The analysis evaluates locations based on weighted criteria:
- **Shops** (20% weight): Primary foot traffic generators
- **Restaurants/Cafes** (15% weight): Consistent visitor attraction
- **Intersections** (15% weight): Pedestrian movement indicators
- **Public Transport** (12% weight): Commuter foot traffic
- **Schools** (10% weight): Regular crowd generation
- **Healthcare** (8% weight): Steady visitor flow
- **Pedestrian Infrastructure** (8% weight): Walkability indicators
- **Markets** (7% weight): Commercial activity concentration
- **Tourist Sites** (3% weight): Occasional visitor attraction
- **Places of Worship** (2% weight): Periodic gatherings

## File Structure

```
foot-traffic-analysis/
├── app.py                          # Flask web application
├── foot_traffic_analysis.py        # OSM data analysis engine
├── pdf_report_generator.py         # PDF report generation
├── templates/
│   └── index.html                  # Web interface
├── analyses_new/                   # JSON analysis results
├── reports/                        # Generated PDF reports
├── requirements.txt                # Python dependencies
├── README.md                       # This file
└── changelog.md                    # Version history
```

## Technical Details

- **Backend**: Flask (Python)
- **Frontend**: HTML/CSS/JavaScript with Leaflet.js
- **Data Source**: OpenStreetMap via Overpass API
- **Mapping**: OSMnx library for geospatial analysis
- **PDF Generation**: ReportLab library
- **Network Resilience**: Multiple API endpoints with failover
- **Port**: 10101 (configurable)

## Troubleshooting

### Common Issues

1. **Network Connectivity Errors**:
   - The app automatically tries multiple OpenStreetMap servers
   - Wait a few minutes and try again if servers are busy
   - Check your internet connection

2. **Analysis Takes Too Long**:
   - Large radius areas take longer to process
   - Reduce radius to 200-500m for faster results
   - Urban areas with more data take longer

3. **PDF Generation Fails**:
   - Analysis will continue without PDF
   - Check logs for specific error details
   - Ensure sufficient disk space

### Logs
- Console output shows real-time progress
- File logs saved to `app.log`
- Frontend logs visible in browser console

## Development

The application is designed for production use with:
- Real OpenStreetMap data (no mocks)
- Comprehensive error handling
- Network resilience features
- Detailed logging and monitoring

For development, the Flask debug mode is enabled by default.

## License

[Add your license information here]
