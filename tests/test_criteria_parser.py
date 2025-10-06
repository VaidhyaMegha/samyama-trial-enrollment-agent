"""
Unit tests for Criteria Parser Lambda function.
"""

import json
import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src' / 'lambda' / 'criteria_parser'))

import handler


@pytest.fixture
def sample_criteria_text():
    """Sample trial criteria text."""
    return """
    Inclusion Criteria:
    - Patients must be between 18 and 65 years old
    - Diagnosis of Type 2 Diabetes Mellitus
    - HbA1c between 7% and 10%

    Exclusion Criteria:
    - Chronic kidney disease stage 4 or higher
    - Pregnant or breastfeeding
    """


@pytest.fixture
def mock_bedrock_response():
    """Mock Bedrock response."""
    return {
        'body': Mock(read=lambda: json.dumps({
            'content': [{
                'text': json.dumps([
                    {
                        "type": "inclusion",
                        "category": "demographics",
                        "description": "Age between 18 and 65 years",
                        "attribute": "age",
                        "operator": "between",
                        "value": [18, 65],
                        "unit": "years",
                        "fhir_resource": "Patient",
                        "fhir_path": "Patient.birthDate"
                    },
                    {
                        "type": "inclusion",
                        "category": "condition",
                        "description": "Type 2 Diabetes Mellitus",
                        "attribute": "diabetes",
                        "operator": "contains",
                        "value": "Type 2 Diabetes Mellitus",
                        "fhir_resource": "Condition",
                        "fhir_path": "Condition.code"
                    }
                ])
            }]
        }).encode())
    }


class TestCriteriaParser:
    """Test cases for criteria parser."""

    def test_validate_criterion_valid(self):
        """Test validation of a valid criterion."""
        criterion = {
            "type": "inclusion",
            "category": "demographics",
            "description": "Age between 18 and 65",
            "attribute": "age",
            "operator": "between",
            "value": [18, 65]
        }

        assert handler.validate_criterion(criterion) is True

    def test_validate_criterion_missing_field(self):
        """Test validation fails with missing field."""
        criterion = {
            "type": "inclusion",
            "category": "demographics",
            # Missing description
            "attribute": "age",
            "operator": "between",
            "value": [18, 65]
        }

        with pytest.raises(ValueError, match="Missing required field"):
            handler.validate_criterion(criterion)

    def test_validate_criterion_invalid_type(self):
        """Test validation fails with invalid type."""
        criterion = {
            "type": "invalid_type",
            "category": "demographics",
            "description": "Age test",
            "attribute": "age",
            "operator": "between",
            "value": [18, 65]
        }

        with pytest.raises(ValueError, match="Invalid type"):
            handler.validate_criterion(criterion)

    def test_validate_criterion_invalid_operator(self):
        """Test validation fails with invalid operator."""
        criterion = {
            "type": "inclusion",
            "category": "demographics",
            "description": "Age test",
            "attribute": "age",
            "operator": "invalid_operator",
            "value": [18, 65]
        }

        with pytest.raises(ValueError, match="Invalid operator"):
            handler.validate_criterion(criterion)

    @patch('handler.bedrock_runtime')
    def test_parse_criteria_with_bedrock(self, mock_bedrock, sample_criteria_text, mock_bedrock_response):
        """Test parsing criteria with Bedrock."""
        mock_bedrock.invoke_model.return_value = mock_bedrock_response

        result = handler.parse_criteria_with_bedrock(sample_criteria_text)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['type'] == 'inclusion'
        assert result[0]['attribute'] == 'age'

    @patch('handler.bedrock_runtime')
    def test_lambda_handler_success(self, mock_bedrock, sample_criteria_text, mock_bedrock_response):
        """Test successful lambda handler execution."""
        mock_bedrock.invoke_model.return_value = mock_bedrock_response

        event = {
            'body': json.dumps({
                'criteria_text': sample_criteria_text,
                'trial_id': 'test-trial-001'
            })
        }

        context = Mock()
        context.get_remaining_time_in_millis.return_value = 30000

        response = handler.lambda_handler(event, context)

        # Print response for debugging
        if response['statusCode'] != 200:
            print(f"Error response: {response}")

        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['trial_id'] == 'test-trial-001'
        assert body['count'] == 2

    def test_lambda_handler_missing_criteria(self):
        """Test lambda handler with missing criteria."""
        event = {
            'body': json.dumps({
                'trial_id': 'test-trial-001'
                # Missing criteria_text
            })
        }

        context = Mock()

        response = handler.lambda_handler(event, context)

        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'error' in body


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
