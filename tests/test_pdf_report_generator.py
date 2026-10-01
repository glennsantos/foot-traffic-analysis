"""
Unit tests for pdf_report_generator.py module
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from reportlab.lib import colors

from pdf_report_generator import LocationViabilityReportGenerator


class TestReportGeneratorInitialization:
    """Test report generator initialization"""

    def test_initialization(self):
        """Test that report generator initializes correctly"""
        generator = LocationViabilityReportGenerator()
        assert generator is not None
        assert hasattr(generator, 'styles')
        assert hasattr(generator, 'criteria')
        assert len(generator.criteria) == 12

    def test_criteria_structure(self):
        """Test that all criteria have required fields"""
        generator = LocationViabilityReportGenerator()
        required_fields = ['threshold', 'weight', 'description']

        for indicator, criteria in generator.criteria.items():
            for field in required_fields:
                assert field in criteria, f"{indicator} missing {field}"

    def test_weights_sum_to_one(self):
        """Test that all weights sum to approximately 1.0"""
        generator = LocationViabilityReportGenerator()
        total_weight = sum(criteria['weight'] for criteria in generator.criteria.values())
        assert abs(total_weight - 1.0) < 0.01, f"Weights sum to {total_weight}, expected 1.0"

    def test_custom_styles_created(self):
        """Test that custom styles are created"""
        generator = LocationViabilityReportGenerator()
        assert hasattr(generator, 'title_style')
        assert hasattr(generator, 'heading_style')
        assert hasattr(generator, 'summary_style')


class TestIndicatorScoreCalculation:
    """Test indicator scoring logic"""

    def test_score_meeting_threshold(self):
        """Test score when count meets threshold"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {'shops': 10}  # Threshold is 8
        scores = generator.calculate_indicator_scores(analysis_data)

        shop_score = next(s for s in scores if s['indicator'] == 'shops')
        assert shop_score['base_score'] == 100
        assert shop_score['meets_criteria'] is True

    def test_score_below_threshold(self):
        """Test score when count is below threshold"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {'shops': 4}  # Threshold is 8
        scores = generator.calculate_indicator_scores(analysis_data)

        shop_score = next(s for s in scores if s['indicator'] == 'shops')
        assert shop_score['base_score'] == 50.0  # 4/8 * 100
        assert shop_score['meets_criteria'] is False

    def test_score_exceeding_threshold_double(self):
        """Test bonus score when count exceeds threshold by 2x"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {'shops': 20}  # Threshold is 8, 20 > 16
        scores = generator.calculate_indicator_scores(analysis_data)

        shop_score = next(s for s in scores if s['indicator'] == 'shops')
        assert shop_score['base_score'] == 120  # 100 + 20 bonus

    def test_score_with_dict_data(self):
        """Test scoring with dict format (count and places)"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {
            'shops': {
                'count': 10,
                'places': ['Shop 1', 'Shop 2']
            }
        }
        scores = generator.calculate_indicator_scores(analysis_data)

        shop_score = next(s for s in scores if s['indicator'] == 'shops')
        assert shop_score['count'] == 10
        assert shop_score['places'] == ['Shop 1', 'Shop 2']

    def test_weighted_score_calculation(self):
        """Test that weighted scores are calculated correctly"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {'shops': 8}  # Exactly at threshold
        scores = generator.calculate_indicator_scores(analysis_data)

        shop_score = next(s for s in scores if s['indicator'] == 'shops')
        expected_weighted = 100 * 0.17  # base_score * weight
        assert abs(shop_score['weighted_score'] - expected_weighted) < 0.01

    def test_scores_sorted_by_weighted_score(self):
        """Test that scores are sorted by weighted score descending"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {
            'shops': 20,  # High count, high weight
            'tourist_sites': 10,  # High count, low weight
            'restaurants_and_cafes': 4  # At threshold, medium weight
        }
        scores = generator.calculate_indicator_scores(analysis_data)

        # Check that scores are in descending order
        for i in range(len(scores) - 1):
            assert scores[i]['weighted_score'] >= scores[i + 1]['weighted_score']

    def test_zero_count(self):
        """Test scoring with zero count"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {'shops': 0}
        scores = generator.calculate_indicator_scores(analysis_data)

        shop_score = next(s for s in scores if s['indicator'] == 'shops')
        assert shop_score['base_score'] == 0
        assert shop_score['weighted_score'] == 0
        assert shop_score['meets_criteria'] is False

    def test_all_indicators_included(self):
        """Test that all 12 indicators are scored"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {
            'restaurants_and_cafes': 5,
            'shops': 10,
            'intersection_count': 20,
            'office_buildings': 3,
            'schools_universities': 2,
            'transport_hubs': 3,
            'hospitals_clinics': 1,
            'parking_lots': 2,
            'pedestrian_crossings': 5,
            'markets': 1,
            'tourist_sites': 2,
            'places_of_worship': 2
        }
        scores = generator.calculate_indicator_scores(analysis_data)
        assert len(scores) == 12


class TestViabilityCalculation:
    """Test overall viability calculation"""

    def test_perfect_score(self):
        """Test viability with all indicators at max"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {indicator: 100 for indicator in generator.criteria.keys()}
        scores = generator.calculate_indicator_scores(analysis_data)
        viability, rating, color = generator.calculate_overall_viability(scores)

        assert viability >= 100  # Can exceed 100 due to bonuses
        assert rating == "BEST"
        assert color == colors.darkgreen

    def test_best_rating(self):
        """Test BEST rating threshold (98%+)"""
        generator = LocationViabilityReportGenerator()
        # Create a score set that gives exactly 98%
        scores = [
            {'weighted_score': 98 * criteria['weight'], 'indicator': indicator}
            for indicator, criteria in generator.criteria.items()
        ]
        viability, rating, color = generator.calculate_overall_viability(scores)

        assert viability >= 98
        assert rating == "BEST"

    def test_outstanding_rating(self):
        """Test OUTSTANDING rating (95-97%)"""
        generator = LocationViabilityReportGenerator()
        scores = [
            {'weighted_score': 96 * criteria['weight'], 'indicator': indicator}
            for indicator, criteria in generator.criteria.items()
        ]
        viability, rating, color = generator.calculate_overall_viability(scores)

        assert 95 <= viability < 98
        assert rating == "OUTSTANDING"
        assert color == colors.green

    def test_excellent_rating(self):
        """Test EXCELLENT rating (85-94%)"""
        generator = LocationViabilityReportGenerator()
        scores = [
            {'weighted_score': 90 * criteria['weight'], 'indicator': indicator}
            for indicator, criteria in generator.criteria.items()
        ]
        viability, rating, color = generator.calculate_overall_viability(scores)

        assert 85 <= viability < 95
        assert rating == "EXCELLENT"
        assert color == colors.blue

    def test_good_rating(self):
        """Test GOOD rating (80-89%)"""
        generator = LocationViabilityReportGenerator()
        scores = [
            {'weighted_score': 85 * criteria['weight'], 'indicator': indicator}
            for indicator, criteria in generator.criteria.items()
        ]
        viability, rating, color = generator.calculate_overall_viability(scores)

        assert 80 <= viability < 95
        assert rating in ["GOOD", "EXCELLENT"]

    def test_moderate_rating(self):
        """Test MODERATE rating (70-79%)"""
        generator = LocationViabilityReportGenerator()
        scores = [
            {'weighted_score': 75 * criteria['weight'], 'indicator': indicator}
            for indicator, criteria in generator.criteria.items()
        ]
        viability, rating, color = generator.calculate_overall_viability(scores)

        assert 70 <= viability < 80
        assert rating == "MODERATE"
        assert color == colors.orange

    def test_poor_rating(self):
        """Test POOR rating (<70%)"""
        generator = LocationViabilityReportGenerator()
        scores = [
            {'weighted_score': 50 * criteria['weight'], 'indicator': indicator}
            for indicator, criteria in generator.criteria.items()
        ]
        viability, rating, color = generator.calculate_overall_viability(scores)

        assert viability < 70
        assert rating == "POOR"
        assert color == colors.red


