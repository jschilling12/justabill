import requests
import json
import os
from datetime import datetime
from time import sleep

# President-Congress mapping
PRESIDENTS = [
    {"name": "Donald Trump 2nd", "congresses": [115, 116, 119]},
    {"name": "Joe Biden", "congresses": [117, 118]},
    {"name": "Barack Obama", "congresses": [111, 112, 113, 114]},
    {"name": "George W. Bush", "congresses": [107, 108, 109, 110]},
    {"name": "Bill Clinton", "congresses": [103, 104, 105, 106]},
    {"name": "George H.W. Bush", "congresses": [101, 102]}
]

# Load API key from environment or .env
CONGRESS_API_KEY = os.getenv("CONGRESS_API_KEY", "")
if not CONGRESS_API_KEY:
    try:
        with open("../.env", "r") as f:
            for line in f:
                if line.startswith("CONGRESS_API_KEY="):
                    CONGRESS_API_KEY = line.strip().split("=", 1)[1].strip('"')
                    break
    except:
        pass

if not CONGRESS_API_KEY:
    print("ERROR: CONGRESS_API_KEY not found in environment or .env file")
    exit(1)

def fetch_bills_for_congress(congress_num):
    """Fetch all bills for a given congress session"""
    url = f"https://api.congress.gov/v3/bill/{congress_num}"
    params = {
        "api_key": CONGRESS_API_KEY,
        "limit": 250
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("bills", [])
    except Exception as e:
        print(f"  ERROR fetching congress {congress_num}: {e}")
        return []

def filter_enacted_bills(bills):
    """Filter for only enacted bills"""
    enacted = []
    for bill in bills:
        if not bill or not isinstance(bill, dict):
            continue
        latest_action = bill.get("latestAction")
        if not latest_action or not isinstance(latest_action, dict):
            continue
        action_text = latest_action.get("text", "").lower()
        if any(phrase in action_text for phrase in ["became public law", "became law", "signed by president"]):
            enacted.append({
                "congress": bill.get("congress"),
                "bill_type": bill.get("type", "").lower(),
                "bill_number": int(bill.get("number", 0)),
                "title": bill.get("title", ""),
                "latest_action": latest_action.get("text", ""),
                "action_date": latest_action.get("actionDate", "")
            })
    return enacted

def main():
    print("Fetching enacted bills for all presidents...")
    print(f"Using API key: {CONGRESS_API_KEY[:10]}...")
    print()
    
    all_data = []
    total_enacted = 0
    
    for president in PRESIDENTS:
        print(f"President: {president['name']}")
        president_enacted = []
        
        for congress in president["congresses"]:
            print(f"  Fetching Congress {congress}...", end=" ")
            bills = fetch_bills_for_congress(congress)
            enacted = filter_enacted_bills(bills)
            print(f"{len(enacted)} enacted bills")
            
            president_enacted.extend(enacted)
            total_enacted += len(enacted)
            
            # Rate limit: 1 request per 2 seconds
            sleep(2)
        
        all_data.append({
            "president": president["name"],
            "congresses": president["congresses"],
            "enacted_bills": president_enacted,
            "total_enacted": len(president_enacted)
        })
        
        print(f"  Total enacted for {president['name']}: {len(president_enacted)}")
        print()
    
    # Save to JSON file
    output_file = "enacted_bills_data.json"
    with open(output_file, "w") as f:
        json.dump({
            "fetched_at": datetime.utcnow().isoformat(),
            "total_enacted_bills": total_enacted,
            "presidents": all_data
        }, f, indent=2)
    
    print(f"✅ Complete! Total enacted bills: {total_enacted}")
    print(f"📄 Data saved to: {output_file}")
    print()
    print("Summary by president:")
    for pres_data in all_data:
        print(f"  {pres_data['president']}: {pres_data['total_enacted']} bills")

if __name__ == "__main__":
    main()
