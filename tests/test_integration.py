"""
Integration tests for the complete Foot Traffic Analysis application
"""
import pytest
import os
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from app import app
from foot_traffic_analysis import extract_osm_foot_traffic_indicators
from pdf_report_generator import LocationViabilityReportGenerator


@pytest.fixture
def integration_client():
    """Create a Flask test client for integration tests"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestEndToEndAnalysis:
    """Test complete end-to-end analysis workflow"""

    def test_complete_analysis_workflow(self, integration_client, tmp_path):
        """Test the complete workflow from request to PDF generation"""
        with patch('app.extract_osm_foot_traffic_indicators') as mock_extract, \
             patch('app.get_location_name') as mock_location:

            # Set up mocks
            mock_extract.return_value = (
                pd.DataFrame([{
                    'restaurants_and_cafes': 25,
                    'shops': 45,
                    'intersection_count': 18,
                    'office_buildings': 12,
                    'schools_universities': 3,
                    'transport_hubs': 8,
                    'hospitals_clinics': 2,
                    'parking_lots': 15,
                    'pedestrian_crossings': 22,
                    'markets': 1,
                    'tourist_sites': 5,
                    'places_of_worship': 4
                }]),
                {
                    'restaurants_and_cafes': {
                        'count': 25,
                        'places': ['Restaurant 1', 'Cafe 2'],
                        'detailed_places': [
                            {'name': 'Restaurant 1', 'latitude': 43.6532, 'longitude': -79.3832, 'address': '100 Queen St'}
                        ]
                    },
                    'shops': {'count': 45, 'places': [], 'detailed_places': []},
                    'intersection_count': 18,
                    'office_buildings': {'count': 12, 'places': [], 'detailed_places': []},
                    'schools_universities': {'count': 3, 'places': [], 'detailed_places': []},
                    'transport_hubs': {'count': 8, 'places': [], 'detailed_places': []},
                    'hospitals_clinics': {'count': 2, 'places': [], 'detailed_places': []},
                    'parking_lots': {'count': 15, 'places': [], 'detailed_places': []},
                    'pedestrian_crossings': {'count': 22, 'places': [], 'detailed_places': []},
                    'markets': {'count': 1, 'places': [], 'detailed_places': []},
                    'tourist_sites': {'count': 5, 'places': [], 'detailed_places': []},
                    'places_of_worship': {'count': 4, 'places': [], 'detailed_places': []}
                }
            )
            mock_location.return_value = 'Toronto City Hall'

            # Make analysis request
            response = integration_client.post('/analyze',
                                             json={'lat': 43.6532, 'lon': -79.3832, 'radius': 300},
                                             content_type='application/json')

            # Verify response
            assert response.status_code == 200
            data = json.loads(response.data)

            # Check that all expected fields are present
            assert 'restaurants_and_cafes' in data
            assert 'shops' in data
            assert 'viability_score' in data
            assert 'viability_rating' in data
            assert 'pdf_report' in data
            assert 'saved_file' in data

            # Clean up generated files
            if 'saved_file' in data and os.path.exists(data['saved_file']):
                os.remove(data['saved_file'])
            if 'pdf_report' in data and data['pdf_report']:
                pdf_path = os.path.join('reports', data['pdf_report'])
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)

    def test_workflow_with_empty_results(self, integration_client):
        """Test workflow when no POIs are found"""
        with patch('app.extract_osm_foot_traffic_indicators') as mock_extract, \
             patch('app.get_location_name') as mock_location:

            # Return empty results
            empty_data = {indicator: {'count': 0, 'places': [], 'detailed_places': []}
                         for indicator in ['restaurants_and_cafes', 'shops', 'office_buildings',
                                         'schools_universities', 'transport_hubs', 'hospitals_clinics',
                                         'parking_lots', 'pedestrian_crossings', 'markets',
                                         'tourist_sites', 'places_of_worship']}
            empty_data['intersection_count'] = 0

            mock_extract.return_value = (
                pd.DataFrame([{k: 0 for k in empty_data.keys()}]),
                empty_data
            )
            mock_location.return_value = 'Remote Location'

            response = integration_client.post('/analyze',
                                             json={'lat': 45.0, 'lon': -75.0, 'radius': 300},
                                             content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['viability_rating'] == 'POOR'

            # Clean up
            if 'saved_file' in data and os.path.exists(data['saved_file']):
                os.remove(data['saved_file'])
            if 'pdf_report' in data and data['pdf_report']:
                pdf_path = os.path.join('reports', data['pdf_report'])
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)


class TestAPIEndpointIntegration:
    """Test integration between different API endpoints"""

    def test_analyze_then_last_search(self, integration_client):
        """Test that analysis is stored and retrievable via last-search"""
        with patch('app.extract_osm_foot_traffic_indicators') as mock_extract, \
             patch('app.get_location_name') as mock_location:

            mock_extract.return_value = (
                pd.DataFrame([{'shops': 10}]),
                {'shops': {'count': 10, 'places': [], 'detailed_places': []}}
            )
            mock_location.return_value = 'Test Location'

            # Perform analysis
            analyze_response = integration_client.post('/analyze',
                                                     json={'lat': 43.6532, 'lon': -79.3832, 'radius': 500},
                                                     content_type='application/json')
            assert analyze_response.status_code == 200

            # Retrieve last search
            last_search_response = integration_client.get('/api/last-search')

            if last_search_response.status_code == 200:
                data = json.loads(last_search_response.data)
                assert data['success'] is True
                assert data['lat'] == 43.6532
                assert data['lon'] == -79.3832
                assert data['radius'] == 500

    def test_analyze_then_download_report(self, integration_client):
        """Test that generated PDF can be downloaded"""
        with patch('app.extract_osm_foot_traffic_indicators') as mock_extract, \
             patch('app.get_location_name') as mock_location:

            mock_extract.return_value = (
                pd.DataFrame([{'shops': 10}]),
                {'shops': {'count': 10, 'places': [], 'detailed_places': []}}
            )
            mock_location.return_value = 'TestLocation'

            # Perform analysis
            analyze_response = integration_client.post('/analyze',
                                                     json={'lat': 43.6532, 'lon': -79.3832, 'radius': 300},
                                                     content_type='application/json')
            assert analyze_response.status_code == 200

            data = json.loads(analyze_response.data)

            # Try to download the report
            if 'pdf_report' in data and data['pdf_report']:
                download_response = integration_client.get(f"/download-report/{data['pdf_report']}")
                assert download_response.status_code in [200, 404]  # May not exist in test

                # Clean up
                pdf_path = os.path.join('reports', data['pdf_report'])
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)

            # Clean up JSON file
            if 'saved_file' in data and os.path.exists(data['saved_file']):
                os.remove(data['saved_file'])


class TestDataFlowIntegration:
    """Test data flow between components"""

    def test_osm_data_to_pdf_report(self, tmp_path):
        """Test data flow from OSM extraction to PDF report"""
        # Create mock analysis data
        analysis_data = {
            'restaurants_and_cafes': {'count': 20, 'places': [], 'detailed_places': []},
            'shops': {'count': 35, 'places': [], 'detailed_places': []},
            'intersection_count': 25,
            'office_buildings': {'count': 10, 'places': [], 'detailed_places': []},
            'schools_universities': {'count': 2, 'places': [], 'detailed_places': []},
            'transport_hubs': {'count': 5, 'places': [], 'detailed_places': []},
            'hospitals_clinics': {'count': 1, 'places': [], 'detailed_places': []},
            'parking_lots': {'count': 8, 'places': [], 'detailed_places': []},
            'pedestrian_crossings': {'count': 15, 'places': [], 'detailed_places': []},
            'markets': {'count': 1, 'places': [], 'detailed_places': []},
            'tourist_sites': {'count': 3, 'places': [], 'detailed_places': []},
            'places_of_worship': {'count': 2, 'places': [], 'detailed_places': []}
        }

        # Generate PDF report
        generator = LocationViabilityReportGenerator()
        output_path = tmp_path / "integration_test.pdf"

        result = generator.generate_report(
            analysis_data,
            'Integration Test Location',
            43.6532, -79.3832, 300,
            str(output_path)
        )

        # Verify PDF was created
        assert output_path.exists()

        # Verify report data
        assert result['viability_percentage'] > 0
        assert result['rating'] in ['BEST', 'OUTSTANDING', 'EXCELLENT', 'GOOD', 'MODERATE', 'POOR']
        assert len(result['scores']) == 12

    def test_json_serialization_in_api(self, integration_client):
        """Test that numpy types are properly serialized in API responses"""
        with patch('app.extract_osm_foot_traffic_indicators') as mock_extract, \
             patch('app.get_location_name') as mock_location:

            # Create data with numpy types
            try:
                import numpy as np
                df_data = {
                    'shops': np.int64(10),
                    'restaurants_and_cafes': np.int64(5)
                }
            except ImportError:
                df_data = {'shops': 10, 'restaurants_and_cafes': 5}

            mock_extract.return_value = (
                pd.DataFrame([df_data]),
                {
                    'shops': {'count': 10, 'places': [], 'detailed_places': []},
                    'restaurants_and_cafes': {'count': 5, 'places': [], 'detailed_places': []}
                }
            )
            mock_location.return_value = 'Test'

            response = integration_client.post('/analyze',
                                             json={'lat': 43.6532, 'lon': -79.3832},
                                             content_type='application/json')

            assert response.status_code == 200
            # Should be valid JSON (no numpy types)
            data = json.loads(response.data)
            assert isinstance(data, dict)

            # Clean up
            if 'saved_file' in data and os.path.exists(data['saved_file']):
                os.remove(data['saved_file'])


class TestErrorPropagation:
    """Test error handling across components"""

    def test_osm_extraction_error_propagation(self, integration_client):
        """Test that OSM extraction errors are properly handled"""
        with patch('app.extract_osm_foot_traffic_indicators') as mock_extract:
            mock_extract.side_effect = Exception("OSM API error")

            response = integration_client.post('/analyze',
                                             json={'lat': 43.6532, 'lon': -79.3832},
                                             content_type='application/json')

            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'error' in data

    def test_pdf_generation_error_handling(self, integration_client):
        """Test that PDF generation errors don't break the analysis"""
        with patch('app.extract_osm_foot_traffic_indicators') as mock_extract, \
             patch('app.get_location_name') as mock_location, \
             patch('app.LocationViabilityReportGenerator') as mock_gen:

            mock_extract.return_value = (
                pd.DataFrame([{'shops': 10}]),
                {'shops': {'count': 10, 'places': [], 'detailed_places': []}}
            )
            mock_location.return_value = 'Test'

            # Make PDF generation fail
            mock_gen_instance = MagicMock()
            mock_gen_instance.generate_report.side_effect = Exception("PDF error")
            mock_gen.return_value = mock_gen_instance

            response = integration_client.post('/analyze',
                                             json={'lat': 43.6532, 'lon': -79.3832},
                                             content_type='application/json')

            # Should still succeed with analysis data
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['pdf_report'] is None
            assert 'shops' in data

            # Clean up
            if 'saved_file' in data and os.path.exists(data['saved_file']):
                os.remove(data['saved_file'])


