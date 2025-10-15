"""
Generate Postman Collection JSON files for Clinical Trial Protocol Seeding
Creates 2 collections with 20 protocols each for manual API testing
"""

import json
import sys
sys.path.append('/Users/user/Documents/GitHub/Hackathon/aws-trial-enrollment-agent/scripts')

# Import protocols from seed_protocols.py
from seed_protocols import PROTOCOLS, API_URL

def create_postman_collection(protocols, part_number, filename):
    """
    Create a Postman Collection v2.1.0 JSON structure

    Args:
        protocols: List of protocol dictionaries
        part_number: Part number (1 or 2)
        filename: Output filename
    """

    # Build request items
    items = []
    for i, protocol in enumerate(protocols, 1):
        request_item = {
            "name": f"{protocol['trial_id']} - {protocol['title']}",
            "request": {
                "method": "POST",
                "header": [
                    {
                        "key": "Content-Type",
                        "value": "application/json",
                        "type": "text"
                    }
                ],
                "body": {
                    "mode": "raw",
                    "raw": json.dumps({
                        "trial_id": protocol["trial_id"],
                        "criteria_text": protocol["criteria_text"]
                    }, indent=2)
                },
                "url": {
                    "raw": "{{base_url}}/parse-criteria",
                    "host": ["{{base_url}}"],
                    "path": ["parse-criteria"]
                },
                "description": f"Parse criteria for {protocol['title']}\n\nTrial ID: {protocol['trial_id']}\n\nThis request will take 3-4 minutes to complete due to Bedrock AI processing."
            },
            "response": []
        }
        items.append(request_item)

    # Create collection structure
    collection = {
        "info": {
            "name": f"Clinical Trial Protocols - Parse Criteria API - Part {part_number}",
            "description": f"Collection of 20 clinical trial protocols (Part {part_number} of 2) for seeding the criteria cache table.\n\n## Usage Instructions:\n\n1. **Set Collection Variables:**\n   - `base_url`: https://gt7dlyqj78.execute-api.us-east-1.amazonaws.com/prod\n   - `auth_token`: Get a fresh JWT token by running:\n     ```bash\n     cd infrastructure && python3 get_jwt_token.py --role studyadmin\n     ```\n     Copy the access token and paste it into the `auth_token` variable.\n\n2. **Authentication:**\n   - The collection is configured to use Bearer token authentication\n   - Token expires in 60 minutes - refresh if needed\n\n3. **Running Requests:**\n   - Each request takes 3-4 minutes to complete (Bedrock AI processing)\n   - Run requests one at a time or use Collection Runner with appropriate delays\n   - API Gateway timeout is 30 seconds, but Lambda continues processing\n\n4. **Expected Response:**\n   - Status: 200 OK\n   - Body contains parsed criteria with inclusion/exclusion criteria\n   - Criteria are automatically cached in DynamoDB\n\n## Protocol Coverage:\n\nThis collection includes comprehensive FHIR resource coverage:\n- Patient demographics (age, gender)\n- Conditions (diagnoses, cancer types/stages)\n- Observations (lab values, performance status)\n- Medications (current medications)\n- Procedures (prior treatments)\n- Allergies\n- Immunizations\n- Family history\n- Diagnostic reports\n- Care plans\n- Encounters\n\n## Notes:\n\n- Total protocols across both parts: 40\n- Each protocol has been carefully designed with realistic clinical criteria\n- Protocols cover diverse medical specialties",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            "_exporter_id": "clinical-trial-seeding"
        },
        "auth": {
            "type": "bearer",
            "bearer": [
                {
                    "key": "token",
                    "value": "{{auth_token}}",
                    "type": "string"
                }
            ]
        },
        "variable": [
            {
                "key": "base_url",
                "value": "https://gt7dlyqj78.execute-api.us-east-1.amazonaws.com/prod",
                "type": "string"
            },
            {
                "key": "auth_token",
                "value": "",
                "type": "string",
                "description": "Get token by running: cd infrastructure && python3 get_jwt_token.py --role studyadmin"
            }
        ],
        "item": items
    }

    # Write to file
    output_path = f"/Users/user/Documents/GitHub/Hackathon/aws-trial-enrollment-agent/postman/{filename}"
    with open(output_path, 'w') as f:
        json.dump(collection, f, indent=2)

    print(f"✅ Created: {filename}")
    print(f"   - Protocols: {len(protocols)}")
    print(f"   - Requests: {len(items)}")
    print(f"   - Path: {output_path}\n")


def main():
    print("\n" + "="*80)
    print("POSTMAN COLLECTION GENERATOR")
    print("="*80)
    print(f"\nTotal protocols available: {len(PROTOCOLS)}")
    print("Splitting into 2 collections of 20 protocols each\n")

    # Create postman directory if it doesn't exist
    import os
    os.makedirs("/Users/user/Documents/GitHub/Hackathon/aws-trial-enrollment-agent/postman", exist_ok=True)

    # Part 1: First 20 protocols
    part1_protocols = PROTOCOLS[0:20]
    create_postman_collection(
        protocols=part1_protocols,
        part_number=1,
        filename="Clinical_Trial_Protocols_Part1.postman_collection.json"
    )

    # Part 2: Next 20 protocols
    part2_protocols = PROTOCOLS[20:40]
    create_postman_collection(
        protocols=part2_protocols,
        part_number=2,
        filename="Clinical_Trial_Protocols_Part2.postman_collection.json"
    )

    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\n✅ Successfully created 2 Postman collection files")
    print(f"\n📁 Location: /Users/user/Documents/GitHub/Hackathon/aws-trial-enrollment-agent/postman/")
    print(f"\n📝 Files:")
    print(f"   1. Clinical_Trial_Protocols_Part1.postman_collection.json (Protocols 1-20)")
    print(f"   2. Clinical_Trial_Protocols_Part2.postman_collection.json (Protocols 21-40)")
    print(f"\n🚀 Next Steps:")
    print(f"   1. Import both collections into Postman")
    print(f"   2. Set collection variable 'auth_token' with a fresh JWT token")
    print(f"   3. Run requests individually or use Collection Runner")
    print(f"   4. Each request will take 3-4 minutes to complete")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
