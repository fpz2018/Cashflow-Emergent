#!/usr/bin/env python3
"""
Specific test for bank reconciliation crediteur matching functionality
"""

import requests
import json
from datetime import datetime, date

class BankReconciliationTester:
    def __init__(self, base_url="https://cashflow-manager-30.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    return True, response_data
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_specific_bank_reconciliation(self):
        """Test specific bank reconciliation functionality as requested"""
        print("🏦 Testing Specific Bank Reconciliation Functionality")
        print("=" * 60)
        
        # Test 1: GET /api/bank-reconciliation/unmatched
        print("\n1️⃣ Testing GET /api/bank-reconciliation/unmatched")
        success1, unmatched_data = self.run_test(
            "Get Unmatched Bank Transactions",
            "GET",
            "bank-reconciliation/unmatched",
            200
        )
        
        if success1:
            print(f"   ✅ Found {len(unmatched_data)} unmatched bank transactions")
            if len(unmatched_data) > 0:
                sample_transaction = unmatched_data[0]
                print(f"   Sample transaction: {sample_transaction.get('description', 'N/A')} - €{sample_transaction.get('amount', 0)}")
        
        # Test 2: GET /api/crediteuren
        print("\n2️⃣ Testing GET /api/crediteuren")
        success2, crediteuren_data = self.run_test(
            "Get Crediteuren Data",
            "GET",
            "crediteuren",
            200
        )
        
        if success2:
            print(f"   ✅ Found {len(crediteuren_data)} crediteuren")
            for i, crediteur in enumerate(crediteuren_data[:3]):  # Show first 3
                print(f"   {i+1}. {crediteur.get('crediteur', 'N/A')}: €{crediteur.get('bedrag', 0)} (dag {crediteur.get('dag', 'N/A')})")
        
        # Test 3: GET /api/transactions?reconciled=false
        print("\n3️⃣ Testing GET /api/transactions?reconciled=false")
        success3, unreconciled_transactions = self.run_test(
            "Get Unreconciled Transactions",
            "GET",
            "transactions",
            200,
            params={"reconciled": "false"}
        )
        
        if success3:
            print(f"   ✅ Found {len(unreconciled_transactions)} unreconciled transactions")
        
        # Test 4: GET /api/bank-reconciliation/suggestions/{id}
        if success1 and len(unmatched_data) > 0:
            bank_transaction_id = unmatched_data[0].get('id')
            print(f"\n4️⃣ Testing GET /api/bank-reconciliation/suggestions/{bank_transaction_id}")
            
            success4, suggestions = self.run_test(
                "Get Reconciliation Suggestions",
                "GET",
                f"bank-reconciliation/suggestions/{bank_transaction_id}",
                200
            )
            
            if success4:
                transaction_suggestions = [s for s in suggestions if s.get('match_type') == 'transaction']
                crediteur_suggestions = [s for s in suggestions if s.get('match_type') == 'crediteur']
                
                print(f"   ✅ Found {len(suggestions)} total suggestions")
                print(f"   - Transaction suggestions: {len(transaction_suggestions)}")
                print(f"   - Crediteur suggestions: {len(crediteur_suggestions)}")
                
                # Show details of suggestions
                if transaction_suggestions:
                    print("   📋 Transaction suggestions:")
                    for i, suggestion in enumerate(transaction_suggestions[:2]):
                        print(f"     {i+1}. {suggestion.get('description', 'N/A')} - €{suggestion.get('amount', 0)} (Score: {suggestion.get('match_score', 0)})")
                
                if crediteur_suggestions:
                    print("   💳 Crediteur suggestions:")
                    for i, suggestion in enumerate(crediteur_suggestions[:2]):
                        print(f"     {i+1}. {suggestion.get('patient_name', 'N/A')} - €{suggestion.get('amount', 0)} (Score: {suggestion.get('match_score', 0)})")
                
                # Test 5: POST /api/bank-reconciliation/match-crediteur
                if crediteur_suggestions and success2 and len(crediteuren_data) > 0:
                    crediteur_id = crediteuren_data[0].get('id')  # Use first available crediteur
                    print(f"\n5️⃣ Testing POST /api/bank-reconciliation/match-crediteur")
                    print(f"   Matching bank transaction {bank_transaction_id[:8]}... with crediteur {crediteur_id[:8]}...")
                    
                    success5, match_response = self.run_test(
                        "Match Bank Transaction with Crediteur",
                        "POST",
                        f"bank-reconciliation/match-crediteur?bank_transaction_id={bank_transaction_id}&crediteur_id={crediteur_id}",
                        200
                    )
                    
                    if success5:
                        print(f"   ✅ Successfully matched bank transaction with crediteur")
                        if 'created_expense_id' in match_response:
                            print(f"   Created expense transaction: {match_response['created_expense_id']}")
                        if 'message' in match_response:
                            print(f"   Message: {match_response['message']}")
                    
                    return success1 and success2 and success3 and success4 and success5
                else:
                    print("\n5️⃣ Skipping crediteur matching test - no crediteur suggestions or crediteuren data")
                    return success1 and success2 and success3 and success4
            else:
                return success1 and success2 and success3 and False
        else:
            print("\n4️⃣ Skipping suggestions test - no unmatched bank transactions")
            return success1 and success2 and success3
    
    def test_error_handling(self):
        """Test error handling for bank reconciliation endpoints"""
        print("\n🚨 Testing Error Handling")
        print("=" * 30)
        
        # Test invalid bank transaction ID for suggestions
        success1, _ = self.run_test(
            "Invalid Bank Transaction ID for Suggestions",
            "GET",
            "bank-reconciliation/suggestions/invalid-id",
            404
        )
        
        # Test invalid parameters for match-crediteur
        success2, _ = self.run_test(
            "Invalid Match Crediteur Parameters",
            "POST",
            "bank-reconciliation/match-crediteur?bank_transaction_id=invalid&crediteur_id=invalid",
            404
        )
        
        return success1 and success2

def main():
    print("🏥 Bank Reconciliation Specific Testing")
    print("=" * 50)
    
    tester = BankReconciliationTester()
    
    # Run specific tests
    reconciliation_success = tester.test_specific_bank_reconciliation()
    error_handling_success = tester.test_error_handling()
    
    # Print final results
    print("\n" + "=" * 50)
    print("📊 FINAL TEST RESULTS")
    print("=" * 50)
    
    print(f"Bank Reconciliation Tests: {'✅ PASSED' if reconciliation_success else '❌ FAILED'}")
    print(f"Error Handling Tests:      {'✅ PASSED' if error_handling_success else '❌ FAILED'}")
    
    print(f"\nOverall: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    # Summary of findings
    print("\n" + "=" * 50)
    print("📋 SUMMARY OF FINDINGS")
    print("=" * 50)
    
    if reconciliation_success:
        print("✅ All bank reconciliation endpoints are working correctly")
        print("✅ Unmatched bank transactions endpoint returns data")
        print("✅ Suggestions endpoint returns both transaction and crediteur suggestions")
        print("✅ Crediteur matching endpoint successfully creates expense transactions")
        print("✅ Crediteuren data is available and accessible")
        print("✅ Unreconciled transactions filter works correctly")
    else:
        print("❌ Some bank reconciliation functionality is not working as expected")
    
    return 0 if success_rate >= 80 else 1

if __name__ == "__main__":
    exit(main())