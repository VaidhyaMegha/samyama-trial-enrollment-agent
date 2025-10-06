"""
Demo script for Trial Enrollment Agent.

This script demonstrates the end-to-end workflow of the agent.
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from agent.trial_enrollment_agent import TrialEnrollmentAgent


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80 + "\n")


def demo_scenario_1():
    """
    Demo Scenario 1: Eligible Patient
    Patient-001: 45yo female with Type 2 Diabetes, HbA1c 8%
    """
    print_section("SCENARIO 1: Eligible Patient")

    trial_criteria = """
    Inclusion Criteria:
    - Patients must be between 18 and 65 years old
    - Diagnosis of Type 2 Diabetes Mellitus
    - HbA1c between 7% and 10%

    Exclusion Criteria:
    - Chronic kidney disease stage 4 or higher
    - Pregnant or breastfeeding
    """

    print("Trial Criteria:")
    print(trial_criteria)
    print("\nPatient: patient-001 (Sarah Smith, 45yo female)")
    print("- Type 2 Diabetes Mellitus")
    print("- HbA1c: 8.0%")
    print("\n" + "-"*80)

    # Initialize agent
    agent = TrialEnrollmentAgent()

    # Evaluate eligibility
    print("\n[Agent] Starting eligibility evaluation...")
    result = agent.evaluate_eligibility(
        patient_id="patient-001",
        trial_criteria=trial_criteria,
        trial_id="DIABETES-TRIAL-2024"
    )

    # Display results
    print("\n" + "="*80)
    print(" ELIGIBILITY RESULT")
    print("="*80)
    print(f"\nTrial ID: {result['trial_id']}")
    print(f"Patient ID: {result['patient_id']}")
    print(f"Timestamp: {result['timestamp']}")
    print(f"\nELIGIBLE: {'✓ YES' if result['eligible'] else '✗ NO'}")
    print(f"\nSummary:")
    print(f"  - Total Criteria: {result['summary']['total_criteria']}")
    print(f"  - Inclusion Met: {result['summary']['inclusion_met']}")
    print(f"  - Exclusions Violated: {result['summary']['exclusion_violated']}")

    print(f"\nExplanation:")
    print(result['explanation'])

    # Generate outreach materials if eligible
    if result['eligible']:
        print("\n" + "="*80)
        print(" GENERATING OUTREACH MATERIALS")
        print("="*80)

        outreach = agent.generate_outreach_material(
            patient_id=result['patient_id'],
            trial_id=result['trial_id'],
            eligibility_result=result
        )

        print("\nPhysician Outreach Email:")
        print("-"*80)
        print(outreach['physician_outreach_email'])

        print("\nScreening Checklist:")
        print("-"*80)
        print(outreach['screening_checklist'])


def demo_scenario_2():
    """
    Demo Scenario 2: Ineligible Patient (Too Young)
    Patient-002: 14yo male
    """
    print_section("SCENARIO 2: Ineligible Patient (Age Criterion)")

    trial_criteria = """
    Inclusion Criteria:
    - Patients must be between 18 and 65 years old
    - Diagnosis of Type 2 Diabetes Mellitus
    """

    print("Trial Criteria:")
    print(trial_criteria)
    print("\nPatient: patient-002 (Michael Johnson, 14yo male)")
    print("\n" + "-"*80)

    agent = TrialEnrollmentAgent()

    print("\n[Agent] Starting eligibility evaluation...")
    result = agent.evaluate_eligibility(
        patient_id="patient-002",
        trial_criteria=trial_criteria,
        trial_id="DIABETES-TRIAL-2024"
    )

    print("\n" + "="*80)
    print(" ELIGIBILITY RESULT")
    print("="*80)
    print(f"\nELIGIBLE: {'✓ YES' if result['eligible'] else '✗ NO'}")

    if not result['eligible']:
        print("\nFailed Criteria:")
        for failed in result['summary'].get('failed_criteria', []):
            print(f"  - {failed['criterion']['description']}: {failed['reason']}")

    print(f"\nExplanation:")
    print(result['explanation'])


def demo_scenario_3():
    """
    Demo Scenario 3: Ineligible Patient (Exclusion Criterion)
    Patient-003: 54yo male with Type 2 Diabetes and CKD Stage 4
    """
    print_section("SCENARIO 3: Ineligible Patient (Exclusion Criterion)")

    trial_criteria = """
    Inclusion Criteria:
    - Patients must be between 18 and 65 years old
    - Diagnosis of Type 2 Diabetes Mellitus
    - HbA1c between 7% and 10%

    Exclusion Criteria:
    - Chronic kidney disease stage 4 or higher
    """

    print("Trial Criteria:")
    print(trial_criteria)
    print("\nPatient: patient-003 (Robert Williams, 54yo male)")
    print("- Type 2 Diabetes Mellitus")
    print("- HbA1c: 7.5%")
    print("- Chronic Kidney Disease Stage 4 ⚠️")
    print("\n" + "-"*80)

    agent = TrialEnrollmentAgent()

    print("\n[Agent] Starting eligibility evaluation...")
    result = agent.evaluate_eligibility(
        patient_id="patient-003",
        trial_criteria=trial_criteria,
        trial_id="DIABETES-TRIAL-2024"
    )

    print("\n" + "="*80)
    print(" ELIGIBILITY RESULT")
    print("="*80)
    print(f"\nELIGIBLE: {'✓ YES' if result['eligible'] else '✗ NO'}")

    print(f"\nExplanation:")
    print(result['explanation'])


def main():
    """Run all demo scenarios."""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "TRIAL ENROLLMENT AGENT DEMO" + " "*31 + "║")
    print("╚" + "="*78 + "╝")

    print("\nThis demo showcases the AI agent's ability to:")
    print("  1. Parse clinical trial eligibility criteria")
    print("  2. Check patient FHIR data against criteria")
    print("  3. Determine eligibility with detailed explanations")
    print("  4. Generate outreach materials for eligible patients")

    print("\nNote: This demo uses mock data and simulated Lambda invocations.")
    print("In production, it would connect to AWS Bedrock and HealthLake.")

    input("\nPress Enter to start the demo...")

    try:
        # Run scenarios
        demo_scenario_1()
        input("\n\nPress Enter to continue to Scenario 2...")

        demo_scenario_2()
        input("\n\nPress Enter to continue to Scenario 3...")

        demo_scenario_3()

        print("\n" + "="*80)
        print(" DEMO COMPLETE")
        print("="*80)
        print("\nThe agent successfully demonstrated:")
        print("  ✓ Criteria parsing with Amazon Bedrock")
        print("  ✓ FHIR data integration")
        print("  ✓ Multi-criteria eligibility evaluation")
        print("  ✓ Explainable AI decision-making")
        print("  ✓ Automated outreach generation")

    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
    except Exception as e:
        print(f"\n\nError during demo: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