class TestIndicatorNameFormatting:
    """Test indicator name formatting"""

    def test_format_underscore_to_space(self):
        """Test that underscores are replaced with spaces"""
        generator = LocationViabilityReportGenerator()
        formatted = generator.format_indicator_name('restaurants_and_cafes')
        assert '_' not in formatted
        assert ' ' in formatted

    def test_format_title_case(self):
        """Test that names are converted to title case"""
        generator = LocationViabilityReportGenerator()
        formatted = generator.format_indicator_name('restaurants_and_cafes')
        assert formatted == 'Restaurants And Cafes'

    def test_format_various_names(self):
        """Test formatting of various indicator names"""
        generator = LocationViabilityReportGenerator()
        test_cases = {
            'shops': 'Shops',
            'intersection_count': 'Intersection Count',
            'places_of_worship': 'Places Of Worship',
            'transport_hubs': 'Transport Hubs'
        }

        for input_name, expected in test_cases.items():
            assert generator.format_indicator_name(input_name) == expected


class TestSummaryGeneration:
    """Test executive summary generation"""

    def test_summary_includes_location(self):
        """Test that summary includes location information"""
        generator = LocationViabilityReportGenerator()
        scores = generator.calculate_indicator_scores({'shops': 10})
        viability, rating, _ = generator.calculate_overall_viability(scores)

        summary = generator.generate_summary(
            'Toronto, Canada', 43.6532, -79.3832, 300,
            viability, rating, scores
        )

        assert 'Toronto, Canada' in summary
        assert '43.6532' in summary
        assert '-79.3832' in summary
        assert '300m' in summary

    def test_summary_includes_viability(self):
        """Test that summary includes viability score and rating"""
        generator = LocationViabilityReportGenerator()
        scores = generator.calculate_indicator_scores({'shops': 10})
        viability, rating, _ = generator.calculate_overall_viability(scores)

        summary = generator.generate_summary(
            'Test Location', 43.6532, -79.3832, 300,
            viability, rating, scores
        )

        assert rating in summary
        assert f"{viability:.1f}%" in summary

    def test_summary_includes_criteria_met(self):
        """Test that summary shows criteria met count"""
        generator = LocationViabilityReportGenerator()
        scores = generator.calculate_indicator_scores({'shops': 10, 'restaurants_and_cafes': 5})
        viability, rating, _ = generator.calculate_overall_viability(scores)

        summary = generator.generate_summary(
            'Test Location', 43.6532, -79.3832, 300,
            viability, rating, scores
        )

        assert 'Criteria Met:' in summary

    def test_summary_high_viability_recommendation(self):
        """Test recommendation for high viability (>=85%)"""
        generator = LocationViabilityReportGenerator()
        # Create high-scoring data
        analysis_data = {indicator: 100 for indicator in generator.criteria.keys()}
        scores = generator.calculate_indicator_scores(analysis_data)
        viability, rating, _ = generator.calculate_overall_viability(scores)

        summary = generator.generate_summary(
            'Test Location', 43.6532, -79.3832, 300,
            viability, rating, scores
        )

        assert 'Highly suitable' in summary or 'suitable' in summary.lower()

    def test_summary_low_viability_recommendation(self):
        """Test recommendation for low viability (<70%)"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {indicator: 1 for indicator in generator.criteria.keys()}
        scores = generator.calculate_indicator_scores(analysis_data)
        viability, rating, _ = generator.calculate_overall_viability(scores)

        summary = generator.generate_summary(
            'Test Location', 43.6532, -79.3832, 300,
            viability, rating, scores
        )

        assert 'alternative' in summary.lower() or 'consider' in summary.lower()


class TestConclusionGeneration:
    """Test conclusion and recommendations generation"""

    def test_conclusion_includes_score(self):
        """Test that conclusion includes viability score"""
        generator = LocationViabilityReportGenerator()
        scores = generator.calculate_indicator_scores({'shops': 10})
        viability, rating, _ = generator.calculate_overall_viability(scores)

        conclusion = generator.generate_conclusion(viability, rating, scores)

        assert f"{viability:.1f}%" in conclusion
        assert rating in conclusion

    def test_conclusion_best_rating(self):
        """Test conclusion for BEST/OUTSTANDING rating (>=95%)"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {indicator: 100 for indicator in generator.criteria.keys()}
        scores = generator.calculate_indicator_scores(analysis_data)
        viability, rating, _ = generator.calculate_overall_viability(scores)

        conclusion = generator.generate_conclusion(viability, rating, scores)

        assert 'outstanding' in conclusion.lower() or 'best' in conclusion.lower()
        assert 'premium' in conclusion.lower()

    def test_conclusion_excellent_rating(self):
        """Test conclusion for EXCELLENT rating (85-94%)"""
        generator = LocationViabilityReportGenerator()
        scores = [
            {'weighted_score': 90 * criteria['weight'], 'indicator': indicator,
             'meets_criteria': True, 'count': 10, 'base_score': 90, 'threshold': 5}
            for indicator, criteria in generator.criteria.items()
        ]
        viability = 90.0
        rating = "EXCELLENT"

        conclusion = generator.generate_conclusion(viability, rating, scores)

        assert 'excellent' in conclusion.lower()

    def test_conclusion_poor_rating(self):
        """Test conclusion for POOR rating (<70%)"""
        generator = LocationViabilityReportGenerator()
        scores = [
            {'weighted_score': 50 * criteria['weight'], 'indicator': indicator,
             'meets_criteria': False, 'count': 1, 'base_score': 50, 'threshold': 10}
            for indicator, criteria in generator.criteria.items()
        ]
        viability = 50.0
        rating = "POOR"

        conclusion = generator.generate_conclusion(viability, rating, scores)

        assert 'poor' in conclusion.lower()
        assert 'alternative' in conclusion.lower() or 'consider' in conclusion.lower()

    def test_conclusion_includes_top_strengths(self):
        """Test that conclusion includes top 3 strengths"""
        generator = LocationViabilityReportGenerator()
        scores = generator.calculate_indicator_scores({
            'shops': 20,
            'restaurants_and_cafes': 15,
            'intersection_count': 25
        })
        viability, rating, _ = generator.calculate_overall_viability(scores)

        conclusion = generator.generate_conclusion(viability, rating, scores)

        assert 'Key Strengths:' in conclusion

    def test_conclusion_includes_improvements(self):
        """Test that conclusion includes areas for improvement"""
        generator = LocationViabilityReportGenerator()
        scores = generator.calculate_indicator_scores({
            'shops': 2,  # Below threshold
            'restaurants_and_cafes': 1  # Below threshold
        })
        viability, rating, _ = generator.calculate_overall_viability(scores)

        conclusion = generator.generate_conclusion(viability, rating, scores)

        assert 'Areas for Improvement:' in conclusion or 'improvement' in conclusion.lower()


