"""
Unit tests for FHIR Search Lambda function.
"""

import json
import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path
fhir_search_path = Path(__file__).parent.parent / 'src' / 'lambda' / 'fhir_search'
sys.path.insert(0, str(fhir_search_path))

# Import with explicit module reload to avoid conflicts with criteria_parser tests
import importlib
import handler
importlib.reload(handler)


@pytest.fixture
def sample_patient_resource():
    """Sample Patient FHIR resource."""
    return {
        "resourceType": "Patient",
        "id": "patient-001",
        "birthDate": "1979-05-15",
        "gender": "female"
    }


@pytest.fixture
def sample_condition_bundle():
    """Sample Condition search bundle."""
    return {
        "resourceType": "Bundle",
        "total": 1,
        "entry": [
            {
                "resource": {
                    "resourceType": "Condition",
                    "id": "condition-001",
                    "code": {
                        "coding": [{
                            "system": "http://snomed.info/sct",
                            "code": "44054006",
                            "display": "Type 2 Diabetes Mellitus"
                        }],
                        "text": "Type 2 Diabetes Mellitus"
                    },
                    "clinicalStatus": {
                        "coding": [{
                            "code": "active"
                        }]
                    }
                }
            }
        ]
    }


class TestFHIRSearch:
    """Test cases for FHIR search."""

    def test_calculate_age(self):
        """Test age calculation."""
        age = handler.calculate_age("1979-05-15")
        # Age should be around 45 (as of 2024)
        assert 44 <= age <= 46

    def test_check_demographic_criterion_age_between(self, sample_patient_resource):
        """Test checking age criterion with between operator."""
        criterion = {
            "attribute": "age",
            "operator": "between",
            "value": [18, 65]
        }

        result = handler.check_demographic_criterion(sample_patient_resource, criterion)

        assert result['met'] is True
        assert 'age' in result['reason']

    def test_check_demographic_criterion_age_too_young(self, sample_patient_resource):
        """Test checking age criterion when patient is too young."""
        # Modify patient to be born in 2010
        patient = sample_patient_resource.copy()
        patient['birthDate'] = "2010-03-20"

        criterion = {
            "attribute": "age",
            "operator": "between",
            "value": [18, 65]
        }

        result = handler.check_demographic_criterion(patient, criterion)

        assert result['met'] is False

    def test_check_demographic_criterion_gender(self, sample_patient_resource):
        """Test checking gender criterion."""
        criterion = {
            "attribute": "gender",
            "operator": "equals",
            "value": "female"
        }

        result = handler.check_demographic_criterion(sample_patient_resource, criterion)

        assert result['met'] is True

    @patch('handler.query_fhir_resource')
    def test_check_condition_criterion_has_condition(self, mock_query, sample_condition_bundle):
        """Test checking condition criterion when patient has the condition."""
        mock_query.return_value = sample_condition_bundle

        criterion = {
            "operator": "contains",
            "value": "diabetes"
        }

        result = handler.check_condition_criterion("patient-001", criterion)

        assert result['met'] is True
        assert result['evidence']['condition_count'] == 1

    @patch('handler.query_fhir_resource')
    def test_check_condition_criterion_no_condition(self, mock_query):
        """Test checking condition criterion when patient doesn't have it."""
        mock_query.return_value = {"resourceType": "Bundle", "total": 0}

        criterion = {
            "operator": "not_contains",
            "value": "chronic kidney disease"
        }

        result = handler.check_condition_criterion("patient-001", criterion)

        assert result['met'] is True  # not_contains should be True when no conditions found

    @patch('handler.get_patient_resource')
    @patch('handler.query_fhir_resource')
    def test_lambda_handler_success(self, mock_query, mock_get_patient, sample_patient_resource, sample_condition_bundle):
        """Test successful lambda handler execution."""
        mock_get_patient.return_value = sample_patient_resource
        mock_query.return_value = sample_condition_bundle

        event = {
            'body': json.dumps({
                'patient_id': 'patient-001',
                'criteria': [
                    {
                        "type": "inclusion",
                        "category": "demographics",
                        "description": "Age 18-65",
                        "attribute": "age",
                        "operator": "between",
                        "value": [18, 65]
                    },
                    {
                        "type": "inclusion",
                        "category": "condition",
                        "description": "Type 2 Diabetes",
                        "attribute": "diabetes",
                        "operator": "contains",
                        "value": "diabetes"
                    }
                ]
            })
        }

        context = Mock()

        response = handler.lambda_handler(event, context)

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['patient_id'] == 'patient-001'
        assert body['eligible'] is True
        assert len(body['results']) == 2

    def test_lambda_handler_missing_patient_id(self):
        """Test lambda handler with missing patient_id."""
        event = {
            'body': json.dumps({
                'criteria': []
            })
        }

        context = Mock()

        response = handler.lambda_handler(event, context)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
