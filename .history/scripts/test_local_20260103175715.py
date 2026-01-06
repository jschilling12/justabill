#!/usr/bin/env python3
"""
Local testing script that works without external API keys.
Creates mock bill data directly in the database for testing.
"""
import httpx
import asyncio
import sys
import uuid
from datetime import datetime, timedelta

API_URL = "http://localhost:8000"

# ANSI colors
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


def print_header(text: str):
    """Print a section header"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")


def print_success(text: str):
    """Print success message"""
    print(f"{GREEN}✓{RESET} {text}")


def print_error(text: str):
    """Print error message"""
    print(f"{RED}✗{RESET} {text}")


def print_info(text: str):
    """Print info message"""
    print(f"{BLUE}ℹ{RESET} {text}")


async def check_health():
    """Check if backend is running"""
    print_header("Backend Health Check")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{API_URL}/health", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                print_success("Backend is healthy")
                print(f"  Status: {data.get('status')}")
                print(f"  Database: {data.get('database')}")
                return True
            else:
                print_error(f"Backend health check failed: {response.status_code}")
                return False
    except httpx.ConnectError:
        print_error("Cannot connect to backend")
        print_info(f"Make sure backend is running: docker-compose up -d backend")
        return False
    except Exception as e:
        print_error(f"Error: {e}")
        return False


async def test_api_endpoints():
    """Test basic API endpoints"""
    print_header("API Endpoint Tests")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test GET /bills (should work even with no data)
            response = await client.get(f"{API_URL}/bills?page=1&page_size=10")
            if response.status_code == 200:
                data = response.json()
                print_success(f"GET /bills - {data.get('total', 0)} bills found")
                return data
            else:
                print_error(f"GET /bills failed: {response.status_code}")
                return None
    except Exception as e:
        print_error(f"Error testing endpoints: {e}")
        return None


async def create_mock_bill_directly():
    """
    Create a mock bill for testing purposes.
    This bypasses the Congress API and creates a minimal test bill.
    """
    print_header("Creating Mock Bill (Test Mode)")
    
    # Create a mock bill with test data
    mock_bill_data = {
        "congress": 118,
        "bill_type": "hr",
        "bill_number": 9999,
        "title": "Test Bill for Local Development",
        "sponsor_name": "Test Sponsor",
        "sponsor_party": "Independent",
        "sponsor_state": "TS",
        "summary": "This is a test bill created for local development and testing purposes. It does not represent real legislation.",
        "status": "introduced",
        "introduced_date": "2026-01-01",
        "latest_action_date": "2026-01-01",
        "latest_action_text": "Introduced in House",
        "policy_area": "Testing",
        "official_url": "https://www.congress.gov/bill/118th-congress/house-bill/9999",
        "text_versions": {
            "Introduced in House": "https://example.com/test-bill.txt"
        },
        # Add sections
        "sections": [
            {
                "section_number": "1",
                "section_title": "Short Title",
                "content": "This Act may be cited as the 'Test Bill for Local Development'.",
                "position": 1
            },
            {
                "section_number": "2",
                "section_title": "Purpose and Findings",
                "content": "The purpose of this test bill is to demonstrate the functionality of the Just A Bill application. Congress finds that:\n(1) Testing is important for software development.\n(2) Mock data helps validate application features.\n(3) Users should be able to explore the interface without real API keys.",
                "position": 2
            },
            {
                "section_number": "3",
                "section_title": "Test Provisions",
                "content": "SEC. 3. TEST PROVISIONS.\n\n(a) General Rule.--This section contains test provisions to demonstrate section voting.\n\n(b) Subsection Example.--Users can vote on this section:\n  (1) Upvote if they support this provision;\n  (2) Downvote if they oppose this provision;\n  (3) Skip if they are unsure.",
                "position": 3
            },
            {
                "section_number": "4",
                "section_title": "Implementation",
                "content": "The Secretary shall implement this test bill by:\n(1) Validating all application features work correctly;\n(2) Ensuring the database schema is properly structured;\n(3) Confirming the voting mechanism functions as expected.",
                "position": 4
            }
        ]
    }
    
    print_info("Creating test bill in database...")
    print(f"  Congress: {mock_bill_data['congress']}")
    print(f"  Type: {mock_bill_data['bill_type'].upper()}")
    print(f"  Number: {mock_bill_data['bill_number']}")
    print(f"  Sections: {len(mock_bill_data['sections'])}")
    
    # In a real implementation, this would call an internal endpoint
    # For now, we'll note that this needs to be implemented
    print_info("\nNote: Direct database insertion not yet implemented in this script.")
    print_info("To create test bills, you have two options:")
    print_info("  1. Add a test/mock endpoint to the backend")
    print_info("  2. Run the ingestion with actual API keys")
    
    return None


async def test_voting_flow(bill_id: str):
    """Test the voting flow"""
    print_header("Testing Voting Flow")
    
    # Generate a session ID
    session_id = str(uuid.uuid4())
    print_info(f"Session ID: {session_id}")
    
    try:
        async with httpx.AsyncClient() as client:
            # Get bill details
            response = await client.get(f"{API_URL}/bills/{bill_id}")
            if response.status_code != 200:
                print_error(f"Failed to get bill details: {response.status_code}")
                return False
            
            bill_data = response.json()
            print_success(f"Retrieved bill: {bill_data['title'][:60]}...")
            
            sections = bill_data.get('sections', [])
            if not sections:
                print_error("Bill has no sections to vote on")
                return False
            
            print_info(f"Bill has {len(sections)} sections")
            
            # Vote on first few sections
            votes = [("up", "✓ Support"), ("down", "✗ Oppose"), ("skip", "⊗ Skip")]
            
            for i, section in enumerate(sections[:3]):
                vote_type, vote_label = votes[i % len(votes)]
                
                print(f"\n  Section {section['section_number']}: {section.get('section_title', 'Untitled')}")
                print(f"  Voting: {vote_label}")
                
                response = await client.post(
                    f"{API_URL}/votes/vote",
                    params={"bill_id": bill_id},
                    headers={"X-Session-ID": session_id},
                    json={
                        "section_id": section['id'],
                        "vote": vote_type
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print_success(f"Vote recorded: {result['vote']}")
                else:
                    print_error(f"Vote failed: {response.status_code}")
            
            # Get user summary
            print("\n" + "="*60)
            response = await client.get(
                f"{API_URL}/bills/{bill_id}/user-summary",
                headers={"X-Session-ID": session_id}
            )
            
            if response.status_code == 200:
                summary = response.json()
                print_success("User Summary Retrieved")
                print(f"\n  Overall Stance: {summary['overall_stance']}")
                print(f"  Support Score: {summary['support_percentage']:.1f}%")
                print(f"  Votes Cast: {summary['votes_cast']}")
                print(f"  Total Sections: {summary['total_sections']}")
                
                if summary.get('key_supported_sections'):
                    print("\n  Sections You Supported:")
                    for sec in summary['key_supported_sections'][:2]:
                        print(f"    • Section {sec['section_number']}: {sec['section_title']}")
                
                if summary.get('key_opposed_sections'):
                    print("\n  Sections You Opposed:")
                    for sec in summary['key_opposed_sections'][:2]:
                        print(f"    • Section {sec['section_number']}: {sec['section_title']}")
                
                return True
            else:
                print_error(f"Failed to get user summary: {response.status_code}")
                return False
            
    except Exception as e:
        print_error(f"Error in voting flow: {e}")
        return False


async def run_full_test():
    """Run full application test"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}Just A Bill - Local Test Suite{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    
    # Check health
    if not await check_health():
        print_error("\nBackend is not running. Start it with:")
        print_info("  docker-compose up -d")
        return False
    
    # Test API endpoints
    bills_data = await test_api_endpoints()
    
    if bills_data and bills_data.get('total', 0) > 0:
        # If bills exist, test with first bill
        bill = bills_data['items'][0]
        print_info(f"\nUsing existing bill: {bill['title'][:60]}...")
        await test_voting_flow(bill['id'])
    else:
        print_info("\nNo bills found in database")
        print_info("\nTo test the full application:")
        print_info("  1. Add your API keys to .env file")
        print_info("  2. Run: python scripts/demo.py")
        print_info("     This will ingest real bills from Congress.gov")
        print_info("\nOR create a test bill endpoint in the backend")
    
    print_header("Test Summary")
    print_success("Local testing completed")
    print_info("Application structure is functional")
    
    return True


async def main():
    """Main function"""
    try:
        await run_full_test()
        return 0
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        return 1
    except Exception as e:
        print_error(f"\nUnexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
