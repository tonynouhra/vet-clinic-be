import pytest
from tests.dynamic.decorators import feature_test
from tests.dynamic.data_factory import TestDataFactory

class TestDebug:
    @pytest.fixture
    def test_data_factory(self):
        return TestDataFactory()
    
    @feature_test("health_records")
    def test_simple(self, test_data_factory):
        print(f"Test Data Factory: {test_data_factory}")
        # api_version should be available somehow
        assert True