class TestTableCreation:
    """Test table creation methods"""

    def test_create_indicators_table(self):
        """Test creation of indicators table"""
        generator = LocationViabilityReportGenerator()
        scores = generator.calculate_indicator_scores({
            'shops': 10,
            'restaurants_and_cafes': 5
        })

        table = generator.create_indicators_table(scores)

        assert table is not None
        # Table should have header + score rows
        assert len(table._cellvalues) > 0

    def test_create_places_table_with_data(self):
        """Test creation of places table with valid data"""
        generator = LocationViabilityReportGenerator()
        places_data = [
            {'name': 'Place 1', 'latitude': 43.6532, 'longitude': -79.3832, 'address': '100 Queen St'},
            {'name': 'Place 2', 'latitude': 43.6533, 'longitude': -79.3833, 'address': '101 Queen St'}
        ]

        table = generator.create_places_table('Test Places', places_data)

        assert table is not None
        assert len(table._cellvalues) == 3  # Header + 2 rows

    def test_create_places_table_empty(self):
        """Test creation of places table with no data"""
        generator = LocationViabilityReportGenerator()

        table = generator.create_places_table('Test Places', [])

        assert table is None

    def test_create_places_table_none(self):
        """Test creation of places table with None"""
        generator = LocationViabilityReportGenerator()

        table = generator.create_places_table('Test Places', None)

        assert table is None

    def test_create_places_table_limit(self):
        """Test that places table limits to 20 entries"""
        generator = LocationViabilityReportGenerator()
        places_data = [
            {'name': f'Place {i}', 'latitude': 43.65 + i*0.001,
             'longitude': -79.38 + i*0.001, 'address': f'{i} Street'}
            for i in range(50)
        ]

        table = generator.create_places_table('Test Places', places_data)

        # Should have header + 20 rows (limited)
        assert len(table._cellvalues) == 21

    def test_create_places_table_long_names(self):
        """Keep full place names available for wrapping in the report."""
        generator = LocationViabilityReportGenerator()
        long_name = 'A' * 50  # 50 characters
        places_data = [
            {'name': long_name, 'latitude': 43.6532,
             'longitude': -79.3832, 'address': '100 Queen St'}
        ]

        table = generator.create_places_table('Test Places', places_data)

        # Full names should survive the table conversion.
        assert len(table._cellvalues) == 2
        cell_value = table._cellvalues[1][0]
        assert cell_value.getPlainText() == long_name


