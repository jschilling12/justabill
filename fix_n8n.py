import json

# Load the workflow
with open('n8n/workflows/enacted-bills-on-demand.json', 'r') as f:
    data = json.load(f)

# Find the Filter for Popularity Scan node
node = next((n for n in data['nodes'] if n['name'] == 'Filter for Popularity Scan'), None)

if node:
    # Get the jsCode
    code = node['parameters']['jsCode']
    
    # Remove Reagan entry
    code = code.replace(
        '  "George H.W. Bush": { start: "1989-01-20", end: "1993-01-20" },\n  "Ronald Reagan": { start: "1981-01-20", end: "1989-01-20" },\n};',
        '  "George H.W. Bush": { start: "1989-01-20", end: "1993-01-20" },\n};'
    )
    
    # Update the node
    node['parameters']['jsCode'] = code
    
    # Save the workflow
    with open('n8n/workflows/enacted-bills-on-demand.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print("✓ Removed Reagan from n8n workflow")
else:
    print("✗ Could not find Filter for Popularity Scan node")
