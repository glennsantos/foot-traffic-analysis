# Testing Documentation

## Comprehensive Test Suite for Foot Traffic Analysis Tool

This document describes the comprehensive test suite created for the Foot Traffic Analysis Tool.

---

## Table of Contents

1. [Overview](#overview)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Coverage](#test-coverage)
5. [Test Categories](#test-categories)
6. [Writing New Tests](#writing-new-tests)
7. [Continuous Integration](#continuous-integration)

---

## Overview

The test suite provides comprehensive coverage of all major functionalities in the Foot Traffic Analysis Tool:

- **Unit Tests**: Test individual functions and components in isolation
- **Integration Tests**: Test complete workflows and interactions between components
- **API Tests**: Test all Flask API endpoints
- **Edge Cases**: Test error handling and boundary conditions

### Test Statistics

- **Total Test Files**: 5
- **Total Test Cases**: 100+
- **Code Coverage Target**: >80%
- **Modules Tested**: 4 (app.py, foot_traffic_analysis.py, pdf_report_generator.py, scripts/package.py)

---

## Test Structure

```
tests/
├── __init__.py                     # Test package initialization
├── conftest.py                     # Shared fixtures and test configuration
├── test_foot_traffic_analysis.py   # Tests for OSM data extraction
├── test_pdf_report_generator.py    # Tests for PDF report generation
├── test_app.py                     # Tests for Flask application
└── test_integration.py             # End-to-end integration tests
```

### Test Files

#### `conftest.py`
Shared pytest fixtures and configuration:
- Flask test client
- Mock OSM data (graphs, places, GeoDataFrames)
- Mock API responses (Nominatim, Overpass)
- Sample analysis results
- Test coordinates and data

#### `test_foot_traffic_analysis.py`
Tests for `foot_traffic_analysis.py` module:
- Overpass endpoint parsing and normalization
- URL validation and status checking
- Endpoint selection and failover
- OSM data extraction with retry logic
- Place data extraction and formatting
- Intersection counting
- Combined categories (office buildings, tourist sites)
- Error handling and edge cases

**Test Classes:**
- `TestOverpassEndpointParsing` (6 tests)
- `TestURLNormalization` (5 tests)
- `TestStatusURL` (3 tests)
- `TestOverpassEndpointTesting` (5 tests)
- `TestWorkingEndpoint` (4 tests)
- `TestOSMDataExtraction` (6 tests)
- `TestPlaceDataExtraction` (3 tests)
- `TestIntersectionCounting` (2 tests)
- `TestCombinedCategories` (2 tests)

#### `test_pdf_report_generator.py`
Tests for `pdf_report_generator.py` module:
- Report generator initialization
- Criteria structure and weights
- Indicator score calculation
- Overall viability calculation and ratings
- Indicator name formatting
- Executive summary generation
- Conclusion and recommendations
- Table creation (indicators and places)
- Complete PDF report generation
- Edge cases and error handling

**Test Classes:**
- `TestReportGeneratorInitialization` (4 tests)
- `TestIndicatorScoreCalculation` (9 tests)
- `TestViabilityCalculation` (7 tests)
- `TestIndicatorNameFormatting` (3 tests)
- `TestSummaryGeneration` (5 tests)
- `TestConclusionGeneration` (5 tests)
- `TestTableCreation` (6 tests)
- `TestPDFReportGeneration` (6 tests)
- `TestEdgeCases` (4 tests)

#### `test_app.py`
Tests for `app.py` Flask application:
- App configuration
- Nominatim header generation
- Client IP extraction
- JSON serialization helpers
- Location name geocoding
- Index route
- Health check endpoint
- Last search retrieval
- Report download
- Analysis endpoint
- Directory creation
- Error handling

**Test Classes:**
- `TestAppConfiguration` (3 tests)
- `TestNominatimHeaders` (3 tests)
- `TestClientIP` (3 tests)
- `TestJSONSerialization` (10 tests)
- `TestLocationName` (4 tests)
- `TestIndexRoute` (2 tests)
- `TestHealthCheckRoute` (3 tests)
- `TestLastSearchRoute` (2 tests)
- `TestDownloadReportRoute` (3 tests)
- `TestAnalyzeRoute` (11 tests)
- `TestDirectoryCreation` (1 test)
- `TestErrorHandling` (1 test)

#### `test_integration.py`
End-to-end integration tests:
- Complete analysis workflow
- API endpoint integration
- Data flow between components
- Error propagation
- Concurrent requests
- Different radius values
- File generation and structure

**Test Classes:**
- `TestEndToEndAnalysis` (2 tests)
- `TestAPIEndpointIntegration` (2 tests)
- `TestDataFlowIntegration` (2 tests)
- `TestErrorPropagation` (2 tests)
- `TestConcurrentRequests` (1 test)
- `TestDifferentRadii` (1 test)
- `TestFileGeneration` (2 tests)

---

## Running Tests

### Prerequisites

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

Or using the Makefile:

```bash
make -f Makefile.tests install-test
```

### Run All Tests

```bash
pytest
```

Or with coverage:

```bash
pytest --cov=. --cov-report=html --cov-report=term-missing
```

Or using the Makefile:

```bash
make -f Makefile.tests test
```

### Run Specific Test Files

```bash
# Test only foot traffic analysis
pytest tests/test_foot_traffic_analysis.py -v

# Test only PDF generation
pytest tests/test_pdf_report_generator.py -v

# Test only Flask app
pytest tests/test_app.py -v

# Test only integration tests
pytest tests/test_integration.py -v
```

### Run Specific Test Classes

```bash
pytest tests/test_app.py::TestAnalyzeRoute -v
```

### Run Specific Tests

```bash
pytest tests/test_app.py::TestAnalyzeRoute::test_analyze_success -v
```

### Run Tests by Pattern

```bash
# Run all tests with "analyze" in the name
pytest -k analyze -v

# Run all tests except integration tests
pytest -k "not integration" -v
```

### Quick Test Run (No Coverage)

```bash
make -f Makefile.tests test-quick
```

### Verbose Output

```bash
make -f Makefile.tests test-verbose
```

---

## Test Coverage

### Generate Coverage Report

```bash
make -f Makefile.tests test-coverage
```

This generates:
- **HTML Report**: `htmlcov/index.html` (open in browser)
- **Terminal Report**: Shows missing lines
- **XML Report**: `coverage.xml` (for CI/CD)

### View Coverage Report

```bash
# Open HTML coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage Targets

| Module | Target Coverage | Current Coverage |
|--------|----------------|------------------|
| `app.py` | >80% | TBD |
| `foot_traffic_analysis.py` | >80% | TBD |
| `pdf_report_generator.py` | >80% | TBD |
| **Overall** | >80% | TBD |

---

## Test Categories

### Unit Tests

Test individual functions in isolation with mocked dependencies.

**Examples:**
- URL normalization: `test_normalize_base_url()`
- Score calculation: `test_score_meeting_threshold()`
- JSON serialization: `test_to_json_safe_numpy_int()`

### Integration Tests

Test complete workflows and interactions between components.

**Examples:**
- End-to-end analysis: `test_complete_analysis_workflow()`
- API chaining: `test_analyze_then_last_search()`
- Data flow: `test_osm_data_to_pdf_report()`

### API Tests

Test Flask API endpoints with various inputs and scenarios.

**Examples:**
- Analysis endpoint: `test_analyze_success()`
- Download endpoint: `test_download_report_success()`
- Health check: `test_healthz_returns_200()`

### Edge Case Tests

Test error handling, boundary conditions, and unusual inputs.

**Examples:**
- Invalid coordinates: `test_invalid_coordinates()`
- Empty results: `test_workflow_with_empty_results()`
- API failures: `test_all_retries_fail()`

---

## Writing New Tests

### Test Structure Template

```python
class TestMyFeature:
    """Test my new feature"""

    def test_basic_functionality(self):
        """Test basic functionality works"""
        # Arrange
        input_data = {...}
        expected_output = {...}

        # Act
        result = my_function(input_data)

        # Assert
        assert result == expected_output

    def test_error_handling(self):
        """Test error handling"""
        with pytest.raises(ValueError):
            my_function(invalid_input)

    def test_with_mock(self, mocker):
        """Test with mocked dependencies"""
        mock_api = mocker.patch('module.external_api')
        mock_api.return_value = {'data': 'test'}

        result = my_function()

        assert mock_api.called
        assert result is not None
```

### Using Fixtures

```python
def test_with_fixture(test_client, mock_osm_places):
    """Test using shared fixtures from conftest.py"""
    # test_client and mock_osm_places are automatically injected
    response = test_client.get('/api/endpoint')
    assert response.status_code == 200
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    (0, "POOR"),
    (50, "POOR"),
    (75, "MODERATE"),
    (85, "EXCELLENT"),
    (98, "BEST"),
])
def test_viability_ratings(input, expected):
    """Test different viability ratings"""
    rating = get_rating(input)
    assert rating == expected
```

---

## Continuous Integration

### GitHub Actions (Recommended)

Create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'

    - name: Install dependencies
      run: |
        pip install -r requirements-dev.txt

    - name: Run tests
      run: |
        pytest --cov=. --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v2
      with:
        file: ./coverage.xml
```

### Local Pre-commit Hook

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Run tests before commit

echo "Running tests..."
pytest tests/ -q

if [ $? -ne 0 ]; then
    echo "Tests failed! Commit aborted."
    exit 1
fi

echo "All tests passed!"
```

Make it executable:

```bash
chmod +x .git/hooks/pre-commit
```

---

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'app'`

**Solution**: Ensure you're running pytest from the project root directory.

---

**Issue**: Tests fail due to missing dependencies

**Solution**:
```bash
pip install -r requirements-dev.txt
```

---

**Issue**: Permission denied when creating files

**Solution**: Ensure test directories exist and have write permissions:
```bash
mkdir -p reports analyses_new
chmod 755 reports analyses_new
```

---

**Issue**: Coverage report not generating

**Solution**: Install coverage tools:
```bash
pip install pytest-cov coverage
```

---

## Best Practices

1. **Write tests first** (TDD): Write failing tests before implementing features
2. **Test one thing**: Each test should verify a single behavior
3. **Use descriptive names**: Test names should describe what they test
4. **Mock external dependencies**: Don't rely on external APIs in tests
5. **Clean up after tests**: Remove created files, reset state
6. **Keep tests fast**: Unit tests should run in milliseconds
7. **Test edge cases**: Test boundary conditions and error scenarios
8. **Maintain fixtures**: Keep conftest.py organized and documented
9. **Aim for high coverage**: Target >80% code coverage
10. **Review test output**: Understand why tests pass or fail

---

## Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Python Testing Best Practices](https://realpython.com/pytest-python-testing/)
- [Mocking in Python](https://docs.python.org/3/library/unittest.mock.html)

---

## Contact

For questions about the test suite, please contact the development team or open an issue in the project repository.