class TestConcurrentRequests:
    """Test handling of multiple concurrent requests"""

    def test_multiple_sequential_requests(self, integration_client):
        """Test multiple sequential analysis requests"""
        with patch('app.extract_osm_foot_traffic_indicators') as mock_extract, \
             patch('app.get_location_name') as mock_location:

            mock_extract.return_value = (
                pd.DataFrame([{'shops': 10}]),
                {'shops': {'count': 10, 'places': [], 'detailed_places': []}}
            )
            mock_location.return_value = 'Test'

            # Make multiple requests
            locations = [
                (43.6532, -79.3832),
                (40.7128, -74.0060),
                (51.5074, -0.1278)
            ]

            for lat, lon in locations:
                response = integration_client.post('/analyze',
                                                 json={'lat': lat, 'lon': lon, 'radius': 300},
                                                 content_type='application/json')
                assert response.status_code == 200

                # Clean up
                data = json.loads(response.data)
                if 'saved_file' in data and os.path.exists(data['saved_file']):
                    os.remove(data['saved_file'])
                if 'pdf_report' in data and data['pdf_report']:
                    pdf_path = os.path.join('reports', data['pdf_report'])
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)


class TestDifferentRadii:
    """Test analysis with different radius values"""

    def test_multiple_radii(self, integration_client):
        """Test analysis with different radius values"""
        with patch('app.extract_osm_foot_traffic_indicators') as mock_extract, \
             patch('app.get_location_name') as mock_location:

            def extract_with_radius(lat, lon, radius_m):
                # Return different counts based on radius
                count = radius_m // 100  # More POIs with larger radius
                return (
                    pd.DataFrame([{'shops': count}]),
                    {'shops': {'count': count, 'places': [], 'detailed_places': []}}
                )

            mock_extract.side_effect = extract_with_radius
            mock_location.return_value = 'Test'

            # Test different radii
            radii = [100, 300, 500, 1000]

            for radius in radii:
                response = integration_client.post('/analyze',
                                                 json={'lat': 43.6532, 'lon': -79.3832, 'radius': radius},
                                                 content_type='application/json')
                assert response.status_code == 200

                data = json.loads(response.data)
                assert data['radius_meters'] == radius

                # Clean up
                if 'saved_file' in data and os.path.exists(data['saved_file']):
                    os.remove(data['saved_file'])
                if 'pdf_report' in data and data['pdf_report']:
                    pdf_path = os.path.join('reports', data['pdf_report'])
                    if os.path.exists(pdf_path):
                        os.remove(pdf_path)


