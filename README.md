# Foot Traffic Analysis Tool

A web-based application for analyzing foot traffic indicators in specific locations using OpenStreetMap data. The tool provides comprehensive analysis of various factors that contribute to pedestrian activity and generates detailed viability reports.

## Features

- **Interactive Map Interface**: Click on any location or search for addresses
- **Comprehensive Analysis**: Analyzes 12 foot traffic indicators including:
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
  - Office buildings
  - Parking facilities

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
   - Default: 300 meters
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
- **Best (98%+)**: Ideal for premium retail and flagship stores
- **Outstanding (95-97%)**: Exceptional foot traffic potential
- **Excellent (85-94%)**: Highly suitable for foot traffic-dependent businesses
- **Good (80-89%)**: Suitable for most commercial activities
- **Moderate (70-79%)**: Requires careful business planning
- **Poor (<70%)**: Limited foot traffic potential

### Key Indicators
The analysis evaluates locations based on weighted criteria:
- **Shops** (17% weight): Primary foot traffic generators
- **Restaurants/Cafes** (13% weight): Consistent visitor attraction
- **Intersections** (12% weight): Pedestrian movement indicators
- **Office Buildings** (10% weight): Strong B2B lunch crowd drivers
- **Transport Hubs** (10% weight): Commuter foot traffic
- **Schools** (9% weight): Regular crowd generation
- **Healthcare** (7% weight): Steady visitor flow
- **Parking Lots** (7% weight): Drive-in accessibility boosters
- **Pedestrian Infrastructure** (7% weight): Walkability indicators
- **Markets** (6% weight): Commercial activity concentration
- **Tourist Sites** (1% weight): Occasional visitor attraction
- **Places of Worship** (1% weight): Periodic gatherings

## File Structure

```