#!/usr/bin/env python3
"""
Demo script to ingest sample bills and demonstrate the application
"""
import httpx
import asyncio
import sys

API_URL = "http://localhost:8000"

# Sample bills to ingest (real bills from 118th Congress)
SAMPLE_BILLS = [
    {"congress": 118, "bill_type": "hr", "bill_number": 1, "title": "Lower Energy Costs Act"},
    {"congress": 118, "bill_type": "hr", "bill_number": 2, "title": "Secure the Border Act of 2023"},
    {"congress": 118, "bill_type": "s", "bill_number": 1, "title": "Big Oil Windfall Profits Tax Act"},
]


async def check_health():
    """Check if backend is running"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/health", timeout=5.0)
            if response.status_code == 200:
                print("✓ Backend is healthy")
                return True
            else:
                print(f"✗ Backend health check failed: {response.status_code}")
                return False
    except Exception as e:
        print(f"✗ Cannot connect to backend: {e}")
        print(f"  Make sure the backend is running at {API_URL}")
        return False


async def ingest_bill(congress: int, bill_type: str, bill_number: int, title: str = None):
    """Ingest a bill"""
    print(f"\n📄 Ingesting {congress}/{bill_type}/{bill_number}...")
    if title:
        print(f"   Title: {title}")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{API_URL}/ingest/bill",
                json={
                    "congress": congress,
                    "bill_type": bill_type,
                    "bill_number": bill_number
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Success: {data['message']}")
                print(f"  Bill ID: {data['bill_id']}")
                print(f"  Sections created: {data['sections_created']}")
                return data['bill_id']
            else:
                print(f"✗ Error: {response.status_code}")
                print(f"  {response.text}")
                return None
    except Exception as e:
        print(f"✗ Exception: {e}")
        return None


async def list_bills():
    """List all bills"""
    print("\n📋 Listing bills...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/bills?page=1&page_size=10")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Found {data['total']} bills")
                for bill in data['items']:
                    print(f"\n  - {bill['bill_type'].upper()}. {bill['bill_number']}")
                    print(f"    ID: {bill['id']}")
                    print(f"    Title: {bill['title'][:80]}...")
                return data['items']
            else:
                print(f"✗ Error: {response.status_code}")
                return []
    except Exception as e:
        print(f"✗ Exception: {e}")
        return []


async def show_bill_sections(bill_id: str):
    """Show sections of a bill"""
    print(f"\n📑 Fetching bill {bill_id}...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/bills/{bill_id}")
            
            if response.status_code == 200:
                bill = response.json()
                print(f"✓ {bill['bill_type'].upper()}. {bill['bill_number']}: {bill['title']}")
                print(f"\n  Sections ({len(bill['sections'])}):")
                
                for section in bill['sections'][:5]:  # Show first 5 sections
                    print(f"\n  {section['section_key']}: {section['heading']}")
                    
                    if section.get('summary_json'):
                        summary = section['summary_json']
                        bullets = summary.get('plain_summary_bullets', [])
                        print(f"    Summary: {bullets[0][:80]}..." if bullets else "    No summary")
                    else:
                        print("    (Summary pending...)")
                
                if len(bill['sections']) > 5:
                    print(f"\n  ... and {len(bill['sections']) - 5} more sections")
                
                return bill
            else:
                print(f"✗ Error: {response.status_code}")
                return None
    except Exception as e:
        print(f"✗ Exception: {e}")
        return None


async def main():
    """Main demo script"""
    print("=" * 60)
    print("Just A Bill - Demo Script")
    print("=" * 60)
    
    # Check health
    if not await check_health():
        print("\n⚠️  Backend is not running. Start it with:")
        print("   docker-compose up -d backend")
        sys.exit(1)
    
    # Ingest sample bills
    print("\n" + "=" * 60)
    print("Step 1: Ingesting Sample Bills")
    print("=" * 60)
    
    bill_ids = []
    for bill in SAMPLE_BILLS:
        bill_id = await ingest_bill(**bill)
        if bill_id:
            bill_ids.append(bill_id)
        await asyncio.sleep(2)  # Rate limiting
    
    if not bill_ids:
        print("\n⚠️  No bills were successfully ingested.")
        print("   This might be because:")
        print("   1. Congress API key is not configured")
        print("   2. Bills are not available in Congress.gov API yet")
        print("   3. Network issues")
        sys.exit(1)
    
    # Wait for summarization
    print("\n" + "=" * 60)
    print("Step 2: Waiting for Summarization")
    print("=" * 60)
    print("\n⏳ Waiting 10 seconds for worker to summarize sections...")
    print("   (Check worker logs: docker logs -f justabill-worker)")
    await asyncio.sleep(10)
    
    # List bills
    print("\n" + "=" * 60)
    print("Step 3: Listing Bills")
    print("=" * 60)
    bills = await list_bills()
    
    # Show first bill details
    if bills:
        print("\n" + "=" * 60)
        print("Step 4: Viewing Bill Details")
        print("=" * 60)
        await show_bill_sections(bills[0]['id'])
    
    # Final instructions
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)
    print("\n✓ Next steps:")
    print(f"  1. Open the frontend: http://localhost:3000")
    print(f"  2. Browse bills and vote on sections")
    print(f"  3. View your personalized summary")
    print(f"\n✓ API Documentation: http://localhost:8000/docs")
    print(f"✓ n8n Workflows: http://localhost:5678")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
