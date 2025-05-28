# Changelog

All notable changes to the Foot Traffic Analysis application will be documented in this file.

## [2025-05-28] - Enhanced Business Indicators Update

### Added
- **Office Buildings Indicator**: New indicator to track office buildings and commercial structures
  - Threshold: ≥ 3 office buildings
  - Weight: 10% (strong B2B lunch crowd driver)
  - OSM Tags: `building=office`, `building=commercial`, `office=*`
  - Description: Office buildings generate strong B2B lunch crowd traffic

- **Parking Lots Indicator**: New indicator to track parking facilities
  - Threshold: ≥ 1 parking facility
  - Weight: 7% (boosts drive-in accessibility)
  - OSM Tags: `amenity=parking`
  - Description: Parking facilities boost drive-in accessibility

### Changed
- **Weight Redistribution**: Adjusted existing indicator weights to accommodate new indicators while maintaining 100% total:
  - Restaurants/Cafes: 15% → 13%
  - Shops: 20% → 17%
  - Intersections: 15% → 12%
  - Schools/Universities: 10% → 9%
  - Bus Stops: 12% → 10%
  - Healthcare: 8% → 7%
  - Pedestrian Crossings: 8% → 7%
  - Markets: 7% → 6%
  - Tourist Sites: 3% → 1%
  - Places of Worship: 2% → 1%

### Technical Details
- Updated `foot_traffic_analysis.py` to collect office and parking data from OSM
- Modified `pdf_report_generator.py` with new criteria and weights
- Enhanced frontend `index.html` with new indicator descriptions and thresholds
- Maintained backward compatibility with existing analysis files

### Business Impact
- Better assessment of business district viability
- Improved evaluation of accessibility for drive-in customers
- More comprehensive foot traffic analysis for commercial locations

## [2025-05-28] - Network Resilience Update

### Fixed
- **Critical Network Issue**: Fixed DNS resolution failures when connecting to OpenStreetMap Overpass API
- **Connection Timeouts**: Improved timeout handling and retry logic for API requests

### Added
- **Multiple Endpoint Support**: Added fallback to multiple Overpass API endpoints:
  - `overpass.kumi.systems` (primary)
  - `overpass-api.de` (fallback)
  - `overpass.nchc.org.tw` (fallback)
- **Endpoint Health Checking**: Automatic testing of endpoint availability before analysis
- **Exponential Backoff**: Intelligent retry logic with increasing delays (5s, 10s, 20s)
- **Network Connectivity Testing**: Frontend now tests connectivity before starting analysis
- **Enhanced Error Messages**: Better user feedback for network-related issues
- **Comprehensive Logging**: Added detailed logging for both frontend and backend operations

### Improved
- **Timeout Settings**: Increased API timeout from 3 to 5 minutes for better reliability
- **Error Handling**: More graceful handling of network failures with helpful user suggestions
- **User Experience**: Progress indicators and helpful suggestions during network issues

### Technical Details
- Modified `foot_traffic_analysis.py` to implement robust endpoint switching
- Added network connectivity pre-checks in frontend
- Enhanced logging throughout the application stack
- Improved error messages with actionable suggestions for users

### Usage Notes
- Analysis may take 1-3 minutes depending on network conditions
- If analysis fails, wait a few minutes and try again
- The application will automatically try alternative servers if one is unavailable

## [2.0.0] - 2025-05-28

### Added - PDF Report Generation & Viability Analysis
- **Comprehensive PDF Reports**: Automatically generated detailed viability reports for each analysis
  - Executive summary with key findings and recommendations
  - Overall viability score (0-100%) with rating (Excellent/Good/Moderate/Poor)
  - Indicators ranked from most promising to least promising
  - Detailed analysis of each indicator with business implications
  - Specific recommendations based on viability score
  - Professional formatting with tables, charts, and structured layout

- **Intelligent Viability Scoring System**:
  - Weighted scoring algorithm based on business importance
  - Shops (20% weight) - Primary foot traffic generators
  - Restaurants/Cafes (15% weight) - Consistent visitor attraction
  - Intersections (15% weight) - Pedestrian movement indicators
  - Public Transport (12% weight) - Commuter foot traffic
  - Schools (10% weight) - Regular crowd generation
  - Healthcare (8% weight) - Steady visitor flow
  - Pedestrian Infrastructure (8% weight) - Walkability indicators
  - Markets (7% weight) - Commercial activity concentration
  - Tourist Sites (3% weight) - Occasional visitor attraction
  - Places of Worship (2% weight) - Periodic gatherings

