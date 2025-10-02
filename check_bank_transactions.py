#!/usr/bin/env python3
"""
Check bank transactions in database
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / 'backend/.env')

async def check_bank_transactions():
    # Connect to database
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    print("🔍 Checking bank transactions in database...")
    
    # Check total count
    total_count = await db.bank_transactions.count_documents({})
    print(f"📊 Total bank transactions: {total_count}")
    
    # Check unreconciled count
    unreconciled_count = await db.bank_transactions.count_documents({"reconciled": False})
    print(f"📊 Unreconciled bank transactions: {unreconciled_count}")
    
    # Check negative transactions
    negative_count = await db.bank_transactions.count_documents({"amount": {"$lt": 0}})
    print(f"📊 Negative amount transactions: {negative_count}")
    
    # Check unreconciled negative transactions
    unreconciled_negative_count = await db.bank_transactions.count_documents({
        "reconciled": False,
        "amount": {"$lt": 0}
    })
    print(f"📊 Unreconciled negative transactions: {unreconciled_negative_count}")
    
    # Show examples of negative transactions
    if negative_count > 0:
        print(f"\n📋 Examples of negative transactions:")
        negative_transactions = await db.bank_transactions.find({"amount": {"$lt": 0}}).limit(3).to_list(3)
        for trans in negative_transactions:
            print(f"  - ID: {trans['id']}")
            print(f"    Amount: €{trans['amount']}")
            print(f"    Description: {trans['description']}")
            print(f"    Reconciled: {trans.get('reconciled', 'unknown')}")
            print(f"    Date: {trans.get('date', 'unknown')}")
            print()

if __name__ == "__main__":
    asyncio.run(check_bank_transactions())