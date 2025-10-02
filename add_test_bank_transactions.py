#!/usr/bin/env python3
"""
Script om test uitgaande bank transacties toe te voegen voor crediteur matching
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path
import uuid
from datetime import date, datetime, timezone

# Load environment
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / 'backend/.env')

async def add_test_bank_transactions():
    # Connect to database
    mongo_url = os.environ['MONGO_URL']
    client = AsyncIOMotorClient(mongo_url)
    db = client[os.environ['DB_NAME']]
    
    # Test uitgaande transacties die matchen met bestaande crediteuren
    test_transactions = [
        {
            "id": str(uuid.uuid4()),
            "date": "2025-10-02",
            "amount": -4696.97,  # Exact match met CPEP Vastgoedexploitatie
            "original_amount": -4696.97,
            "description": "SEPA Incasso CPEP Vastgoedexploitatie huur oktober",
            "counterparty": "CPEP VASTGOEDEXPLOITATIE",
            "account_number": "NL91ABNA0417164300",
            "bank_date": "2025-10-02",
            "reconciled": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "date": "2025-10-01",
            "amount": -485.95,  # Exact match met MONITORED REHAB SYSTEMS
            "original_amount": -485.95,
            "description": "Betaling factuur MONITORED REHAB SYSTEMS software",
            "counterparty": "MONITORED REHAB SYSTEMS BV",
            "account_number": "NL91ABNA0417164300",
            "bank_date": "2025-10-01", 
            "reconciled": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "date": "2025-09-28",
            "amount": -80.00,  # Exact match met X2Com
            "original_amount": -80.00,
            "description": "Maandelijkse betaling X2Com internetdiensten",
            "counterparty": "X2COM",
            "account_number": "NL91ABNA0417164300",
            "bank_date": "2025-09-28",
            "reconciled": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "date": "2025-09-19", 
            "amount": -86.82,  # Exact match met ZIGGO ZAKELIJK
            "original_amount": -86.82,
            "description": "ZIGGO ZAKELIJK maandabonnement september",
            "counterparty": "ZIGGO ZAKELIJK SERVICES BV",
            "account_number": "NL91ABNA0417164300", 
            "bank_date": "2025-09-19",
            "reconciled": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "date": "2025-09-25",
            "amount": -120.50,  # Geen exacte match, maar wel uitgave
            "original_amount": -120.50,
            "description": "Algemene kantoorkosten september",
            "counterparty": "DIVERSE LEVERANCIERS",
            "account_number": "NL91ABNA0417164300",
            "bank_date": "2025-09-25",
            "reconciled": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    
    print(f"Toevoegen van {len(test_transactions)} test uitgaande bank transacties...")
    
    # Insert test transactions
    result = await db.bank_transactions.insert_many(test_transactions)
    
    print(f"✅ Succesvol {len(result.inserted_ids)} uitgaande bank transacties toegevoegd")
    
    # Verify insertion
    count = await db.bank_transactions.count_documents({"amount": {"$lt": 0}})
    print(f"✅ Totaal aantal negatieve bank transacties in database: {count}")
    
    # Show some examples
    negative_transactions = await db.bank_transactions.find({"amount": {"$lt": 0}}).limit(3).to_list(3)
    print("\n📋 Voorbeelden van toegevoegde transacties:")
    for trans in negative_transactions:
        print(f"  - {trans['description']}: €{trans['amount']} ({trans['counterparty']})")

if __name__ == "__main__":
    asyncio.run(add_test_bank_transactions())