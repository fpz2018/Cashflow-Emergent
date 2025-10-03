#!/usr/bin/env python3

import sys
import os
import csv
import io
sys.path.append('/app/backend')

from server import parse_csv_file, validate_bunq_row, parse_dutch_currency

def debug_bunq_parsing_fixed():
    """Debug BUNQ CSV parsing with correct semicolon delimiter"""
    print("🔍 Debugging BUNQ CSV Parsing with Semicolon Delimiter...")
    
    # Test data with semicolon delimiter (correct BUNQ format)
    bunq_test_data = """datum;bedrag;debiteur;omschrijving
1-1-2025;€ -89,75;PHYSITRACK* PHYSITRACK;PHYSITRACK* PHYSITRACK +358208301303 GB
2-1-2025;€ 124,76;VGZ Organisatie BV;Uw ref: 202200008296 Natura decl. 103271663.
3-1-2025;€ 1.311,03;Grote Betaling BV;Grote inkomsten transactie
4-1-2025;€ -2.780,03;Grote Uitgave BV;Grote uitgaven transactie"""
    
    print("Step 1: Parse CSV file with semicolon delimiter")
    rows = parse_csv_file(bunq_test_data)
    print(f"Found {len(rows)} rows")
    
    expected_amounts = [-89.75, 124.76, 1311.03, -2780.03]
    
    for i, row in enumerate(rows):
        print(f"\nRow {i+1}: {row}")
        
        # Check what's in the bedrag column
        bedrag_value = row.get('bedrag', '')
        print(f"  bedrag column value: '{bedrag_value}'")
        
        # Test parse_dutch_currency directly
        parsed_amount = parse_dutch_currency(bedrag_value)
        expected = expected_amounts[i] if i < len(expected_amounts) else 0
        print(f"  parse_dutch_currency result: {parsed_amount} (expected: {expected})")
        
        # Check if parsing is correct
        if abs(parsed_amount - expected) < 0.01:
            print(f"  ✅ CORRECT: Currency parsing working")
        else:
            print(f"  ❌ INCORRECT: Currency parsing failed")
        
        # Test validate_bunq_row
        validation_result = validate_bunq_row(row, i+1)
        print(f"  validate_bunq_row result:")
        print(f"    amount: {validation_result.mapped_data.get('amount', 'N/A')}")
        print(f"    errors: {validation_result.validation_errors}")
        print(f"    status: {validation_result.import_status}")

if __name__ == "__main__":
    debug_bunq_parsing_fixed()