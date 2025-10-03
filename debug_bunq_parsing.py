#!/usr/bin/env python3

import sys
import os
import csv
import io
sys.path.append('/app/backend')

from server import parse_csv_file, validate_bunq_row, parse_dutch_currency

def debug_bunq_parsing():
    """Debug BUNQ CSV parsing step by step"""
    print("🔍 Debugging BUNQ CSV Parsing...")
    
    # Test data from the review request - exact BUNQ format
    bunq_test_data = """datum,bedrag,debiteur,omschrijving
1-1-2025,€ -89,75,PHYSITRACK* PHYSITRACK,PHYSITRACK* PHYSITRACK +358208301303 GB
2-1-2025,€ 124,76,VGZ Organisatie BV,Uw ref: 202200008296 Natura decl. 103271663.
3-1-2025,€ 1.311,03,Grote Betaling BV,Grote inkomsten transactie
4-1-2025,€ -2.780,03,Grote Uitgave BV,Grote uitgaven transactie"""
    
    print("Step 1: Parse CSV file")
    rows = parse_csv_file(bunq_test_data)
    print(f"Found {len(rows)} rows")
    
    for i, row in enumerate(rows):
        print(f"\nRow {i+1}: {row}")
        
        # Check what's in the bedrag column
        bedrag_value = row.get('bedrag', '')
        print(f"  bedrag column value: '{bedrag_value}'")
        
        # Test parse_dutch_currency directly
        parsed_amount = parse_dutch_currency(bedrag_value)
        print(f"  parse_dutch_currency result: {parsed_amount}")
        
        # Test validate_bunq_row
        validation_result = validate_bunq_row(row, i+1)
        print(f"  validate_bunq_row result:")
        print(f"    mapped_data: {validation_result.mapped_data}")
        print(f"    errors: {validation_result.validation_errors}")
        print(f"    status: {validation_result.import_status}")

if __name__ == "__main__":
    debug_bunq_parsing()