- **Enhanced Frontend Features**:
  - Viability summary display with color-coded ratings
  - PDF download button for detailed reports
  - Summary information shown directly in results panel
  - Improved visual hierarchy and information organization

- **Technical Improvements**:
  - Added ReportLab and Matplotlib dependencies for PDF generation
  - New `pdf_report_generator.py` module with comprehensive reporting logic
  - Enhanced Flask app with PDF download endpoint
  - Automatic report file management in `reports/` directory
  - Graceful fallback if PDF generation fails

### Changed
- Updated requirements.txt with specific version numbers for better stability
- Enhanced README.md with comprehensive documentation of new features
- Improved error handling for PDF generation process
- Updated file structure documentation

### Technical Details
- PDF reports saved to `reports/` directory with timestamped filenames
- Reports include location coordinates, analysis radius, and generation timestamp
- Scoring algorithm considers both threshold achievement and relative importance
- Professional report layout with consistent styling and branding

## [1.2.0] - 2025-05-28

### Added - Network Resilience & Comprehensive Logging
- **Multiple Overpass API Endpoints**: Added fallback servers for improved reliability
  - Primary: overpass-api.de
  - Fallback 1: overpass.kumi.systems  
  - Fallback 2: overpass.nchc.org.tw
- **Endpoint Health Checking**: Pre-analysis connectivity tests
- **Exponential Backoff Retry Logic**: 5s, 10s, 20s delays between retries
- **Extended Timeout**: Increased from 3 to 5 minutes for large area analysis
- **Comprehensive Logging**: 
  - Backend file logging (app.log) and console output
  - Frontend progress messages and error reporting
  - Network connectivity pre-checks and status updates
  - Step-by-step analysis progress tracking

### Added - User Experience Improvements  
- **Confirmation Dialogs**: User confirmation required before starting analysis
- **Progress Tracking**: Real-time status updates during analysis process
- **Enhanced Error Messages**: User-friendly error descriptions with suggestions
- **Network Status Indicators**: Clear feedback on connectivity issues

### Fixed
- **DOM Element Access**: Fixed "TypeError: document.getElementById(...) is null" error
- **HTML Structure Preservation**: Proper element restoration in analyzeLocation()
- **Safe Element Handling**: Added null checks for all DOM operations
- **Results Display**: Fixed displayResults() function element access

### Changed
- **Port Configuration**: Updated default port from 8080 to 10101
- **Error Handling**: Enhanced error messages for network-related issues
- **User Interface**: Improved instruction text and confirmation prompts
- **Logging Format**: Structured log messages with timestamps and severity levels

### Technical Details
- Network resilience implemented in `foot_traffic_analysis.py`
- Frontend logging system with console and user-visible messages
- Session-based storage for last search locations
- Client IP tracking for user session management

## [1.1.0] - 2025-05-27

### Added
- **Location Search**: Nominatim-powered address search with autocomplete
- **Last Search Memory**: Automatic restoration of previous search location
- **Enhanced UI**: Improved styling and user experience
- **Session Management**: Client IP-based session tracking

### Changed
- **Port**: Updated from 8080 to 1010 (later changed to 10101)
- **File Organization**: Analyses saved to `analyses_new/` directory
- **Error Handling**: Improved error messages and user feedback

## [1.0.0] - 2025-05-27

### Added
- **Initial Release**: Basic foot traffic analysis functionality
- **Interactive Map**: Leaflet.js-based map interface
- **OSM Data Analysis**: Integration with OpenStreetMap via OSMnx
- **10 Key Indicators**: Comprehensive analysis of foot traffic factors
- **Criteria-Based Evaluation**: Threshold-based assessment system
- **JSON Export**: Analysis results saved to structured files
- **Responsive Design**: Mobile-friendly interface

### Features
- Click-to-analyze map interface
- Adjustable analysis radius (100-2000m)
- Real-time data from OpenStreetMap
- Detailed indicator breakdown with place listings
- Criteria compliance checking with visual indicators 