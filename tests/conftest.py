"""
Pytest fixtures and test configuration
"""
import os
import sys
import json
import pytest
from unittest.mock import Mock, MagicMock, patch
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, LineString
import networkx as nx

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import app
from foot_traffic_analysis import extract_osm_foot_traffic_indicators
from pdf_report_generator import LocationViabilityReportGenerator


@pytest.fixture
def test_client():
    """Create a Flask test client"""
    app.app.config['TESTING'] = True
    app.app.config['SECRET_KEY'] = 'test-secret-key'
    with app.app.test_client() as client:
        yield client


@pytest.fixture
def test_coordinates():
    """Sample test coordinates (Toronto City Hall)"""
    return {
        'latitude': 43.6532,
        'longitude': -79.3832,
        'radius': 300
    }


@pytest.fixture
def mock_osm_graph():
    """Create a mock OSMnx graph for intersection counting"""
    G = nx.MultiDiGraph()
    # Add CRS to graph attributes for OSMnx compatibility
    G.graph['crs'] = 'EPSG:4326'

    # Create a simple street network with 5 intersections
    nodes = [
        (1, {'y': 43.6532, 'x': -79.3832, 'street_count': 3}),
        (2, {'y': 43.6535, 'x': -79.3835, 'street_count': 2}),
        (3, {'y': 43.6530, 'x': -79.3830, 'street_count': 2}),
        (4, {'y': 43.6538, 'x': -79.3828, 'street_count': 2}),
        (5, {'y': 43.6528, 'x': -79.3838, 'street_count': 2}),
    ]
    for node_id, attrs in nodes:
        G.add_node(node_id, **attrs)

    # Add edges
    edges = [(1, 2), (1, 3), (2, 4), (3, 5), (4, 5)]
    for u, v in edges:
        G.add_edge(u, v)

    return G


@pytest.fixture
def mock_osm_places():
    """Create mock OSM places data (GeoDataFrame)"""
    places_data = [
        {
            'name': 'Test Restaurant',
            'amenity': 'restaurant',
            'geometry': Point(-79.3832, 43.6532),
            'addr:street': 'Queen Street',
            'addr:housenumber': '100'
        },
        {
            'name': 'Test Cafe',
            'amenity': 'cafe',
            'geometry': Point(-79.3835, 43.6535),
            'addr:street': 'Bay Street',
            'addr:housenumber': '200'
        },
        {
            'name': 'Test Shop',
            'shop': 'clothing',
            'geometry': Point(-79.3830, 43.6530),
            'addr:street': 'King Street',
            'addr:housenumber': '300'
        },
        {
            'name': None,
            'shop': 'supermarket',
            'geometry': Point(-79.3828, 43.6538),
        },
    ]
    return gpd.GeoDataFrame(places_data, crs='EPSG:4326')


@pytest.fixture
def mock_analysis_results():
    """Mock analysis results with all indicators"""
    return {
        'restaurants_cafes': 25,
        'restaurants_cafes_places': [
            {'name': 'Coffee Shop', 'lat': 43.6532, 'lon': -79.3832, 'address': '100 Queen St'},
            {'name': 'Pizza Place', 'lat': 43.6533, 'lon': -79.3833, 'address': '101 Queen St'},
        ],
        'shops': 45,
        'shops_places': [
            {'name': 'Clothing Store', 'lat': 43.6534, 'lon': -79.3834, 'address': '102 Queen St'},
        ],
        'intersections': 18,
        'office_buildings': 12,
        'office_buildings_places': [
            {'name': 'Office Tower', 'lat': 43.6535, 'lon': -79.3835, 'address': '103 Queen St'},
        ],
        'schools': 3,
        'schools_places': [],
        'transport_hubs': 8,
        'transport_hubs_places': [
            {'name': 'Bus Stop Queen/Bay', 'lat': 43.6536, 'lon': -79.3836, 'address': 'Queen St'},
        ],
        'hospitals': 2,
        'hospitals_places': [],
        'parking_lots': 15,
        'parking_lots_places': [],
        'crossings': 22,
        'crossings_places': [],
        'markets': 1,
        'markets_places': [
            {'name': 'Farmers Market', 'lat': 43.6537, 'lon': -79.3837, 'address': '104 Queen St'},
        ],
        'tourist_sites': 5,
        'tourist_sites_places': [],
        'places_of_worship': 4,
        'places_of_worship_places': [],
    }


@pytest.fixture
def mock_nominatim_response():
    """Mock Nominatim API response for reverse geocoding"""
    return {
        'display_name': 'Toronto City Hall, 100 Queen Street West, Toronto, Ontario, Canada',
        'address': {
            'city': 'Toronto',
            'state': 'Ontario',
            'country': 'Canada'
        }
    }


