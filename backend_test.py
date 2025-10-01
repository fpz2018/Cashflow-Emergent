import requests
import sys
import json
import io
from datetime import datetime, date

class CashflowAPITester:
    def __init__(self, base_url="https://health-cash-pulse.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.created_transactions = []

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
                    if method == 'POST' and 'id' in response_data:
                        print(f"   Created ID: {response_data['id']}")
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

    def test_api_root(self):
        """Test API root endpoint"""
        return self.run_test("API Root", "GET", "", 200)

    def test_categories(self):
        """Test category endpoints"""
        print("\n📋 Testing Category Endpoints...")
        
        # Test income categories
        success1, income_cats = self.run_test("Income Categories", "GET", "categories/income", 200)
        if success1:
            expected_income = ['zorgverzekeraar', 'particulier', 'fysiofitness', 'orthomoleculair', 'credit_declaratie', 'creditfactuur']
            if all(cat in income_cats for cat in expected_income):
                print("   ✅ All expected income categories found")
            else:
                print(f"   ⚠️  Missing income categories: {set(expected_income) - set(income_cats)}")

        # Test expense categories  
        success2, expense_cats = self.run_test("Expense Categories", "GET", "categories/expense", 200)
        if success2:
            expected_expense = ['huur', 'materiaal', 'salaris', 'overig']
            if all(cat in expense_cats for cat in expected_expense):
                print("   ✅ All expected expense categories found")
            else:
                print(f"   ⚠️  Missing expense categories: {set(expected_expense) - set(expense_cats)}")

        return success1 and success2

    def test_create_transactions(self):
        """Test creating transactions with different categories and types"""
        print("\n💰 Testing Transaction Creation...")
        
        test_transactions = [
            {
                "type": "income",
                "category": "zorgverzekeraar", 
                "amount": 150.50,
                "description": "Fysiotherapie behandeling",
                "date": "2024-01-15",
                "patient_name": "Jan Jansen",
                "invoice_number": "INV-001"
            },
            {
                "type": "income",
                "category": "particulier",
                "amount": 75.00,
                "description": "Particuliere behandeling",
                "date": "2024-01-15",
                "patient_name": "Marie Pietersen"
            },
            {
                "type": "income", 
                "category": "fysiofitness",
                "amount": 45.00,
                "description": "FysioFitness sessie",
                "date": "2024-01-15"
            },
            {
                "type": "expense",
                "category": "huur",
                "amount": 1200.00,
                "description": "Maandelijkse huur praktijk",
                "date": "2024-01-15"
            },
            {
                "type": "credit",
                "category": "zorgverzekeraar",
                "amount": 25.00,
                "description": "Credit declaratie correctie",
                "date": "2024-01-15"
            }
        ]

        all_success = True
        for i, transaction in enumerate(test_transactions):
            success, response = self.run_test(
                f"Create Transaction {i+1} ({transaction['category']})",
                "POST", 
                "transactions",
                200,
                data=transaction
            )
            if success and 'id' in response:
                self.created_transactions.append(response['id'])
            all_success = all_success and success

        return all_success

    def test_get_transactions(self):
        """Test retrieving transactions"""
        print("\n📋 Testing Transaction Retrieval...")
        
        # Get all transactions
        success1, transactions = self.run_test("Get All Transactions", "GET", "transactions", 200)
        if success1:
            print(f"   Found {len(transactions)} transactions")

        # Test with filters
        success2, _ = self.run_test("Get Transactions by Category", "GET", "transactions", 200, 
                                   params={"category": "zorgverzekeraar"})
        
        success3, _ = self.run_test("Get Transactions by Type", "GET", "transactions", 200,
                                   params={"type": "income"})

        success4, _ = self.run_test("Get Transactions by Date Range", "GET", "transactions", 200,
                                   params={"start_date": "2024-01-01", "end_date": "2024-01-31"})

        return success1 and success2 and success3 and success4

    def test_individual_transaction(self):
        """Test getting individual transaction"""
        if not self.created_transactions:
            print("⚠️  No transactions to test individual retrieval")
            return True

        transaction_id = self.created_transactions[0]
        return self.run_test(f"Get Transaction {transaction_id}", "GET", f"transactions/{transaction_id}", 200)[0]

    def test_update_transaction(self):
        """Test updating a transaction"""
        if not self.created_transactions:
            print("⚠️  No transactions to test update")
            return True

        transaction_id = self.created_transactions[0]
        update_data = {
            "amount": 175.75,
            "description": "Updated fysiotherapie behandeling",
            "notes": "Updated via API test"
        }

        return self.run_test(f"Update Transaction {transaction_id}", "PUT", f"transactions/{transaction_id}", 200, data=update_data)[0]

    def test_cashflow_endpoints(self):
        """Test cashflow calculation endpoints"""
        print("\n📊 Testing Cashflow Endpoints...")
        
        # Test daily cashflow
        today = date.today().isoformat()
        success1, daily_data = self.run_test("Daily Cashflow", "GET", f"cashflow/daily/{today}", 200)
        if success1:
            print(f"   Daily net cashflow: €{daily_data.get('net_cashflow', 0)}")
            print(f"   Transactions count: {daily_data.get('transactions_count', 0)}")

        # Test cashflow summary
        success2, summary_data = self.run_test("Cashflow Summary", "GET", "cashflow/summary", 200)
        if success2:
            print(f"   Today's net: €{summary_data.get('today', {}).get('net_cashflow', 0)}")
            print(f"   Total transactions: {summary_data.get('total_transactions', 0)}")

        return success1 and success2

    def test_delete_transaction(self):
        """Test deleting a transaction"""
        if not self.created_transactions:
            print("⚠️  No transactions to test deletion")
            return True

        # Keep one transaction, delete the rest for cleanup
        transaction_id = self.created_transactions[-1]
        success = self.run_test(f"Delete Transaction {transaction_id}", "DELETE", f"transactions/{transaction_id}", 200)[0]
        
        if success:
            self.created_transactions.remove(transaction_id)
        
        return success

    def create_test_csv(self, import_type):
        """Create test CSV content for different import types"""
        if import_type == 'epd_declaraties':
            csv_content = """factuur,datum,verzekeraar,bedrag
INV001,2025-01-15,CZ Zorgverzekeraar,150.50
INV002,2025-01-16,VGZ,75.00
INV003,2025-01-17,Zilveren Kruis,200.25"""
        elif import_type == 'epd_particulier':
            csv_content = """factuur,datum,debiteur,bedrag
PART001,2025-01-15,Jan de Vries,85.00
PART002,2025-01-16,Marie Jansen,120.50
PART003,2025-01-17,Piet Bakker,95.75"""
        elif import_type == 'bank_bunq':
            csv_content = """Date,Amount,Counterparty,Description,Account
2025-01-15,150.50,CZ Zorgverzekeraar,Betaling declaratie INV001,NL91BUNQ0123456789
2025-01-16,-45.00,Office Supplies BV,Kantoormateriaal,NL91BUNQ0123456789
2025-01-17,200.25,Zilveren Kruis,Betaling declaratie INV003,NL91BUNQ0123456789"""
        else:
            return ""
        
        return csv_content

    def test_import_preview_endpoints(self):
        """Test import preview functionality"""
        print("\n📤 Testing Import Preview Endpoints...")
        
        import_types = ['epd_declaraties', 'epd_particulier', 'bank_bunq']
        all_success = True
        
        for import_type in import_types:
            print(f"\n--- Testing {import_type} import preview ---")
            
            # Create test CSV
            csv_content = self.create_test_csv(import_type)
            
            # Test preview endpoint with multipart form data
            files = {
                'file': ('test.csv', csv_content, 'text/csv')
            }
            data = {
                'import_type': import_type
            }
            
            url = f"{self.api_url}/import/preview"
            print(f"   URL: {url}")
            
            try:
                response = requests.post(url, data=data, files=files)
                success = response.status_code == 200
                
                if success:
                    self.tests_passed += 1
                    print(f"✅ Passed - Status: {response.status_code}")
                    try:
                        response_data = response.json()
                        print(f"  📊 Preview results:")
                        print(f"    - Total rows: {response_data.get('total_rows', 0)}")
                        print(f"    - Valid rows: {response_data.get('valid_rows', 0)}")
                        print(f"    - Error rows: {response_data.get('error_rows', 0)}")
                        print(f"    - File name: {response_data.get('file_name', 'N/A')}")
                    except:
                        pass
                else:
                    print(f"❌ Failed - Expected 200, got {response.status_code}")
                    try:
                        print(f"   Error: {response.json()}")
                    except:
                        print(f"   Response: {response.text}")
                    all_success = False
                
                self.tests_run += 1
                
            except Exception as e:
                print(f"❌ Failed - Error: {str(e)}")
                all_success = False
                self.tests_run += 1
        
        return all_success

    def test_import_execute_endpoints(self):
        """Test import execution functionality"""
        print("\n⚡ Testing Import Execute Endpoints...")
        
        # Test EPD declaraties import
        csv_content = self.create_test_csv('epd_declaraties')
        files = {
            'file': ('test_declaraties.csv', csv_content, 'text/csv')
        }
        data = {
            'import_type': 'epd_declaraties'
        }
        
        url = f"{self.api_url}/import/execute"
        print(f"   URL: {url}")
        
        try:
            response = requests.post(url, data=data, files=files)
            success = response.status_code == 200
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"  📊 Import results:")
                    print(f"    - Success: {response_data.get('success', False)}")
                    print(f"    - Imported count: {response_data.get('imported_count', 0)}")
                    print(f"    - Error count: {response_data.get('error_count', 0)}")
                    print(f"    - Created transactions: {len(response_data.get('created_transactions', []))}")
                except:
                    pass
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                try:
                    print(f"   Error: {response.json()}")
                except:
                    print(f"   Response: {response.text}")
            
            self.tests_run += 1
            return success
            
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.tests_run += 1
            return False

    def test_bank_reconciliation_endpoints(self):
        """Test bank reconciliation functionality"""
        print("\n🏦 Testing Bank Reconciliation Endpoints...")
        
        # Test get unmatched bank transactions
        success1, _ = self.run_test(
            "Get Unmatched Bank Transactions",
            "GET",
            "bank-reconciliation/unmatched",
            200
        )
        
        # First import some bank data to test reconciliation
        csv_content = self.create_test_csv('bank_bunq')
        files = {
            'file': ('test_bank.csv', csv_content, 'text/csv')
        }
        data = {
            'import_type': 'bank_bunq'
        }
        
        url = f"{self.api_url}/import/execute"
        
        try:
            response = requests.post(url, data=data, files=files)
            success2 = response.status_code == 200
            
            if success2:
                self.tests_passed += 1
                print(f"✅ Bank data import - Status: {response.status_code}")
                
                # Test get unmatched again (should have data now)
                success3, bank_data = self.run_test(
                    "Get Unmatched Bank Transactions (with data)",
                    "GET",
                    "bank-reconciliation/unmatched",
                    200
                )
                
                if success3 and isinstance(bank_data, list) and len(bank_data) > 0:
                    bank_transaction_id = bank_data[0].get('id')
                    if bank_transaction_id:
                        # Test suggestions endpoint
                        success4, _ = self.run_test(
                            "Get Reconciliation Suggestions",
                            "GET",
                            f"bank-reconciliation/suggestions/{bank_transaction_id}",
                            200
                        )
                        return success1 and success2 and success3 and success4
                
                return success1 and success2 and success3
            else:
                print(f"❌ Bank data import failed - Status: {response.status_code}")
                self.tests_run += 1
                return success1 and False
                
        except Exception as e:
            print(f"❌ Bank data import error: {str(e)}")
            self.tests_run += 1
            return success1 and False

    def test_error_handling(self):
        """Test error handling"""
        print("\n🚨 Testing Error Handling...")
        
        # Test invalid transaction creation
        invalid_transaction = {
            "type": "income",
            "category": "",  # Missing category
            "amount": -50,   # Negative amount
            "description": "",  # Missing description
            "date": "invalid-date"
        }
        
        success1 = self.run_test("Invalid Transaction Creation", "POST", "transactions", 422, data=invalid_transaction)[0]
        
        # Test non-existent transaction
        success2 = self.run_test("Non-existent Transaction", "GET", "transactions/non-existent-id", 404)[0]
        
        # Test invalid date format
        success3 = self.run_test("Invalid Date Format", "GET", "cashflow/daily/invalid-date", 422)[0]
        
        # Test invalid import type
        csv_content = "test,data\n1,2"
        files = {
            'file': ('test.csv', csv_content, 'text/csv')
        }
        data = {
            'import_type': 'invalid_type'
        }
        
        url = f"{self.api_url}/import/preview"
        
        try:
            response = requests.post(url, data=data, files=files)
            success4 = response.status_code == 400
            if success4:
                self.tests_passed += 1
                print(f"✅ Invalid Import Type - Status: {response.status_code}")
            else:
                print(f"❌ Invalid Import Type - Expected 400, got {response.status_code}")
            self.tests_run += 1
        except Exception as e:
            print(f"❌ Invalid Import Type error: {str(e)}")
            success4 = False
            self.tests_run += 1
        
        return success1 and success2 and success3 and success4