class TestPDFReportGeneration:
    """Test complete PDF report generation"""

    def test_generate_report_creates_file(self, mock_analysis_results, tmp_path):
        """Test that report generation creates a PDF file"""
        generator = LocationViabilityReportGenerator()
        output_path = tmp_path / "test_report.pdf"

        result = generator.generate_report(
            mock_analysis_results,
            'Toronto, Canada',
            43.6532, -79.3832, 300,
            str(output_path)
        )

        assert output_path.exists()
        assert result is not None
        assert 'viability_percentage' in result
        assert 'rating' in result
        assert 'summary' in result
        assert 'scores' in result

    def test_generate_report_return_values(self, mock_analysis_results, tmp_path):
        """Test that generate_report returns correct structure"""
        generator = LocationViabilityReportGenerator()
        output_path = tmp_path / "test_report.pdf"

        result = generator.generate_report(
            mock_analysis_results,
            'Toronto, Canada',
            43.6532, -79.3832, 300,
            str(output_path)
        )

        assert isinstance(result['viability_percentage'], (int, float))
        assert isinstance(result['rating'], str)
        assert isinstance(result['summary'], str)
        assert isinstance(result['scores'], list)

    def test_generate_report_with_minimal_data(self, tmp_path):
        """Test report generation with minimal data"""
        generator = LocationViabilityReportGenerator()
        output_path = tmp_path / "test_report.pdf"

        minimal_data = {indicator: 0 for indicator in generator.criteria.keys()}

        result = generator.generate_report(
            minimal_data,
            'Test Location',
            0.0, 0.0, 300,
            str(output_path)
        )

        assert output_path.exists()
        assert result['rating'] == 'POOR'

    def test_generate_report_with_maximum_data(self, tmp_path):
        """Test report generation with maximum data"""
        generator = LocationViabilityReportGenerator()
        output_path = tmp_path / "test_report.pdf"

        max_data = {
            indicator: {'count': 1000, 'places': [f'Place {i}' for i in range(10)],
                       'detailed_places': [{'name': f'Place {i}', 'latitude': 43.65,
                                          'longitude': -79.38, 'address': f'{i} St'}
                                         for i in range(10)]}
            for indicator in generator.criteria.keys()
        }

        result = generator.generate_report(
            max_data,
            'Premium Location',
            43.6532, -79.3832, 300,
            str(output_path)
        )

        assert output_path.exists()
        assert result['rating'] in ['BEST', 'OUTSTANDING']

    def test_generate_report_with_detailed_places(self, tmp_path):
        """Test report generation includes detailed places"""
        generator = LocationViabilityReportGenerator()
        output_path = tmp_path / "test_report.pdf"

        analysis_data = {
            'shops': {
                'count': 10,
                'places': ['Shop 1', 'Shop 2'],
                'detailed_places': [
                    {'name': 'Shop 1', 'latitude': 43.6532, 'longitude': -79.3832, 'address': '100 Queen St'},
                    {'name': 'Shop 2', 'latitude': 43.6533, 'longitude': -79.3833, 'address': '101 Queen St'}
                ]
            }
        }

        result = generator.generate_report(
            analysis_data,
            'Test Location',
            43.6532, -79.3832, 300,
            str(output_path)
        )

        assert output_path.exists()
        # Check that detailed places are included in the analysis
        shop_score = next((s for s in result['scores'] if s['indicator'] == 'shops'), None)
        assert shop_score is not None
        assert shop_score['count'] == 10


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_analysis_data(self):
        """Test with empty analysis data"""
        generator = LocationViabilityReportGenerator()
        scores = generator.calculate_indicator_scores({})
        assert len(scores) == 0

    def test_unknown_indicator(self):
        """Test with unknown indicator (should be ignored)"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {'unknown_indicator': 100, 'shops': 10}
        scores = generator.calculate_indicator_scores(analysis_data)

        # Should only score 'shops', not 'unknown_indicator'
        assert all(s['indicator'] != 'unknown_indicator' for s in scores)

    def test_negative_count(self):
        """Test handling of negative counts (should work but give 0 score)"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {'shops': -5}
        scores = generator.calculate_indicator_scores(analysis_data)

        shop_score = next(s for s in scores if s['indicator'] == 'shops')
        assert shop_score['base_score'] <= 0
        assert shop_score['meets_criteria'] is False

    def test_none_places(self):
        """Test handling of None in places data"""
        generator = LocationViabilityReportGenerator()
        analysis_data = {
            'shops': {
                'count': 5,
                'places': None
            }
        }
        scores = generator.calculate_indicator_scores(analysis_data)

        shop_score = next(s for s in scores if s['indicator'] == 'shops')
        assert shop_score['places'] is None