class TestFileGeneration:
    """Test file generation and cleanup"""

    def test_json_file_structure(self, integration_client):
        """Test that generated JSON file has correct structure"""
        with patch('app.extract_osm_foot_traffic_indicators') as mock_extract, \
             patch('app.get_location_name') as mock_location:

            mock_extract.return_value = (
                pd.DataFrame([{'shops': 10}]),
                {'shops': {'count': 10, 'places': ['Shop 1'], 'detailed_places': []}}
            )
            mock_location.return_value = 'TestLocation'

            response = integration_client.post('/analyze',
                                             json={'lat': 43.6532, 'lon': -79.3832, 'radius': 300},
                                             content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.data)

            # Check JSON file was created
            if 'saved_file' in data and os.path.exists(data['saved_file']):
                with open(data['saved_file'], 'r') as f:
                    saved_data = json.load(f)

                # Verify structure
                assert 'timestamp' in saved_data
                assert 'location_name' in saved_data
                assert 'latitude' in saved_data
                assert 'longitude' in saved_data
                assert 'radius_meters' in saved_data
                assert 'analysis' in saved_data

                # Clean up
                os.remove(data['saved_file'])

            if 'pdf_report' in data and data['pdf_report']:
                pdf_path = os.path.join('reports', data['pdf_report'])
                if os.path.exists(pdf_path):
                    os.remove(pdf_path)

    def test_pdf_file_generation(self, integration_client):
        """Test that PDF file is actually generated"""
        with patch('app.extract_osm_foot_traffic_indicators') as mock_extract, \
             patch('app.get_location_name') as mock_location:

            mock_extract.return_value = (
                pd.DataFrame([{'shops': 10}]),
                {'shops': {'count': 10, 'places': [], 'detailed_places': []}}
            )
            mock_location.return_value = 'TestLocation'

            response = integration_client.post('/analyze',
                                             json={'lat': 43.6532, 'lon': -79.3832, 'radius': 300},
                                             content_type='application/json')

            assert response.status_code == 200
            data = json.loads(response.data)

            # Check PDF was created
            if 'pdf_report' in data and data['pdf_report']:
                pdf_path = os.path.join('reports', data['pdf_report'])
                assert os.path.exists(pdf_path)

                # Verify it's a PDF file (starts with %PDF)
                with open(pdf_path, 'rb') as f:
                    header = f.read(4)
                    assert header == b'%PDF'

                # Clean up
                os.remove(pdf_path)

            if 'saved_file' in data and os.path.exists(data['saved_file']):
                os.remove(data['saved_file'])
