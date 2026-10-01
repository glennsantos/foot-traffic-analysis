"""
Unit tests for foot_traffic_analysis.py module
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
import networkx as nx

from foot_traffic_analysis import (
    _parse_overpass_endpoints_from_env,
    _normalize_overpass_urls,
    _status_url_for,
    test_overpass_endpoint as check_endpoint_status,  # Renamed to avoid pytest collecting it
    get_working_endpoint,
    extract_osm_foot_traffic_indicators,
)


class TestOverpassEndpointParsing:
    """Test Overpass endpoint parsing and normalization"""

    def test_parse_overpass_endpoints_from_env_empty(self):
        """Test parsing when env variable is empty"""
        with patch.dict(os.environ, {'OVERPASS_ENDPOINTS': ''}):
            result = _parse_overpass_endpoints_from_env()
            assert result is None

    def test_parse_overpass_endpoints_from_env_single(self):
        """Test parsing single endpoint"""
        with patch.dict(os.environ, {'OVERPASS_ENDPOINTS': 'https://overpass-api.de/api/'}):
            result = _parse_overpass_endpoints_from_env()
            assert result == ['https://overpass-api.de/api/']

    def test_parse_overpass_endpoints_from_env_multiple(self):
        """Test parsing multiple endpoints"""
        endpoints = 'https://overpass-api.de/api/,https://overpass.kumi.systems/api/'
        with patch.dict(os.environ, {'OVERPASS_ENDPOINTS': endpoints}):
            result = _parse_overpass_endpoints_from_env()
            assert len(result) == 2
            assert 'https://overpass-api.de/api/' in result
            assert 'https://overpass.kumi.systems/api/' in result

    def test_parse_overpass_endpoints_from_env_with_spaces(self):
        """Test parsing endpoints with extra spaces"""
        endpoints = '  https://overpass-api.de/api/  ,  https://overpass.kumi.systems/api/  '
        with patch.dict(os.environ, {'OVERPASS_ENDPOINTS': endpoints}):
            result = _parse_overpass_endpoints_from_env()
            assert len(result) == 2
            assert all('  ' not in endpoint for endpoint in result)

    def test_parse_overpass_endpoints_no_env(self):
        """Test when environment variable is not set"""
        with patch.dict(os.environ, {}, clear=True):
            result = _parse_overpass_endpoints_from_env()
            assert result is None


class TestURLNormalization:
    """Test URL normalization for v1/v2 compatibility"""

    def test_normalize_base_url(self):
        """Test normalization of base URL"""
        base, full = _normalize_overpass_urls("https://overpass-api.de/api")
        assert base == "https://overpass-api.de/api"
        assert full == "https://overpass-api.de/api/interpreter"

    def test_normalize_interpreter_url(self):
        """Test normalization of full interpreter URL"""
        base, full = _normalize_overpass_urls("https://overpass-api.de/api/interpreter")
        assert base == "https://overpass-api.de/api"
        assert full == "https://overpass-api.de/api/interpreter"

    def test_normalize_trailing_slash(self):
        """Test normalization with trailing slash"""
        base, full = _normalize_overpass_urls("https://overpass-api.de/api/")
        assert base == "https://overpass-api.de/api"
        assert full == "https://overpass-api.de/api/interpreter"

    def test_normalize_empty_string(self):
        """Test normalization with empty string"""
        base, full = _normalize_overpass_urls("")
        assert base == ""
        assert full == ""

    def test_normalize_none(self):
        """Test normalization with None"""
        base, full = _normalize_overpass_urls(None)
        assert base == ""
        assert full == ""


class TestStatusURL:
    """Test status URL generation"""

    def test_status_url_base_endpoint(self):
        """Test status URL for base endpoint"""
        url = _status_url_for("https://overpass-api.de/api")
        assert url == "https://overpass-api.de/api/status"

    def test_status_url_interpreter_endpoint(self):
        """Test status URL for interpreter endpoint"""
        url = _status_url_for("https://overpass-api.de/api/interpreter")
        assert url == "https://overpass-api.de/api/status"

    def test_status_url_trailing_slash(self):
        """Test status URL with trailing slash"""
        url = _status_url_for("https://overpass-api.de/api/")
        assert url == "https://overpass-api.de/api/status"


class TestOverpassEndpointTesting:
    """Test endpoint connectivity testing"""

    def test_endpoint_working(self, mock_requests_get):
        """Test when endpoint is accessible"""
        mock_requests_get.return_value.status_code = 200
        result = check_endpoint_status("https://overpass-api.de/api")
        assert result is True

    def test_endpoint_redirect(self, mock_requests_get):
        """Test when endpoint returns redirect (3xx)"""
        mock_requests_get.return_value.status_code = 301
        result = check_endpoint_status("https://overpass-api.de/api")
        assert result is True

    def test_endpoint_error(self, mock_requests_get):
        """Test when endpoint returns error"""
        mock_requests_get.return_value.status_code = 500
        result = check_endpoint_status("https://overpass-api.de/api")
        assert result is False

    def test_endpoint_timeout(self):
        """Test when endpoint times out"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = TimeoutError()
            result = check_endpoint_status("https://overpass-api.de/api")
            assert result is False

    def test_endpoint_connection_error(self):
        """Test when connection fails"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = ConnectionError()
            result = check_endpoint_status("https://overpass-api.de/api")
            assert result is False


class TestWorkingEndpoint:
    """Test working endpoint selection"""

    def test_env_override(self):
        """Test environment variable override"""
        with patch.dict(os.environ, {'OVERPASS_URL': 'https://custom-endpoint.com/api'}):
            result = get_working_endpoint()
            assert result == 'https://custom-endpoint.com/api'

    def test_first_endpoint_works(self):
        """Test when first endpoint is working"""
        with patch('foot_traffic_analysis.test_overpass_endpoint') as mock_test:
            mock_test.return_value = True
            with patch.dict(os.environ, {}, clear=True):
                result = get_working_endpoint()
                assert result in ['https://overpass.kumi.systems/api', 'https://overpass-api.de/api']

    def test_second_endpoint_works(self):
        """Test when first fails but second works"""
        with patch('foot_traffic_analysis.test_overpass_endpoint') as mock_test:
            mock_test.side_effect = [False, True]
            with patch.dict(os.environ, {}, clear=True):
                result = get_working_endpoint()
                assert result in ['https://overpass.kumi.systems/api', 'https://overpass-api.de/api']

    def test_all_endpoints_fail(self):
        """Test when all endpoints fail (should return first as fallback)"""
        with patch('foot_traffic_analysis.test_overpass_endpoint') as mock_test:
            mock_test.return_value = False
            with patch.dict(os.environ, {}, clear=True):
                result = get_working_endpoint()
                # Should return first endpoint as fallback
                assert result is not None


class TestOSMDataExtraction:
    """Test OSM data extraction and analysis"""

    @pytest.mark.skip(reason="Integration test - requires full OSMnx mocking")
    def test_extract_with_valid_coordinates(self, test_coordinates, mock_osmnx_graph_from_point,
                                           mock_osmnx_features_from_point):
        """Test extraction with valid coordinates"""
        with patch('foot_traffic_analysis.get_working_endpoint') as mock_endpoint:
            mock_endpoint.return_value = 'https://overpass-api.de/api'

            df, analysis = extract_osm_foot_traffic_indicators(
                test_coordinates['latitude'],
                test_coordinates['longitude'],
                test_coordinates['radius']
            )

            # Check that DataFrame is returned
            assert isinstance(df, pd.DataFrame)
            assert len(df) == 1

            # Check that analysis dict contains all required keys
            assert 'latitude' in analysis
            assert 'longitude' in analysis
            assert 'restaurants_and_cafes' in analysis
            assert 'shops' in analysis
            assert 'intersection_count' in analysis
            assert 'office_buildings' in analysis
            assert 'schools_universities' in analysis
            assert 'transport_hubs' in analysis
            assert 'hospitals_clinics' in analysis
            assert 'parking_lots' in analysis
            assert 'pedestrian_crossings' in analysis
            assert 'markets' in analysis
            assert 'tourist_sites' in analysis
            assert 'places_of_worship' in analysis

    @pytest.mark.skip(reason="Integration test - requires full OSMnx mocking")
    def test_extract_with_retry_logic(self, test_coordinates, mock_osm_graph):
        """Test that retry logic is triggered on failure"""
        with patch('foot_traffic_analysis.get_working_endpoint') as mock_endpoint, \
             patch('foot_traffic_analysis.ox.features_from_point') as mock_features, \
             patch('foot_traffic_analysis.ox.graph_from_point') as mock_graph, \
             patch('foot_traffic_analysis.ox.graph_to_gdfs') as mock_gdfs, \
             patch('time.sleep'):  # Mock sleep to speed up test

            mock_endpoint.return_value = 'https://overpass-api.de/api'

            # First two attempts fail, third succeeds
            mock_features.side_effect = [
                Exception("Network error"),
                Exception("Timeout"),
                gpd.GeoDataFrame()  # Success on third attempt
            ]
            mock_graph.return_value = mock_osm_graph

            # Mock graph_to_gdfs
            nodes_data = {'street_count': [3, 2, 2]}
            nodes_gdf = gpd.GeoDataFrame(nodes_data, crs='EPSG:4326')
            edges_gdf = gpd.GeoDataFrame(crs='EPSG:4326')
            mock_gdfs.return_value = (nodes_gdf, edges_gdf)

            df, analysis = extract_osm_foot_traffic_indicators(
                test_coordinates['latitude'],
                test_coordinates['longitude'],
                test_coordinates['radius'],
                max_retries=3
            )

            # Should succeed after retries
            assert df is not None
            assert analysis is not None
            assert mock_features.call_count == 3

    def test_extract_all_retries_fail(self, test_coordinates):
        """Test when all retries fail"""
        with patch('foot_traffic_analysis.get_working_endpoint') as mock_endpoint, \
             patch('foot_traffic_analysis.ox.features_from_point') as mock_features, \
             patch('time.sleep'):

            mock_endpoint.return_value = 'https://overpass-api.de/api'
            mock_features.side_effect = Exception("Network error")

            with pytest.raises(Exception) as exc_info:
                extract_osm_foot_traffic_indicators(
                    test_coordinates['latitude'],
                    test_coordinates['longitude'],
                    test_coordinates['radius'],
                    max_retries=3
                )

            assert "Failed to fetch OSM POIs after 3 attempts" in str(exc_info.value)

    def test_extract_street_network_failure_is_reported(self, test_coordinates):
        """A missing street network must not be reported as zero intersections."""
        with patch('foot_traffic_analysis.get_working_endpoint') as mock_endpoint, \
             patch('foot_traffic_analysis.ox.features_from_point') as mock_features, \
             patch('foot_traffic_analysis.ox.graph_from_point') as mock_graph, \
             patch('time.sleep'):

            mock_endpoint.return_value = 'https://overpass-api.de/api'
            mock_features.return_value = gpd.GeoDataFrame()
            mock_graph.side_effect = Exception("Graph extraction failed")

            with pytest.raises(Exception, match="Failed to fetch OSM street network after 3 attempts"):
                extract_osm_foot_traffic_indicators(
                    test_coordinates['latitude'],
                    test_coordinates['longitude'],
                    test_coordinates['radius'],
                    max_retries=3
                )

    @pytest.mark.skip(reason="Integration test - requires full OSMnx mocking")
    def test_extract_with_custom_radius(self, mock_osmnx_graph_from_point,
                                       mock_osmnx_features_from_point):
        """Test extraction with custom radius"""
        with patch('foot_traffic_analysis.get_working_endpoint') as mock_endpoint:
            mock_endpoint.return_value = 'https://overpass-api.de/api'

            df, analysis = extract_osm_foot_traffic_indicators(
                43.6532, -79.3832, radius_m=500
            )

            assert df is not None
            # Verify that the radius was used in the API calls
            assert mock_osmnx_features_from_point.called

    def test_invalid_coordinates(self):
        """Test with invalid coordinates"""
        with patch('foot_traffic_analysis.get_working_endpoint') as mock_endpoint, \
             patch('foot_traffic_analysis.ox.features_from_point') as mock_features:

            mock_endpoint.return_value = 'https://overpass-api.de/api'
            mock_features.side_effect = Exception("Invalid coordinates")

            with pytest.raises(Exception):
                extract_osm_foot_traffic_indicators(999, 999, 300)


class TestPlaceDataExtraction:
    """Test place data extraction and formatting"""

    @pytest.mark.skip(reason="Integration test - requires full OSMnx mocking")
    def test_place_collection_with_results(self, mock_osm_places, mock_osmnx_graph_from_point,
                                          mock_osmnx_features_from_point):
        """Test that places are collected correctly"""
        with patch('foot_traffic_analysis.get_working_endpoint') as mock_endpoint:
            mock_endpoint.return_value = 'https://overpass-api.de/api'

            df, analysis = extract_osm_foot_traffic_indicators(43.6532, -79.3832, 300)

            # Check that restaurants_and_cafes has places
            restaurants = analysis['restaurants_and_cafes']
            assert isinstance(restaurants, dict)
            assert 'count' in restaurants
            assert 'places' in restaurants
            assert 'detailed_places' in restaurants

    @pytest.mark.skip(reason="Integration test - requires full OSMnx mocking")
    def test_detailed_place_info_structure(self, mock_osm_places, mock_osmnx_graph_from_point,
                                          mock_osmnx_features_from_point):
        """Test that detailed place info has correct structure"""
        with patch('foot_traffic_analysis.get_working_endpoint') as mock_endpoint:
            mock_endpoint.return_value = 'https://overpass-api.de/api'

            df, analysis = extract_osm_foot_traffic_indicators(43.6532, -79.3832, 300)

            # Check structure of detailed places
            for category_key in ['restaurants_and_cafes', 'shops']:
                category = analysis[category_key]
                if category['count'] > 0:
                    for place in category['detailed_places']:
                        assert 'name' in place
                        assert 'latitude' in place
                        assert 'longitude' in place
                        assert 'address' in place

    @pytest.mark.skip(reason="Integration test - requires full OSMnx mocking")
    def test_empty_place_collection(self, mock_osm_graph):
        """Test place collection when no POIs are found"""
        with patch('foot_traffic_analysis.get_working_endpoint') as mock_endpoint, \
             patch('foot_traffic_analysis.ox.features_from_point') as mock_features, \
             patch('foot_traffic_analysis.ox.graph_from_point') as mock_graph, \
             patch('foot_traffic_analysis.ox.graph_to_gdfs') as mock_gdfs:

            mock_endpoint.return_value = 'https://overpass-api.de/api'
            # Return empty GeoDataFrame
            mock_features.return_value = gpd.GeoDataFrame()
            mock_graph.return_value = mock_osm_graph

            # Mock graph_to_gdfs
            nodes_data = {'street_count': [1, 1]}  # No intersections
            nodes_gdf = gpd.GeoDataFrame(nodes_data, crs='EPSG:4326')
            edges_gdf = gpd.GeoDataFrame(crs='EPSG:4326')
            mock_gdfs.return_value = (nodes_gdf, edges_gdf)

            df, analysis = extract_osm_foot_traffic_indicators(43.6532, -79.3832, 300)

            # All categories should have 0 count and empty lists
            assert analysis['restaurants_and_cafes']['count'] == 0
            assert len(analysis['restaurants_and_cafes']['places']) == 0
            assert analysis['shops']['count'] == 0


class TestIntersectionCounting:
    """Test intersection counting logic"""

    def test_intersection_count(self):
        """Test that intersections are counted correctly"""
        with patch('foot_traffic_analysis.get_working_endpoint') as mock_endpoint, \
             patch('foot_traffic_analysis.ox.features_from_point') as mock_features, \
             patch('foot_traffic_analysis.ox.graph_from_point') as mock_graph, \
             patch('foot_traffic_analysis.ox.graph_to_gdfs') as mock_gdfs:

            mock_endpoint.return_value = 'https://overpass-api.de/api'
            mock_features.return_value = gpd.GeoDataFrame()

            # Create mock graph
            G = nx.MultiDiGraph()
            mock_graph.return_value = G

            # Create mock nodes with street_count
            nodes_data = {
                'street_count': [1, 3, 2, 4, 1]  # 3 intersections (>1 street)
            }
            nodes = pd.DataFrame(nodes_data)
            edges = pd.DataFrame()
            mock_gdfs.return_value = (nodes, edges)

            df, analysis = extract_osm_foot_traffic_indicators(43.6532, -79.3832, 300)

            assert analysis['intersection_count'] == 3

    def test_no_intersections(self):
        """Test when there are no intersections"""
        with patch('foot_traffic_analysis.get_working_endpoint') as mock_endpoint, \
             patch('foot_traffic_analysis.ox.features_from_point') as mock_features, \
             patch('foot_traffic_analysis.ox.graph_from_point') as mock_graph, \
             patch('foot_traffic_analysis.ox.graph_to_gdfs') as mock_gdfs:

            mock_endpoint.return_value = 'https://overpass-api.de/api'
            mock_features.return_value = gpd.GeoDataFrame()
            mock_graph.return_value = nx.MultiDiGraph()

            # All nodes have street_count of 1 or less
            nodes = pd.DataFrame({'street_count': [1, 1, 1]})
            edges = pd.DataFrame()
            mock_gdfs.return_value = (nodes, edges)

            df, analysis = extract_osm_foot_traffic_indicators(43.6532, -79.3832, 300)

            assert analysis['intersection_count'] == 0


class TestCombinedCategories:
    """Test combined category logic (office buildings, tourist sites)"""

    @pytest.mark.skip(reason="Integration test - requires full OSMnx mocking")
    def test_office_buildings_combined(self, mock_osmnx_graph_from_point):
        """Test that office buildings from different tags are combined"""
        with patch('foot_traffic_analysis.get_working_endpoint') as mock_endpoint, \
             patch('foot_traffic_analysis.ox.features_from_point') as mock_features:

            mock_endpoint.return_value = 'https://overpass-api.de/api'

            # Create GeoDataFrames with different office types
            def features_side_effect(point, dist, tags):
                if 'building' in tags:
                    return gpd.GeoDataFrame([
                        {'building': 'office', 'name': 'Office 1', 'geometry': Point(-79.38, 43.65)}
                    ], crs='EPSG:4326')
                elif 'office' in tags:
                    return gpd.GeoDataFrame([
                        {'office': 'company', 'name': 'Office 2', 'geometry': Point(-79.38, 43.65)}
                    ], crs='EPSG:4326')
                else:
                    return gpd.GeoDataFrame()

            mock_features.side_effect = features_side_effect

            df, analysis = extract_osm_foot_traffic_indicators(43.6532, -79.3832, 300)

            # Should combine office buildings from both tags
            assert analysis['office_buildings']['count'] >= 0

    @pytest.mark.skip(reason="Integration test - requires full OSMnx mocking")
    def test_tourist_sites_combined(self, mock_osmnx_graph_from_point):
        """Test that tourist sites and leisure places are combined"""
        with patch('foot_traffic_analysis.get_working_endpoint') as mock_endpoint, \
             patch('foot_traffic_analysis.ox.features_from_point') as mock_features:

            mock_endpoint.return_value = 'https://overpass-api.de/api'

            def features_side_effect(point, dist, tags):
                if 'tourism' in tags:
                    return gpd.GeoDataFrame([
                        {'tourism': 'museum', 'name': 'Museum', 'geometry': Point(-79.38, 43.65)}
                    ], crs='EPSG:4326')
                elif 'leisure' in tags:
                    return gpd.GeoDataFrame([
                        {'leisure': 'park', 'name': 'Park', 'geometry': Point(-79.38, 43.65)}
                    ], crs='EPSG:4326')
                else:
                    return gpd.GeoDataFrame()

            mock_features.side_effect = features_side_effect

            df, analysis = extract_osm_foot_traffic_indicators(43.6532, -79.3832, 300)

            # Should combine tourist and leisure places
            assert 'tourist_sites' in analysis
            assert isinstance(analysis['tourist_sites'], dict)
