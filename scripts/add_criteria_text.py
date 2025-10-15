"""
Add criteria_text field to all protocols in criteria cache
Generates human-readable criteria text from parsed_criteria
"""

import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table_name = 'TrialEnrollmentAgentStack-CriteriaCacheTableFDCD8472-1QNO79RYH9M88'
table = dynamodb.Table(table_name)

def generate_criteria_text(parsed_criteria):
    """Generate human-readable criteria text from parsed criteria."""
    inclusion_criteria = []
    exclusion_criteria = []

    for criterion in parsed_criteria:
        desc = criterion.get('description', '')
        criterion_type = criterion.get('type', '')

        if criterion_type == 'inclusion':
            inclusion_criteria.append(f"- {desc}")
        elif criterion_type == 'exclusion':
            exclusion_criteria.append(f"- {desc}")

    text_parts = []

    if inclusion_criteria:
        text_parts.append("Inclusion Criteria:")
        text_parts.extend(inclusion_criteria)

    if exclusion_criteria:
        if inclusion_criteria:
            text_parts.append("")  # Empty line between sections
        text_parts.append("Exclusion Criteria:")
        text_parts.extend(exclusion_criteria)

    return "\n".join(text_parts)

def update_protocol(trial_id, parsed_criteria):
    """Update a protocol with criteria_text."""
    try:
        criteria_text = generate_criteria_text(parsed_criteria)

        table.update_item(
            Key={'trial_id': trial_id},
            UpdateExpression='SET criteria_text = :text',
            ExpressionAttributeValues={':text': criteria_text}
        )

        return True, len(criteria_text)
    except Exception as e:
        return False, str(e)

def main():
    print('='*80)
    print('ADDING criteria_text TO ALL PROTOCOLS')
    print('='*80)
    print()

    # Scan all items
    response = table.scan()
    items = response.get('Items', [])

    print(f'Found {len(items)} protocols to update')
    print()

    success_count = 0
    fail_count = 0

    for item in items:
        trial_id = item.get('trial_id')
        parsed_criteria = item.get('parsed_criteria', [])

        success, result = update_protocol(trial_id, parsed_criteria)

        if success:
            print(f'✅ {trial_id:30} - Added {result} chars of criteria text')
            success_count += 1
        else:
            print(f'❌ {trial_id:30} - Error: {result}')
            fail_count += 1

    print()
    print('='*80)
    print(f'✅ Successfully updated: {success_count}/{len(items)}')
    if fail_count > 0:
        print(f'❌ Failed: {fail_count}/{len(items)}')
    print('='*80)
    print()

    # Verify by checking one protocol
    print('Verifying update...')
    response = table.get_item(Key={'trial_id': 'DIABETES-SIMPLE-001'})
    item = response.get('Item', {})

    if 'criteria_text' in item:
        print('✅ criteria_text field is now present!')
        print()
        print('Sample criteria_text (DIABETES-SIMPLE-001):')
        print('-'*80)
        print(item['criteria_text'])
        print('-'*80)
    else:
        print('❌ criteria_text field still missing!')

if __name__ == '__main__':
    main()
