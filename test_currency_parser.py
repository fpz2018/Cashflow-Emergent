#!/usr/bin/env python3

# Direct test of the parse_dutch_currency function
import sys
import os
sys.path.append('/app/backend')

# Import the function from server.py
from server import parse_dutch_currency

def test_parse_dutch_currency():
    """Test the parse_dutch_currency function directly"""
    print("🇳🇱 Testing parse_dutch_currency function directly...")
    
    test_cases = [
        ("€ -89,75", -89.75),
        ("€ 124,76", 124.76),
        ("€ 1.311,03", 1311.03),
        ("€ -2.780,03", -2780.03),
        ("€ -48,50", -48.50),
        ("€ 1.008,00", 1008.00),
        ("€ 2.500,75", 2500.75),
    ]
    
    all_passed = True
    
    for input_value, expected in test_cases:
        result = parse_dutch_currency(input_value)
        passed = abs(result - expected) < 0.01
        
        status = "✅" if passed else "❌"
        print(f"{status} '{input_value}' → {result} (expected {expected})")
        
        if not passed:
            all_passed = False
            print(f"   ERROR: Got {result}, expected {expected}")
    
    if all_passed:
        print("\n✅ ALL CURRENCY PARSING TESTS PASSED!")
    else:
        print("\n❌ SOME CURRENCY PARSING TESTS FAILED!")
    
    return all_passed

if __name__ == "__main__":
    test_parse_dutch_currency()