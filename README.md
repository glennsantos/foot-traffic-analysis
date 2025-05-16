# Foot Traffic Analysis

A web application for analyzing foot traffic indicators using OpenStreetMap data.

## Running with Docker (Recommended)

### Prerequisites
- Docker installed on your system

### Steps

1. **Build the Docker image**
   ```bash
   docker build -t foot-traffic-analysis .
   ```

2. **Run the container**
   ```bash
   docker run -d -p 8081:8081 -v $(pwd)/analyses:/app/analyses --name foot-traffic-app foot-traffic-analysis
   ```
   - `-p 1010:1010` maps port 1010 on your host to port 1010 in the container
   - `-v $(pwd)/analyses:/app/analyses` mounts the local analyses directory to persist results
   - `--name foot-traffic-app` gives the container a name

3. **Access the application**
   Open your web browser and go to: http://localhost:8081

4. **Stopping the container**
   ```bash
   docker stop foot-traffic-app
   ```

5. **Removing the container**
   ```bash
   docker rm foot-traffic-app
   ```

6. **Viewing logs**
   ```bash
   docker logs foot-traffic-app
   ```

## Running with Python

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### Steps

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**
   ```bash
   python3 app.py
   ```
   - The application will be available at http://localhost:8081
   - Press `Ctrl+C` to stop the server

   **Note:** If port 8081 is in use, you can modify the port in `app.py` by changing the `port` parameter in the `app.run()` call.

## Usage

1. Open the application in your web browser
2. Use the map interface to select a location
3. The application will analyze foot traffic indicators for the selected area
4. View the analysis results in the web interface

## Project Structure

- `app.py` - Main Flask application
- `foot_traffic_analysis.py` - Core analysis functionality
- `templates/` - HTML templates
- `analyses/` - Directory where analysis results are stored (created automatically)
- `cache/` - Cached OSM data (created automatically)

## License

[Add your license information here]