@pytest.fixture
def mock_overpass_response():
    """Mock Overpass API status response"""
    return {
        'status': 200,
        'text': 'Connected to Overpass API'
    }


@pytest.fixture
def sample_pdf_path(tmp_path):
    """Provide a temporary path for PDF generation"""
    return str(tmp_path / "test_report.pdf")


@pytest.fixture
def mock_osmnx_graph_from_point(mock_osm_graph):
    """Mock osmnx.graph_from_point and graph_to_gdfs functions"""
    with patch('foot_traffic_analysis.ox.graph_from_point') as mock_graph, \
         patch('foot_traffic_analysis.ox.graph_to_gdfs') as mock_gdfs:
        mock_graph.return_value = mock_osm_graph

        # Create mock nodes and edges GeoDataFrames
        nodes_data = {
            'y': [43.6532, 43.6535, 43.6530, 43.6538, 43.6528],
            'x': [-79.3832, -79.3835, -79.3830, -79.3828, -79.3838],
            'street_count': [3, 2, 2, 2, 2]
        }
        nodes_gdf = gpd.GeoDataFrame(nodes_data, crs='EPSG:4326')
        edges_gdf = gpd.GeoDataFrame(crs='EPSG:4326')
        mock_gdfs.return_value = (nodes_gdf, edges_gdf)

        yield mock_graph


@pytest.fixture
def mock_osmnx_features_from_point(mock_osm_places):
    """Mock osmnx.features_from_point function"""
    def mock_features(point, dist, tags):
        # Return different GeoDataFrames based on tags
        if 'amenity' in tags:
            amenities = tags['amenity']
            if isinstance(amenities, list):
                filtered = mock_osm_places[
                    mock_osm_places['amenity'].isin(amenities)
                ]
            else:
                filtered = mock_osm_places[
                    mock_osm_places['amenity'] == amenities
                ]
            return filtered if len(filtered) > 0 else gpd.GeoDataFrame()
        elif 'shop' in tags:
            filtered = mock_osm_places[mock_osm_places['shop'].notna()]
            return filtered if len(filtered) > 0 else gpd.GeoDataFrame()
        else:
            return gpd.GeoDataFrame()

    with patch('foot_traffic_analysis.ox.features_from_point') as mock:
        mock.side_effect = mock_features
        yield mock


@pytest.fixture
def mock_requests_get():
    """Mock requests.get for API calls"""
    with patch('requests.get') as mock:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'ok'}
        mock_response.text = 'OK'
        mock.return_value = mock_response
        yield mock


@pytest.fixture
def cleanup_files():
    """Cleanup generated files after tests"""
    files_to_cleanup = []

    def add_file(filepath):
        files_to_cleanup.append(filepath)

    yield add_file

    # Cleanup after test
    for filepath in files_to_cleanup:
        if os.path.exists(filepath):
            os.remove(filepath)


@pytest.fixture
def mock_env_overpass_endpoints():
    """Mock environment variable for Overpass endpoints"""
    test_endpoints = "https://overpass-api.de/api/,https://overpass.kumi.systems/api/"
    with patch.dict(os.environ, {'OVERPASS_ENDPOINTS': test_endpoints}):
        yield test_endpoints


@pytest.fixture
def session_data():
    """Mock session data for Flask"""
    return {
        'last_search': {
            'latitude': 43.6532,
            'longitude': -79.3832,
            'radius': 300,
            'location_name': 'Toronto, Ontario, Canada',
            'timestamp': '2025-11-18T10:00:00'
        }
    }


@pytest.fixture
def invalid_coordinates():
    """Invalid coordinate test cases"""
    return [
        {'latitude': 91, 'longitude': 0, 'radius': 300},  # Invalid latitude
        {'latitude': -91, 'longitude': 0, 'radius': 300},  # Invalid latitude
        {'latitude': 0, 'longitude': 181, 'radius': 300},  # Invalid longitude
        {'latitude': 0, 'longitude': -181, 'radius': 300},  # Invalid longitude
        {'latitude': 0, 'longitude': 0, 'radius': 50},  # Invalid radius (too small)
        {'latitude': 0, 'longitude': 0, 'radius': 3000},  # Invalid radius (too large)
    ]


@pytest.fixture
def mock_reportlab():
    """Mock ReportLab for PDF generation testing without creating actual PDFs"""
    with patch('pdf_report_generator.SimpleDocTemplate') as mock_doc, \
         patch('pdf_report_generator.Table') as mock_table:
        mock_instance = MagicMock()
        mock_doc.return_value = mock_instance
        yield {'doc': mock_doc, 'table': mock_table, 'instance': mock_instance}