def main():
    print("🏥 Starting Fysiotherapie Cashflow API Tests")
    print("=" * 50)
    
    tester = CashflowAPITester()
    
    # Run all tests
    tests = [
        ("API Root", tester.test_api_root),
        ("Categories", tester.test_categories),
        ("Create Transactions", tester.test_create_transactions),
        ("Get Transactions", tester.test_get_transactions),
        ("Individual Transaction", tester.test_individual_transaction),
        ("Update Transaction", tester.test_update_transaction),
        ("Cashflow Endpoints", tester.test_cashflow_endpoints),
        ("Import Preview", tester.test_import_preview_endpoints),
        ("Import Execute", tester.test_import_execute_endpoints),
        ("Bank Reconciliation", tester.test_bank_reconciliation_endpoints),
        ("Delete Transaction", tester.test_delete_transaction),
        ("Error Handling", tester.test_error_handling)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            results[test_name] = False
    
    # Print final results
    print("\n" + "=" * 50)
    print("📊 FINAL TEST RESULTS")
    print("=" * 50)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:<25} {status}")
    
    print(f"\nOverall: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    # Cleanup remaining transactions
    if tester.created_transactions:
        print(f"\n🧹 Cleaning up {len(tester.created_transactions)} remaining transactions...")
        for transaction_id in tester.created_transactions:
            tester.run_test(f"Cleanup {transaction_id}", "DELETE", f"transactions/{transaction_id}", 200)
    
    success_rate = (tester.tests_passed / tester.tests_run * 100) if tester.tests_run > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    return 0 if success_rate >= 80 else 1

if __name__ == "__main__":
    sys.exit(main())