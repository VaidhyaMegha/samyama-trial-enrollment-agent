"""
Trial Enrollment Agent

Main agent that orchestrates the trial matching workflow using Amazon Bedrock AgentCore.
"""

import json
import os
from typing import Dict, List, Any, Optional
import boto3
from datetime import datetime

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-west-1'))
lambda_client = boto3.client('lambda', region_name=os.environ.get('AWS_REGION', 'ap-south-1'))

# Lambda function names
CRITERIA_PARSER_FUNCTION = os.environ.get('CRITERIA_PARSER_FUNCTION', 'CriteriaParser')
FHIR_SEARCH_FUNCTION = os.environ.get('FHIR_SEARCH_FUNCTION', 'FHIRSearch')


class TrialEnrollmentAgent:
    """
    AI Agent for matching patients to clinical trials.

    This agent:
    1. Parses trial eligibility criteria into structured format
    2. Checks patient data against each criterion
    3. Determines eligibility with detailed explanations
    4. Generates outreach materials
    """

    def __init__(self, model_id: str = "amazon.titan-text-express-v1"):
        """
        Initialize the agent.

        Args:
            model_id: Bedrock model ID for the LLM
        """
        self.model_id = model_id
        self.conversation_history: List[Dict[str, Any]] = []

    def _call_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool (Lambda function).

        Args:
            tool_name: Name of the tool
            parameters: Tool parameters

        Returns:
            Tool result
        """
        function_name = None

        if tool_name == "parse_criteria":
            function_name = CRITERIA_PARSER_FUNCTION
        elif tool_name == "check_criteria":
            function_name = FHIR_SEARCH_FUNCTION
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Invoke Lambda
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=json.dumps(parameters)
        )

        payload = json.loads(response['Payload'].read())

        if payload.get('statusCode') == 200:
            body = json.loads(payload['body'])
            return body
        else:
            raise Exception(f"Tool call failed: {payload.get('body', 'Unknown error')}")

    def _invoke_llm(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> str:
        """
        Invoke the LLM via Bedrock.

        Args:
            messages: Conversation messages
            system_prompt: Optional system prompt

        Returns:
            LLM response text
        """
        # Combine system prompt and user message for Titan
        full_prompt = ""
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n"
        
        # Combine all messages
        for msg in messages:
            if msg['role'] == 'user':
                full_prompt += msg['content']
        
        request_body = {
            "inputText": full_prompt,
            "textGenerationConfig": {
                "maxTokenCount": 4000,
                "temperature": 0.3,
                "topP": 0.9
            }
        }

        response = bedrock_runtime.invoke_model(
            modelId=self.model_id,
            body=json.dumps(request_body)
        )

        response_body = json.loads(response['body'].read())
        return response_body['results'][0]['outputText']

    def evaluate_eligibility(
        self,
        patient_id: str,
        trial_criteria: str,
        trial_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate patient eligibility for a trial.

        Args:
            patient_id: Patient identifier
            trial_criteria: Free-text eligibility criteria
            trial_id: Optional trial identifier

        Returns:
            Eligibility result with explanations
        """
        if trial_id is None:
            trial_id = f"trial-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Step 1: Parse criteria using the Criteria Parser tool
        print(f"[Agent] Parsing eligibility criteria for {trial_id}...")

        parse_result = self._call_tool('parse_criteria', {
            'criteria_text': trial_criteria,
            'trial_id': trial_id
        })

        parsed_criteria = parse_result['criteria']
        print(f"[Agent] Parsed {len(parsed_criteria)} criteria")

        # Step 2: Check patient against criteria using FHIR Search tool
        print(f"[Agent] Checking patient {patient_id} against criteria...")

        check_result = self._call_tool('check_criteria', {
            'patient_id': patient_id,
            'criteria': parsed_criteria
        })

        eligible = check_result['eligible']
        results = check_result['results']
        summary = check_result['summary']

        print(f"[Agent] Patient {patient_id} eligibility: {'ELIGIBLE' if eligible else 'NOT ELIGIBLE'}")

        # Step 3: Generate explanation using LLM
        print(f"[Agent] Generating detailed explanation...")

        explanation = self._generate_explanation(
            patient_id=patient_id,
            trial_id=trial_id,
            eligible=eligible,
            results=results,
            summary=summary
        )

        # Compile final result
        final_result = {
            'trial_id': trial_id,
            'patient_id': patient_id,
            'eligible': eligible,
            'summary': summary,
            'explanation': explanation,
            'detailed_results': results,
            'parsed_criteria': parsed_criteria,
            'timestamp': datetime.now().isoformat()
        }

        return final_result

    def _generate_explanation(
        self,
        patient_id: str,
        trial_id: str,
        eligible: bool,
        results: List[Dict[str, Any]],
        summary: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable explanation of eligibility decision.

        Args:
            patient_id: Patient identifier
            trial_id: Trial identifier
            eligible: Whether patient is eligible
            results: Detailed criterion-by-criterion results
            summary: Summary statistics

        Returns:
            Explanation text
        """
        # Prepare data for LLM
        results_summary = []
        for r in results:
            criterion_info = r['criterion']
            results_summary.append({
                'type': criterion_info['type'],
                'description': criterion_info['description'],
                'met': r['met'],
                'reason': r['reason']
            })

        system_prompt = """You are a clinical trial coordinator AI assistant.
Your task is to explain trial eligibility decisions to healthcare professionals in clear, professional language.

Focus on:
1. Overall eligibility status
2. Which criteria were met or not met
3. Specific evidence from patient records
4. Next steps or recommendations

Be concise but thorough. Use medical terminology appropriately."""

        user_message = f"""Generate a professional explanation for the following trial eligibility assessment:

Trial ID: {trial_id}
Patient ID: {patient_id}
Overall Eligibility: {"ELIGIBLE" if eligible else "NOT ELIGIBLE"}

Criteria Results:
{json.dumps(results_summary, indent=2)}

Summary Statistics:
- Total criteria checked: {summary['total_criteria']}
- Inclusion criteria met: {summary['inclusion_met']}
- Exclusion criteria violated: {summary['exclusion_violated']}

Provide a clear, professional explanation suitable for a clinical research coordinator."""

        explanation = self._invoke_llm(
            messages=[{"role": "user", "content": user_message}],
            system_prompt=system_prompt
        )

        return explanation

    def generate_outreach_material(
        self,
        patient_id: str,
        trial_id: str,
        eligibility_result: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Generate outreach materials for eligible patients.

        Args:
            patient_id: Patient identifier
            trial_id: Trial identifier
            eligibility_result: Result from evaluate_eligibility

        Returns:
            Dictionary with outreach materials
        """
        if not eligibility_result['eligible']:
            return {
                'error': 'Patient is not eligible for this trial'
            }

        system_prompt = """You are a clinical trial recruitment specialist.
Generate professional outreach materials for clinical trial enrollment.

Your materials should be:
1. Professional and respectful
2. Clear about the trial opportunity
3. Emphasize that this is preliminary screening
4. Require physician review and patient consent
5. HIPAA-compliant (no unnecessary PHI disclosure)"""

        # Generate physician outreach email
        physician_email_prompt = f"""Generate a brief email to the patient's physician about a potential trial match:

Trial ID: {trial_id}
Patient ID: {patient_id}

Eligibility Summary:
{eligibility_result['explanation']}

The email should:
- Inform the physician of the match
- Request their review
- Provide next steps
- Be no more than 200 words

Generate only the email body, no subject line."""

        physician_email = self._invoke_llm(
            messages=[{"role": "user", "content": physician_email_prompt}],
            system_prompt=system_prompt
        )

        # Generate screening checklist
        checklist_prompt = f"""Generate a screening checklist for study coordinators:

Trial ID: {trial_id}
Patient ID: {patient_id}

Criteria Met:
{json.dumps([r for r in eligibility_result['detailed_results'] if r['met']], indent=2)}

Create a bulleted checklist of items to verify before enrollment."""

        screening_checklist = self._invoke_llm(
            messages=[{"role": "user", "content": checklist_prompt}],
            system_prompt=system_prompt
        )

        return {
            'physician_outreach_email': physician_email,
            'screening_checklist': screening_checklist,
            'trial_id': trial_id,
            'patient_id': patient_id
        }


def main():
    """
    Example usage of the agent.
    """
    # Example trial criteria
    trial_criteria = """
    Inclusion Criteria:
    - Patients must be between 18 and 65 years old
    - Diagnosis of Type 2 Diabetes Mellitus
    - HbA1c between 7% and 10%

    Exclusion Criteria:
    - Chronic kidney disease stage 4 or higher
    - Pregnant or breastfeeding
    """

    # Initialize agent
    agent = TrialEnrollmentAgent()

    # Evaluate eligibility
    result = agent.evaluate_eligibility(
        patient_id="patient-001",
        trial_criteria=trial_criteria,
        trial_id="NCT12345678"
    )

    print("\n" + "="*80)
    print("ELIGIBILITY ASSESSMENT RESULT")
    print("="*80)
    print(f"\nTrial: {result['trial_id']}")
    print(f"Patient: {result['patient_id']}")
    print(f"Eligible: {result['eligible']}")
    print(f"\n{result['explanation']}")
    print("\n" + "="*80)

    # Generate outreach materials if eligible
    if result['eligible']:
        outreach = agent.generate_outreach_material(
            patient_id=result['patient_id'],
            trial_id=result['trial_id'],
            eligibility_result=result
        )

        print("\nOUTREACH MATERIALS")
        print("="*80)
        print("\nPhysician Email:")
        print(outreach['physician_outreach_email'])
        print("\nScreening Checklist:")
        print(outreach['screening_checklist'])
        print("\n" + "="*80)


if __name__ == "__main__":
    main()
