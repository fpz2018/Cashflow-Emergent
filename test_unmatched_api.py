#!/usr/bin/env python3
"""
Direct test unmatched API endpoint
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment  
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / 'backend/.env')

# Import server components
import sys
sys.path.append(str(ROOT_DIR))

from backend.server import BankTransaction, parse_from_mongo

async def test_unmatched_api():
    # Connect to database
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("🧪 Testing unmatched API logic directly...")
    
    # Replicate the exact query from the API
    bank_transactions = await db.bank_transactions.find({"reconciled": False}).to_list(1000)
    
    print(f"📊 Found {len(bank_transactions)} unreconciled transactions from DB")
    
    # Count negative ones in raw data
    negative_raw = [bt for bt in bank_transactions if bt.get('amount', 0) < 0]
    print(f"📊 Negative transactions in raw data: {len(negative_raw)}")
    
    if len(negative_raw) > 0:
        print(f"\n📋 First negative raw transaction:")
        print(f"  Amount: {negative_raw[0].get('amount')}")
        print(f"  Description: {negative_raw[0].get('description')}")
        print(f"  Date: {negative_raw[0].get('date')}")
    
    # Try to parse them like the API does
    try:
        parsed_transactions = []
        for bt in bank_transactions[:10]:  # Test first 10
            try:
                parsed = BankTransaction(**parse_from_mongo(bt))
                parsed_transactions.append(parsed)
                if parsed.amount < 0:
                    print(f"\n✅ Successfully parsed negative transaction:")
                    print(f"  Amount: {parsed.amount}")
                    print(f"  Description: {parsed.description}")
            except Exception as e:
                print(f"❌ Failed to parse transaction {bt.get('id', 'unknown')}: {e}")
                if bt.get('amount', 0) < 0:
                    print(f"   This was a negative transaction: {bt.get('amount')}")
        
        print(f"\n📊 Successfully parsed {len(parsed_transactions)} transactions")
        negative_parsed = [t for t in parsed_transactions if t.amount < 0]
        print(f"📊 Negative transactions after parsing: {len(negative_parsed)}")
        
    except Exception as e:
        print(f"❌ Error during parsing: {e}")

if __name__ == "__main__":
    asyncio.run(test_unmatched_api())