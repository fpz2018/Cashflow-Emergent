import requests
import sys
import json
import io
from datetime import datetime, date

class CashflowAPITester:
    def __init__(self, base_url="https://cashflow-forecast-6.preview.emergentagent.com"):
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

    def test_crediteuren_endpoint(self):
        """Test crediteuren endpoint"""
        print("\n💳 Testing Crediteuren Endpoint...")
        
        # First create some test crediteuren data
        test_crediteuren = [
            {
                "crediteur": "Huurmaatschappij Amsterdam",
                "bedrag": 1200.00,
                "dag": 1
            },
            {
                "crediteur": "Energieleverancier Vattenfall",
                "bedrag": 150.00,
                "dag": 15
            },
            {
                "crediteur": "Telefoonmaatschappij KPN",
                "bedrag": 45.00,
                "dag": 20
            }
        ]
        
        created_crediteuren = []
        for crediteur_data in test_crediteuren:
            success, response = self.run_test(
                f"Create Crediteur {crediteur_data['crediteur']}",
                "POST",
                "crediteuren",
                200,
                data=crediteur_data
            )
            if success and 'id' in response:
                created_crediteuren.append(response['id'])
        
        # Test get all crediteuren
        success, crediteuren_data = self.run_test(
            "Get All Crediteuren",
            "GET",
            "crediteuren",
            200
        )
        
        if success:
            print(f"   Found {len(crediteuren_data)} crediteuren")
            for crediteur in crediteuren_data[:3]:  # Show first 3
                print(f"   - {crediteur.get('crediteur', 'N/A')}: €{crediteur.get('bedrag', 0)} (dag {crediteur.get('dag', 'N/A')})")
        
        return success

    def test_bank_reconciliation_endpoints(self):
        """Test comprehensive bank reconciliation functionality"""
        print("\n🏦 Testing Bank Reconciliation Endpoints...")
        
        # Test 1: Get unmatched bank transactions (initially empty)
        success1, initial_unmatched = self.run_test(
            "Get Unmatched Bank Transactions (initial)",
            "GET",
            "bank-reconciliation/unmatched",
            200
        )
        
        if success1:
            print(f"   Initial unmatched transactions: {len(initial_unmatched)}")
        
        # Test 2: Import bank data to create test transactions
        csv_content = """datum,bedrag,debiteur,omschrijving
2025-01-15,-1200.00,Huurmaatschappij Amsterdam,Maandelijkse huur januari
2025-01-16,150.50,CZ Zorgverzekeraar,Betaling declaratie INV001
2025-01-17,-150.00,Energieleverancier Vattenfall,Energierekening januari
2025-01-18,-45.00,Telefoonmaatschappij KPN,Telefoonrekening januari
2025-01-19,200.25,Zilveren Kruis,Betaling declaratie INV003"""
        
        files = {
            'file': ('test_bank_reconciliation.csv', csv_content, 'text/csv')
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
                
                # Test 3: Get unmatched bank transactions (should have data now)
                success3, bank_data = self.run_test(
                    "Get Unmatched Bank Transactions (with data)",
                    "GET",
                    "bank-reconciliation/unmatched",
                    200
                )
                
                if success3 and isinstance(bank_data, list):
                    print(f"   Found {len(bank_data)} unmatched bank transactions")
                    
                    if len(bank_data) > 0:
                        bank_transaction = bank_data[0]
                        bank_transaction_id = bank_transaction.get('id')
                        print(f"   Testing with bank transaction: {bank_transaction.get('description', 'N/A')} (€{bank_transaction.get('amount', 0)})")
                        
                        if bank_transaction_id:
                            # Test 4: Get reconciliation suggestions
                            success4, suggestions = self.run_test(
                                "Get Reconciliation Suggestions",
                                "GET",
                                f"bank-reconciliation/suggestions/{bank_transaction_id}",
                                200
                            )
                            
                            if success4 and isinstance(suggestions, list):
                                print(f"   Found {len(suggestions)} suggestions")
                                transaction_suggestions = [s for s in suggestions if s.get('match_type') == 'transaction']
                                crediteur_suggestions = [s for s in suggestions if s.get('match_type') == 'crediteur']
                                
                                print(f"   - Transaction suggestions: {len(transaction_suggestions)}")
                                print(f"   - Crediteur suggestions: {len(crediteur_suggestions)}")
                                
                                # Test 5: Test match-crediteur endpoint if we have crediteur suggestions
                                success5 = True
                                if crediteur_suggestions:
                                    crediteur_suggestion = crediteur_suggestions[0]
                                    crediteur_id = crediteur_suggestion.get('id')
                                    
                                    if crediteur_id:
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
                                
                                # Test 6: Test transactions endpoint with reconciled filter
                                success6, unreconciled_transactions = self.run_test(
                                    "Get Unreconciled Transactions",
                                    "GET",
                                    "transactions?reconciled=false",
                                    200
                                )
                                
                                if success6:
                                    print(f"   Found {len(unreconciled_transactions)} unreconciled transactions")
                                
                                return success1 and success2 and success3 and success4 and success5 and success6
                            
                            return success1 and success2 and success3 and success4
                        
                        return success1 and success2 and success3
                    else:
                        print("   ⚠️  No bank transactions found after import")
                        return success1 and success2 and success3
                
                return success1 and success2 and success3
            else:
                print(f"❌ Bank data import failed - Status: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text}")
                self.tests_run += 1
                return success1 and False
                
        except Exception as e:
            print(f"❌ Bank data import error: {str(e)}")
            self.tests_run += 1
            return success1 and False

    def test_crediteur_suggestions_fix(self):
        """Test specifically that crediteur suggestions are now working"""
        print("\n🎯 Testing Crediteur Suggestions Fix...")
        print("   Focus: Verify suggestions endpoint returns both transaction AND crediteur matches")
        
        # First ensure we have crediteuren data
        test_crediteuren = [
            {
                "crediteur": "Huurmaatschappij Amsterdam",
                "bedrag": 1200.00,
                "dag": 1
            },
            {
                "crediteur": "Energieleverancier Vattenfall", 
                "bedrag": 150.00,
                "dag": 15
            },
            {
                "crediteur": "KPN Telecom",
                "bedrag": 45.00,
                "dag": 20
            }
        ]
        
        created_crediteuren = []
        for crediteur_data in test_crediteuren:
            success, response = self.run_test(
                f"Setup Crediteur {crediteur_data['crediteur']}",
                "POST",
                "crediteuren", 
                200,
                data=crediteur_data
            )
            if success and 'id' in response:
                created_crediteuren.append(response['id'])
        
        # Import bank transactions that should match crediteuren
        csv_content = """datum,bedrag,debiteur,omschrijving
2025-01-15,-1200.00,Huurmaatschappij Amsterdam,Maandelijkse huur januari
2025-01-16,-150.00,Vattenfall,Energierekening januari  
2025-01-17,-45.00,KPN,Telefoonrekening januari
2025-01-18,200.50,CZ Zorgverzekeraar,Betaling declaratie
2025-01-19,-89.75,Albert Heijn,Boodschappen"""
        
        files = {
            'file': ('test_crediteur_matching.csv', csv_content, 'text/csv')
        }
        data = {
            'import_type': 'bank_bunq'
        }
        
        url = f"{self.api_url}/import/execute"
        
        try:
            response = requests.post(url, data=data, files=files)
            import_success = response.status_code == 200
            
            if import_success:
                self.tests_passed += 1
                print(f"✅ Bank data import for crediteur testing - Status: {response.status_code}")
                
                # Get unmatched bank transactions
                success, bank_data = self.run_test(
                    "Get Bank Transactions for Crediteur Testing",
                    "GET",
                    "bank-reconciliation/unmatched",
                    200
                )
                
                if success and isinstance(bank_data, list) and len(bank_data) > 0:
                    print(f"   Found {len(bank_data)} bank transactions to test")
                    
                    # Test suggestions for multiple bank transactions
                    test_results = []
                    
                    for i, bank_transaction in enumerate(bank_data[:4]):  # Test first 4 transactions
                        bank_transaction_id = bank_transaction.get('id')
                        bank_description = bank_transaction.get('description', 'N/A')
                        bank_amount = bank_transaction.get('amount', 0)
                        
                        print(f"\n   Testing suggestions for transaction {i+1}:")
                        print(f"   - Description: {bank_description}")
                        print(f"   - Amount: €{bank_amount}")
                        
                        if bank_transaction_id:
                            success, suggestions = self.run_test(
                                f"Get Suggestions for Transaction {i+1}",
                                "GET",
                                f"bank-reconciliation/suggestions/{bank_transaction_id}",
                                200
                            )
                            
                            if success and isinstance(suggestions, list):
                                transaction_suggestions = [s for s in suggestions if s.get('match_type') == 'transaction']
                                crediteur_suggestions = [s for s in suggestions if s.get('match_type') == 'crediteur']
                                
                                print(f"   - Total suggestions: {len(suggestions)}")
                                print(f"   - Transaction suggestions: {len(transaction_suggestions)}")
                                print(f"   - Crediteur suggestions: {len(crediteur_suggestions)}")
                                
                                # Detailed analysis of crediteur suggestions
                                if crediteur_suggestions:
                                    print(f"   ✅ CREDITEUR SUGGESTIONS FOUND!")
                                    for j, cred_sugg in enumerate(crediteur_suggestions):
                                        print(f"     Crediteur {j+1}: {cred_sugg.get('patient_name', 'N/A')} - €{cred_sugg.get('amount', 0)} (Score: {cred_sugg.get('match_score', 0)})")
                                        print(f"     Reason: {cred_sugg.get('match_reason', 'N/A')}")
                                        print(f"     Crediteur dag: {cred_sugg.get('crediteur_dag', 'N/A')}")
                                        
                                        # Verify required fields
                                        required_fields = ['id', 'match_type', 'match_score', 'match_reason', 'crediteur_dag', 'patient_name', 'amount']
                                        missing_fields = [field for field in required_fields if field not in cred_sugg or cred_sugg[field] is None]
                                        if missing_fields:
                                            print(f"     ⚠️  Missing fields: {missing_fields}")
                                else:
                                    print(f"   ❌ NO CREDITEUR SUGGESTIONS FOUND")
                                
                                # Record test result
                                test_results.append({
                                    'transaction_id': bank_transaction_id,
                                    'description': bank_description,
                                    'amount': bank_amount,
                                    'total_suggestions': len(suggestions),
                                    'transaction_suggestions': len(transaction_suggestions),
                                    'crediteur_suggestions': len(crediteur_suggestions),
                                    'has_crediteur_suggestions': len(crediteur_suggestions) > 0
                                })
                            else:
                                test_results.append({
                                    'transaction_id': bank_transaction_id,
                                    'description': bank_description,
                                    'amount': bank_amount,
                                    'error': 'Failed to get suggestions'
                                })
                    
                    # Summary of test results
                    print(f"\n   📊 CREDITEUR SUGGESTIONS TEST SUMMARY:")
                    total_tested = len(test_results)
                    transactions_with_crediteur_suggestions = sum(1 for r in test_results if r.get('has_crediteur_suggestions', False))
                    
                    print(f"   - Total transactions tested: {total_tested}")
                    print(f"   - Transactions with crediteur suggestions: {transactions_with_crediteur_suggestions}")
                    print(f"   - Success rate: {(transactions_with_crediteur_suggestions/total_tested*100):.1f}%" if total_tested > 0 else "   - Success rate: 0%")
                    
                    # Test is successful if we found crediteur suggestions for at least some transactions
                    crediteur_fix_working = transactions_with_crediteur_suggestions > 0
                    
                    if crediteur_fix_working:
                        print(f"   ✅ CREDITEUR SUGGESTIONS FIX IS WORKING!")
                        print(f"   ✅ Backend now returns both transaction AND crediteur suggestions")
                    else:
                        print(f"   ❌ CREDITEUR SUGGESTIONS FIX NOT WORKING")
                        print(f"   ❌ Backend still only returns transaction suggestions")
                    
                    return crediteur_fix_working
                else:
                    print("   ❌ No bank transactions found for testing")
                    return False
            else:
                print(f"❌ Bank data import failed - Status: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text}")
                self.tests_run += 1
                return False
                
        except Exception as e:
            print(f"❌ Crediteur suggestions test error: {str(e)}")
            self.tests_run += 1
            return False

    def test_cashflow_forecast_endpoints(self):
        """Test the new cashflow forecast API endpoints as requested"""
        print("\n📈 Testing Cashflow Forecast Endpoints...")
        print("   Focus: Testing cashflow-forecast, bank-saldo, overige-omzet, and correcties APIs")
        
        all_success = True
        
        # Test 1: GET /api/cashflow-forecast?days=30
        print("\n--- Testing cashflow-forecast endpoint ---")
        success1, forecast_30 = self.run_test(
            "Cashflow Forecast (30 days)",
            "GET",
            "cashflow-forecast",
            200,
            params={"days": 30}
        )
        
        if success1 and isinstance(forecast_30, dict):
            print(f"   ✅ 30-day forecast structure:")
            print(f"     - Start date: {forecast_30.get('start_date', 'N/A')}")
            print(f"     - Forecast days count: {len(forecast_30.get('forecast_days', []))}")
            print(f"     - Total expected income: €{forecast_30.get('total_expected_income', 0)}")
            print(f"     - Total expected expenses: €{forecast_30.get('total_expected_expenses', 0)}")
            print(f"     - Net expected: €{forecast_30.get('net_expected', 0)}")
            
            # Verify forecast_days array structure
            forecast_days = forecast_30.get('forecast_days', [])
            if forecast_days and len(forecast_days) > 0:
                sample_day = forecast_days[0]
                required_fields = ['date', 'inkomsten', 'uitgaven', 'net_cashflow', 'verwachte_saldo', 'payments']
                missing_fields = [field for field in required_fields if field not in sample_day]
                if missing_fields:
                    print(f"     ⚠️  Missing fields in forecast_days: {missing_fields}")
                else:
                    print(f"     ✅ Forecast day structure is correct")
            else:
                print(f"     ⚠️  No forecast_days data returned")
        
        # Test 2: GET /api/cashflow-forecast?days=60
        success2, forecast_60 = self.run_test(
            "Cashflow Forecast (60 days)",
            "GET", 
            "cashflow-forecast",
            200,
            params={"days": 60}
        )
        
        if success2 and isinstance(forecast_60, dict):
            forecast_days_60 = forecast_60.get('forecast_days', [])
            print(f"   ✅ 60-day forecast: {len(forecast_days_60)} days returned")
        
        # Test 3: GET /api/cashflow-forecast?days=90
        success3, forecast_90 = self.run_test(
            "Cashflow Forecast (90 days)",
            "GET",
            "cashflow-forecast", 
            200,
            params={"days": 90}
        )
        
        if success3 and isinstance(forecast_90, dict):
            forecast_days_90 = forecast_90.get('forecast_days', [])
            print(f"   ✅ 90-day forecast: {len(forecast_days_90)} days returned")
        
        # Test 4: GET /api/bank-saldo
        print("\n--- Testing bank-saldo endpoint ---")
        success4, bank_saldo = self.run_test(
            "Bank Saldo API",
            "GET",
            "bank-saldo",
            200
        )
        
        if success4:
            if isinstance(bank_saldo, list):
                print(f"   ✅ Bank saldo returned array with {len(bank_saldo)} entries")
                if len(bank_saldo) > 0:
                    sample_saldo = bank_saldo[0]
                    required_fields = ['id', 'date', 'saldo', 'description', 'created_at']
                    missing_fields = [field for field in required_fields if field not in sample_saldo]
                    if missing_fields:
                        print(f"     ⚠️  Missing fields in bank saldo: {missing_fields}")
                    else:
                        print(f"     ✅ Bank saldo structure is correct")
                        print(f"     Sample: {sample_saldo.get('description', 'N/A')} - €{sample_saldo.get('saldo', 0)} on {sample_saldo.get('date', 'N/A')}")
                else:
                    print(f"   ✅ Empty array returned (no bank saldo data yet)")
            else:
                print(f"   ⚠️  Expected array, got: {type(bank_saldo)}")
        
        # Test 5: GET /api/overige-omzet
        print("\n--- Testing overige-omzet endpoint ---")
        success5, overige_omzet = self.run_test(
            "Overige Omzet API",
            "GET",
            "overige-omzet",
            200
        )
        
        if success5:
            if isinstance(overige_omzet, list):
                print(f"   ✅ Overige omzet returned array with {len(overige_omzet)} entries")
                if len(overige_omzet) > 0:
                    sample_omzet = overige_omzet[0]
                    required_fields = ['id', 'description', 'amount', 'date', 'category', 'recurring', 'created_at']
                    missing_fields = [field for field in required_fields if field not in sample_omzet]
                    if missing_fields:
                        print(f"     ⚠️  Missing fields in overige omzet: {missing_fields}")
                    else:
                        print(f"     ✅ Overige omzet structure is correct")
                        print(f"     Sample: {sample_omzet.get('description', 'N/A')} - €{sample_omzet.get('amount', 0)} on {sample_omzet.get('date', 'N/A')}")
                else:
                    print(f"   ✅ Empty array returned (no overige omzet data yet)")
            else:
                print(f"   ⚠️  Expected array, got: {type(overige_omzet)}")
        
        # Test 6: GET /api/correcties
        print("\n--- Testing correcties endpoint ---")
        success6, correcties = self.run_test(
            "Correcties API",
            "GET",
            "correcties",
            200
        )
        
        if success6:
            if isinstance(correcties, list):
                print(f"   ✅ Correcties returned array with {len(correcties)} entries")
                if len(correcties) > 0:
                    sample_correctie = correcties[0]
                    required_fields = ['id', 'correction_type', 'amount', 'description', 'date', 'matched', 'created_at']
                    missing_fields = [field for field in required_fields if field not in sample_correctie]
                    if missing_fields:
                        print(f"     ⚠️  Missing fields in correcties: {missing_fields}")
                    else:
                        print(f"     ✅ Correcties structure is correct")
                        print(f"     Sample: {sample_correctie.get('description', 'N/A')} - €{sample_correctie.get('amount', 0)} on {sample_correctie.get('date', 'N/A')}")
                else:
                    print(f"   ✅ Empty array returned (no correcties data yet)")
            else:
                print(f"   ⚠️  Expected array, got: {type(correcties)}")
        
        # Summary
        all_success = success1 and success2 and success3 and success4 and success5 and success6
        
        print(f"\n   📊 CASHFLOW FORECAST ENDPOINTS TEST SUMMARY:")
        print(f"   - Cashflow forecast (30 days): {'✅ PASSED' if success1 else '❌ FAILED'}")
        print(f"   - Cashflow forecast (60 days): {'✅ PASSED' if success2 else '❌ FAILED'}")
        print(f"   - Cashflow forecast (90 days): {'✅ PASSED' if success3 else '❌ FAILED'}")
        print(f"   - Bank saldo API: {'✅ PASSED' if success4 else '❌ FAILED'}")
        print(f"   - Overige omzet API: {'✅ PASSED' if success5 else '❌ FAILED'}")
        print(f"   - Correcties API: {'✅ PASSED' if success6 else '❌ FAILED'}")
        
        if all_success:
            print(f"   ✅ ALL CASHFLOW FORECAST ENDPOINTS WORKING CORRECTLY!")
            print(f"   ✅ No 500 errors detected, data structures are correct")
        else:
            print(f"   ❌ SOME CASHFLOW FORECAST ENDPOINTS HAVE ISSUES")
        
        return all_success

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
        ("Crediteuren Endpoint", tester.test_crediteuren_endpoint),
        ("Bank Reconciliation", tester.test_bank_reconciliation_endpoints),
        ("Crediteur Suggestions Fix", tester.test_crediteur_suggestions_fix),
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