from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, date, timezone, timedelta
from enum import Enum
import csv
import io
from decimal import Decimal, InvalidOperation


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Fysiotherapie Cashflow API")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Enums
class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    CREDIT = "credit"
    CORRECTION = "correction"

class IncomeCategory(str, Enum):
    ZORGVERZEKERAAR = "zorgverzekeraar"
    PARTICULIER = "particulier"  
    FYSIOFITNESS = "fysiofitness"
    ORTHOMOLECULAIR = "orthomoleculair"
    CREDIT_DECLARATIE = "credit_declaratie"
    CREDITFACTUUR = "creditfactuur"

class ExpenseCategory(str, Enum):
    HUUR = "huur"
    MATERIAAL = "materiaal"
    SALARIS = "salaris"
    OVERIG = "overig"

# Helper functions
def prepare_for_mongo(data):
    """Convert date/datetime objects to ISO strings for MongoDB storage"""
    if isinstance(data.get('date'), date):
        data['date'] = data['date'].isoformat()
    if isinstance(data.get('created_at'), datetime):
        data['created_at'] = data['created_at'].isoformat()
    return data

def parse_from_mongo(item):
    """Parse date/datetime strings from MongoDB back to Python objects"""
    if isinstance(item.get('date'), str):
        item['date'] = datetime.fromisoformat(item['date']).date()
    if isinstance(item.get('created_at'), str):
        item['created_at'] = datetime.fromisoformat(item['created_at'])
    return item

# Models
class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: TransactionType
    category: str  # Will be IncomeCategory or ExpenseCategory based on type
    amount: float
    description: str
    date: date
    patient_name: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    reconciled: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TransactionCreate(BaseModel):
    type: TransactionType
    category: str
    amount: float
    description: str
    date: date
    patient_name: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None

class TransactionUpdate(BaseModel):
    type: Optional[TransactionType] = None
    category: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    date: Optional[date] = None
    patient_name: Optional[str] = None
    invoice_number: Optional[str] = None
    notes: Optional[str] = None
    reconciled: Optional[bool] = None

class DailyCashflow(BaseModel):
    date: date
    total_income: float
    total_expenses: float
    net_cashflow: float
    transactions_count: int
    income_by_category: dict
    expense_by_category: dict

class CashflowSummary(BaseModel):
    today: DailyCashflow
    this_week: float
    this_month: float
    total_transactions: int

# Import Models
class ImportPreviewItem(BaseModel):
    row_number: int
    mapped_data: Dict[str, Any]
    validation_errors: List[str]
    import_status: str  # 'valid', 'warning', 'error'

class ImportPreview(BaseModel):
    file_name: str
    import_type: str  # 'epd_declaraties', 'epd_particulier', 'bank_bunq'
    total_rows: int
    valid_rows: int
    error_rows: int
    preview_items: List[ImportPreviewItem]
    column_mapping: Dict[str, str]
    all_errors: Optional[List[str]] = []  # All validation errors for debugging

class ImportResult(BaseModel):
    success: bool
    imported_count: int
    error_count: int
    errors: List[str]
    created_transactions: List[str]  # List of transaction IDs

class BankReconciliation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bank_transaction_id: str
    bank_date: date
    bank_amount: float
    bank_description: str
    matched_transaction_id: Optional[str] = None
    reconciliation_status: str  # 'unmatched', 'matched', 'ignored'
    match_confidence: float = 0.0  # 0-1 score
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class BankTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: date
    amount: float
    description: str
    counterparty: Optional[str] = None
    account_number: Optional[str] = None
    reconciled: bool = False

# Nieuwe models voor verzekeraars en crediteuren
class Verzekeraar(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    naam: str
    termijn: int  # Betaaltermijn in dagen
    actief: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class VerzekeraarCreate(BaseModel):
    naam: str
    termijn: int

class Crediteur(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    crediteur: str
    bedrag: float
    dag: int  # Dag van de maand (1-31)
    actief: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CrediteurCreate(BaseModel):
    crediteur: str
    bedrag: float
    dag: int

class CopyPasteImportRequest(BaseModel):
    data: str  # Raw copy-paste data
    import_type: str  # 'verzekeraars' of 'crediteuren'

class CopyPasteImportResult(BaseModel):
    success: bool
    imported_count: int
    error_count: int
    errors: List[str]
    preview_data: List[Dict[str, Any]]

class VerwachteBetaling(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    transaction_id: Optional[str] = None  # Link naar declaratie
    crediteur_id: Optional[str] = None    # Link naar crediteur
    type: str  # 'declaratie' of 'crediteur'
    beschrijving: str
    bedrag: float
    verwachte_datum: date
    status: str = 'open'  # 'open', 'betaald', 'overdue'
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Transaction endpoints
@api_router.post("/transactions", response_model=Transaction)
async def create_transaction(transaction: TransactionCreate):
    """Create a new transaction"""
    transaction_dict = transaction.dict()
    transaction_obj = Transaction(**transaction_dict)
    
    # Prepare for MongoDB storage
    mongo_dict = prepare_for_mongo(transaction_obj.dict())
    
    try:
        await db.transactions.insert_one(mongo_dict)
        return transaction_obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating transaction: {str(e)}")

@api_router.get("/transactions", response_model=List[Transaction])
async def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    type: Optional[TransactionType] = None
):
    """Get transactions with optional filters"""
    query = {}
    
    # Date range filter
    if start_date or end_date:
        date_query = {}
        if start_date:
            date_query["$gte"] = start_date
        if end_date:
            date_query["$lte"] = end_date
        query["date"] = date_query
    
    # Category filter
    if category:
        query["category"] = category
    
    # Type filter
    if type:
        query["type"] = type
    
    try:
        transactions = await db.transactions.find(query).sort("date", -1).to_list(1000)
        return [Transaction(**parse_from_mongo(trans)) for trans in transactions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transactions: {str(e)}")

@api_router.get("/transactions/{transaction_id}", response_model=Transaction)
async def get_transaction(transaction_id: str):
    """Get a specific transaction"""
    try:
        transaction = await db.transactions.find_one({"id": transaction_id})
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return Transaction(**parse_from_mongo(transaction))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transaction: {str(e)}")

@api_router.put("/transactions/{transaction_id}", response_model=Transaction)
async def update_transaction(transaction_id: str, update_data: TransactionUpdate):
    """Update a transaction"""
    try:
        # Remove None values from update data
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            raise HTTPException(status_code=400, detail="No update data provided")
        
        # Prepare dates for MongoDB
        update_dict = prepare_for_mongo(update_dict)
        
        result = await db.transactions.update_one(
            {"id": transaction_id},
            {"$set": update_dict}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Return updated transaction
        updated_transaction = await db.transactions.find_one({"id": transaction_id})
        return Transaction(**parse_from_mongo(updated_transaction))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating transaction: {str(e)}")

@api_router.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str):
    """Delete a transaction"""
    try:
        result = await db.transactions.delete_one({"id": transaction_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Transaction not found")
        return {"message": "Transaction deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting transaction: {str(e)}")

# Cashflow calculation endpoints
@api_router.get("/cashflow/daily/{date}", response_model=DailyCashflow)
async def get_daily_cashflow(date: str):
    """Get cashflow for a specific date"""
    try:
        # Validate date format
        try:
            datetime.fromisoformat(date)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date format. Use YYYY-MM-DD")
            
        # Get transactions for the date
        transactions = await db.transactions.find({"date": date}).to_list(1000)
        
        total_income = 0
        total_expenses = 0
        income_by_category = {}
        expense_by_category = {}
        
        for trans in transactions:
            amount = trans.get('amount', 0)
            category = trans.get('category', '')
            trans_type = trans.get('type', '')
            
            if trans_type == 'income':
                total_income += amount
                income_by_category[category] = income_by_category.get(category, 0) + amount
            elif trans_type == 'expense':
                total_expenses += amount
                expense_by_category[category] = expense_by_category.get(category, 0) + amount
            elif trans_type == 'credit':
                # Credits reduce income
                total_income -= amount
                income_by_category[category] = income_by_category.get(category, 0) - amount
        
        return DailyCashflow(
            date=datetime.fromisoformat(date).date(),
            total_income=total_income,
            total_expenses=total_expenses,
            net_cashflow=total_income - total_expenses,
            transactions_count=len(transactions),
            income_by_category=income_by_category,
            expense_by_category=expense_by_category
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating daily cashflow: {str(e)}")

@api_router.get("/cashflow/summary", response_model=CashflowSummary)
async def get_cashflow_summary():
    """Get cashflow summary with today, this week, and this month"""
    try:
        today = date.today()
        today_str = today.isoformat()
        
        # Get today's cashflow
        today_cashflow = await get_daily_cashflow(today_str)
        
        # Calculate week and month totals (simplified for now)
        total_transactions = await db.transactions.count_documents({})
        
        return CashflowSummary(
            today=today_cashflow,
            this_week=today_cashflow.net_cashflow * 7,  # Simplified
            this_month=today_cashflow.net_cashflow * 30,  # Simplified  
            total_transactions=total_transactions
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting cashflow summary: {str(e)}")

# Category endpoints
@api_router.get("/categories/income")
async def get_income_categories():
    """Get available income categories"""
    return [category.value for category in IncomeCategory]

@api_router.get("/categories/expense")
async def get_expense_categories():
    """Get available expense categories"""
    return [category.value for category in ExpenseCategory]

# Copy-paste parsing functions
def parse_copy_paste_data(data: str, expected_columns: List[str]) -> List[Dict[str, str]]:
    """Parse copy-paste data (tab/space separated) into structured format"""
    lines = [line.strip() for line in data.strip().split('\n') if line.strip()]
    
    if not lines:
        raise HTTPException(status_code=400, detail="Geen data gevonden")
    
    # Try different delimiters
    delimiters = ['\t', ';', ',', '  ', ' ']
    
    for delimiter in delimiters:
        try:
            parsed_data = []
            for i, line in enumerate(lines):
                if delimiter == '  ':  # Multiple spaces
                    parts = [p.strip() for p in line.split() if p.strip()]
                else:
                    parts = [p.strip() for p in line.split(delimiter)]
                
                # Filter out empty parts but keep parts that might be intentionally empty (like "-")
                filtered_parts = []
                for part in parts:
                    if part.strip() or part == '-':  # Keep non-empty parts or explicit dashes
                        filtered_parts.append(part.strip() if part.strip() else part)
                
                if len(filtered_parts) == len(expected_columns):
                    row_dict = {expected_columns[j]: filtered_parts[j] for j in range(len(filtered_parts))}
                    parsed_data.append(row_dict)
                elif len(filtered_parts) > len(expected_columns):
                    # If we have more parts than expected, try to combine some (useful for names with spaces)
                    if len(expected_columns) >= 2:
                        # Combine extra parts into the first column (usually name)
                        combined_first = ' '.join(filtered_parts[:-(len(expected_columns)-1)])
                        remaining_parts = filtered_parts[-(len(expected_columns)-1):]
                        final_parts = [combined_first] + remaining_parts
                        
                        if len(final_parts) == len(expected_columns):
                            row_dict = {expected_columns[j]: final_parts[j] for j in range(len(final_parts))}
                            parsed_data.append(row_dict)
            
            if len(parsed_data) > 0:
                return parsed_data
                
        except Exception:
            continue
    
    # If no delimiter worked, treat as space-separated with smart combination
    parsed_data = []
    for line in lines:
        parts = [p for p in line.split() if p]
        if len(parts) >= len(expected_columns):
            if len(parts) == len(expected_columns):
                row_dict = {expected_columns[j]: parts[j] for j in range(len(expected_columns))}
            else:
                # Combine extra parts into first column
                combined_first = ' '.join(parts[:-(len(expected_columns)-1)])
                remaining_parts = parts[-(len(expected_columns)-1):]
                final_parts = [combined_first] + remaining_parts
                row_dict = {expected_columns[j]: final_parts[j] for j in range(len(expected_columns))}
            parsed_data.append(row_dict)
    
    return parsed_data

def validate_verzekeraar_data(data: Dict[str, str], row_number: int) -> ImportPreviewItem:
    """Validate verzekeraar copy-paste data"""
    errors = []
    mapped_data = {}
    
    try:
        # Validate naam
        naam = data.get('naam', '').strip()
        if not naam:
            errors.append('Naam is verplicht')
        else:
            mapped_data['naam'] = naam
        
        # Validate termijn
        termijn_str = data.get('termijn', '').strip()
        if not termijn_str:
            errors.append('Termijn is verplicht')
        else:
            try:
                termijn = int(termijn_str)
                if termijn < 0 or termijn > 365:
                    errors.append('Termijn moet tussen 0 en 365 dagen zijn')
                else:
                    mapped_data['termijn'] = termijn
            except ValueError:
                errors.append(f'Ongeldige termijn: {termijn_str}')
        
    except Exception as e:
        errors.append(f'Verwerkingsfout: {str(e)}')
    
    status = 'error' if errors else 'valid'
    return ImportPreviewItem(
        row_number=row_number,
        mapped_data=mapped_data,
        validation_errors=errors,
        import_status=status
    )

def validate_crediteur_data(data: Dict[str, str], row_number: int) -> ImportPreviewItem:
    """Validate crediteur copy-paste data"""
    errors = []
    mapped_data = {}
    
    try:
        # Validate crediteur naam
        crediteur = data.get('crediteur', '').strip()
        if not crediteur:
            errors.append('Crediteur naam is verplicht')
        else:
            mapped_data['crediteur'] = crediteur
        
        # Validate bedrag
        bedrag_str = data.get('bedrag', '').strip()
        if not bedrag_str:
            errors.append('Bedrag is verplicht')
        else:
            try:
                # Clean up Euro format: "€ 12.500,00" or "€ 1.646,30"
                clean_amount = bedrag_str.replace('€', '').replace('EUR', '').strip()
                
                # Handle European number format (comma as decimal separator, dot as thousands separator)
                if ',' in clean_amount:
                    # Split by comma to handle decimal separator
                    parts = clean_amount.rsplit(',', 1)  # Split from right, max 1 split
                    if len(parts) == 2 and len(parts[1]) <= 2:  # Likely decimal separator
                        # Remove dots (thousands separators) from the main part
                        main_part = parts[0].replace('.', '')
                        clean_amount = main_part + '.' + parts[1]
                else:
                    # No comma, but might have dots as thousands separators
                    # Only treat as thousands separator if there are 3+ digits after the last dot
                    if '.' in clean_amount:
                        dot_parts = clean_amount.split('.')
                        if len(dot_parts) > 1 and len(dot_parts[-1]) == 3:
                            # Likely thousands separator format like "12.500"
                            clean_amount = clean_amount.replace('.', '')
                    
                bedrag = float(clean_amount)
                if bedrag <= 0:
                    errors.append('Bedrag moet groter zijn dan 0')
                else:
                    mapped_data['bedrag'] = bedrag
            except ValueError:
                errors.append(f'Ongeldig bedrag: {bedrag_str}')
        
        # Validate dag
        dag_str = data.get('dag', '').strip()
        if not dag_str:
            errors.append('Dag is verplicht')
        else:
            try:
                dag = int(dag_str)
                if dag < 1 or dag > 31:
                    errors.append('Dag moet tussen 1 en 31 zijn')
                else:
                    mapped_data['dag'] = dag
            except ValueError:
                errors.append(f'Ongeldige dag: {dag_str}')
        
    except Exception as e:
        errors.append(f'Verwerkingsfout: {str(e)}')
    
    status = 'error' if errors else 'valid'
    return ImportPreviewItem(
        row_number=row_number,
        mapped_data=mapped_data,
        validation_errors=errors,
        import_status=status
    )

# Import Utility Functions
def parse_csv_file(file_content: str, delimiter: str = ',') -> List[Dict[str, str]]:
    """Parse CSV content and return list of dictionaries"""
    try:
        # Remove BOM if present
        if file_content.startswith('\ufeff'):
            file_content = file_content[1:]
        elif file_content.startswith('\xef\xbb\xbf'):
            file_content = file_content[3:]
            
        # Try different delimiters if the default doesn't work
        delimiters = [';', delimiter, '\t', '|', ',']  # Put ; first for BUNQ
        
        for delim in delimiters:
            try:
                csv_reader = csv.DictReader(io.StringIO(file_content), delimiter=delim)
                rows = list(csv_reader)
                
                # Check if we got meaningful data (at least 2 columns with data)
                if rows and len(rows[0].keys()) >= 2:
                    # Filter out completely empty rows and None keys
                    filtered_rows = []
                    for row in rows:
                        if any(value and str(value).strip() for value in row.values()):
                            # Clean up the row - remove None keys, empty keys, and trim whitespace
                            clean_row = {}
                            for k, v in row.items():
                                if k is not None and str(k).strip() != '':
                                    clean_key = str(k).strip()  # Remove leading/trailing spaces
                                    clean_value = str(v).strip() if v else ''
                                    clean_row[clean_key] = clean_value
                            
                            if clean_row:
                                filtered_rows.append(clean_row)
                    
                    if filtered_rows:
                        return filtered_rows
                        
            except Exception:
                continue
                
        # If all delimiters failed, try one more time with the original
        csv_reader = csv.DictReader(io.StringIO(file_content), delimiter=delimiter)
        return [row for row in csv_reader if row]
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")

def validate_epd_declaratie_row(row: Dict[str, str], row_number: int) -> ImportPreviewItem:
    """Validate EPD declaratie row and return preview item"""
    errors = []
    mapped_data = {}
    
    # Map columns: factuur, datum, verzekeraar, bedrag
    try:
        mapped_data['invoice_number'] = row.get('factuur', '').strip()
        if not mapped_data['invoice_number']:
            errors.append('Factuur nummer is verplicht')
            
        # Parse date - support Dutch format like "8-1-2025"
        date_str = row.get('datum', '').strip()
        if date_str:
            try:
                # Try Dutch format first (d-m-yyyy)
                mapped_data['date'] = datetime.strptime(date_str, '%d-%m-%Y').date().isoformat()
            except ValueError:
                try:
                    # Try ISO format
                    mapped_data['date'] = datetime.strptime(date_str, '%Y-%m-%d').date().isoformat()
                except ValueError:
                    try:
                        # Try other common formats
                        mapped_data['date'] = datetime.strptime(date_str, '%d/%m/%Y').date().isoformat()
                    except ValueError:
                        errors.append(f'Ongeldige datum format: {date_str}')
        else:
            errors.append('Datum is verplicht')
            
        # Parse amount - handle Euro format like "€ 1.646,30"
        amount_str = row.get('bedrag', '').strip()
        if amount_str:
            try:
                # Clean up Euro format: "€ 1.646,30"
                clean_amount = amount_str.replace('€', '').replace('EUR', '').strip()
                
                # Handle European number format (comma as decimal separator, dot as thousands separator)
                if ',' in clean_amount:
                    # Split by comma to handle decimal separator
                    parts = clean_amount.rsplit(',', 1)  # Split from right, max 1 split
                    if len(parts) == 2 and len(parts[1]) <= 2:  # Likely decimal separator
                        # Remove dots (thousands separators) from the main part
                        main_part = parts[0].replace('.', '')
                        clean_amount = main_part + '.' + parts[1]
                    
                mapped_data['amount'] = float(clean_amount)
                if mapped_data['amount'] <= 0:
                    errors.append('Bedrag moet groter zijn dan 0')
            except (ValueError, InvalidOperation):
                errors.append(f'Ongeldig bedrag: {amount_str}')
        else:
            errors.append('Bedrag is verplicht')
            
        # Verzekeraar - extract clean name from format like "202200008321-Centrale Verwerkingseenheid CZ: CZ, Nationale-Nederlanden en OHRA"
        verzekeraar_raw = row.get('verzekeraar', '').strip()
        if verzekeraar_raw:
            # Try to extract the clean verzekeraar name after the dash
            if '-' in verzekeraar_raw:
                verzekeraar_clean = verzekeraar_raw.split('-', 1)[1].strip()
            else:
                verzekeraar_clean = verzekeraar_raw
            mapped_data['patient_name'] = verzekeraar_clean
        else:
            mapped_data['patient_name'] = ''
            
        mapped_data['description'] = f"Declaratie {mapped_data.get('invoice_number', '')} - {mapped_data.get('patient_name', '')}"
        mapped_data['type'] = 'income'
        mapped_data['category'] = 'zorgverzekeraar'
        
    except Exception as e:
        errors.append(f'Verwerkingsfout: {str(e)}')
    
    status = 'error' if errors else 'valid'
    return ImportPreviewItem(
        row_number=row_number,
        mapped_data=mapped_data,
        validation_errors=errors,
        import_status=status
    )

def validate_epd_particulier_row(row: Dict[str, str], row_number: int) -> ImportPreviewItem:
    """Validate EPD particulier row and return preview item"""
    errors = []
    mapped_data = {}
    
    # Map columns: factuur, datum, debiteur, bedrag
    try:
        mapped_data['invoice_number'] = row.get('factuur', '').strip()
        if not mapped_data['invoice_number']:
            errors.append('Factuur nummer is verplicht')
            
        # Parse date - support Dutch format like "8-1-2025"
        date_str = row.get('datum', '').strip()
        if date_str:
            try:
                # Try Dutch format first (d-m-yyyy)
                mapped_data['date'] = datetime.strptime(date_str, '%d-%m-%Y').date().isoformat()
            except ValueError:
                try:
                    # Try ISO format
                    mapped_data['date'] = datetime.strptime(date_str, '%Y-%m-%d').date().isoformat()
                except ValueError:
                    try:
                        # Try other common formats
                        mapped_data['date'] = datetime.strptime(date_str, '%d/%m/%Y').date().isoformat()
                    except ValueError:
                        errors.append(f'Ongeldige datum format: {date_str}')
        else:
            errors.append('Datum is verplicht')
            
        # Parse amount - handle Euro format like "€ 1.646,30"
        amount_str = row.get('bedrag', '').strip()
        if amount_str:
            try:
                # Clean up Euro format: "€ 1.646,30"
                clean_amount = amount_str.replace('€', '').replace('EUR', '').strip()
                
                # Handle European number format (comma as decimal separator, dot as thousands separator)
                if ',' in clean_amount:
                    # Split by comma to handle decimal separator
                    parts = clean_amount.rsplit(',', 1)  # Split from right, max 1 split
                    if len(parts) == 2 and len(parts[1]) <= 2:  # Likely decimal separator
                        # Remove dots (thousands separators) from the main part
                        main_part = parts[0].replace('.', '')
                        clean_amount = main_part + '.' + parts[1]
                    
                mapped_data['amount'] = float(clean_amount)
                if mapped_data['amount'] <= 0:
                    errors.append('Bedrag moet groter zijn dan 0')
            except (ValueError, InvalidOperation):
                errors.append(f'Ongeldig bedrag: {amount_str}')
        else:
            errors.append('Bedrag is verplicht')
            
        # Debiteur
        mapped_data['patient_name'] = row.get('debiteur', '').strip()
        mapped_data['description'] = f"Particuliere factuur {mapped_data.get('invoice_number', '')} - {mapped_data.get('patient_name', '')}"
        mapped_data['type'] = 'income'
        mapped_data['category'] = 'particulier'
        
    except Exception as e:
        errors.append(f'Verwerkingsfout: {str(e)}')
    
    status = 'error' if errors else 'valid'
    return ImportPreviewItem(
        row_number=row_number,
        mapped_data=mapped_data,
        validation_errors=errors,
        import_status=status
    )

def validate_bunq_row(row: Dict[str, str], row_number: int) -> ImportPreviewItem:
    """Validate BUNQ bank row and return preview item"""
    errors = []
    mapped_data = {}
    
    # Extended column name mapping for different BUNQ export formats
    try:
        # First, let's debug what columns we actually have
        available_columns = list(row.keys())
        
        # Parse date - try extensive list of possible column names (including exact BUNQ format)
        date_str = ''
        date_columns = [
            'datum',  # Exact BUNQ column name first
            'Date', 'Datum', 'date', 'DATE',
            'Transactiedatum', 'transactiedatum', 'Transaction Date', 'transaction_date',
            'Boekingsdatum', 'boekingsdatum', 'Booking Date', 'booking_date',
            'Created', 'created', 'Tijd', 'tijd', 'Time', 'time'
        ]
        
        found_date_col = None
        for date_col in date_columns:
            if date_col in row and row[date_col] and str(row[date_col]).strip():
                date_str = str(row[date_col]).strip()
                found_date_col = date_col
                break
                
        if date_str:
            try:
                # Try various date formats (including BUNQ format)
                date_formats = [
                    '%d-%m-%Y',  # BUNQ format: 1-1-2025
                    '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y',
                    '%Y/%m/%d', '%d.%m.%Y', '%Y.%m.%d',
                    '%Y-%m-%d %H:%M:%S', '%d-%m-%Y %H:%M:%S'
                ]
                
                parsed_date = None
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt).date()
                        break
                    except ValueError:
                        continue
                        
                if parsed_date:
                    mapped_data['date'] = parsed_date.isoformat()
                else:
                    errors.append(f'Ongeldige datum format: {date_str}')
                    
            except Exception as e:
                errors.append(f'Datum parsing fout: {str(e)}')
        else:
            errors.append(f'Datum kolom niet gevonden. Beschikbare kolommen: {", ".join(available_columns)}')
            
        # Parse amount - try extensive list of possible column names (including exact BUNQ format)
        amount_str = ''
        amount_columns = [
            'bedrag',  # Exact BUNQ column name first
            ' bedrag',  # With leading space (as seen in the error)
            'Amount', 'Bedrag', 'amount', 'AMOUNT',
            'Transactiebedrag', 'transactiebedrag', 'Transaction Amount', 'transaction_amount',
            'Saldo mutatie', 'saldo_mutatie', 'Balance Change', 'balance_change',
            'Waarde', 'waarde', 'Value', 'value', 'EUR', 'eur',
            'Debet', 'debet', 'Credit', 'credit'
        ]
        
        found_amount_col = None
        for amount_col in amount_columns:
            if amount_col in row and row[amount_col] and str(row[amount_col]).strip():
                amount_str = str(row[amount_col]).strip()
                # Clean up BUNQ format: "€ -89,75" or "€ 124,76"
                clean_amount = amount_str.replace('€', '').replace('EUR', '').strip()
                
                # Handle European number format (comma as decimal separator)
                # Only replace the last comma with dot (decimal separator)
                if ',' in clean_amount:
                    parts = clean_amount.rsplit(',', 1)  # Split from right, max 1 split
                    if len(parts) == 2 and len(parts[1]) <= 2:  # Likely decimal separator
                        clean_amount = parts[0].replace(',', '') + '.' + parts[1]
                    
                amount_str = clean_amount
                found_amount_col = amount_col
                break
                
        if amount_str:
            try:
                original_amount = float(amount_str)
                mapped_data['amount'] = abs(original_amount)  # Use absolute value
                mapped_data['original_amount'] = original_amount  # Keep original for reconciliation
            except (ValueError, InvalidOperation):
                errors.append(f'Ongeldig bedrag: {amount_str}')
        else:
            errors.append(f'Bedrag kolom niet gevonden. Beschikbare kolommen: {", ".join(available_columns)}')
            
        # Other fields - try extensive column names (including exact BUNQ format)
        mapped_data['counterparty'] = ''
        counterparty_columns = [
            'debiteur',  # Exact BUNQ column name first
            'Counterparty', 'tegenpartij', 'Tegenpartij', 'counterparty',
            'Naam tegenpartij', 'naam_tegenpartij', 'Counterparty Name', 'counterparty_name',
            'Begunstigde', 'begunstigde', 'Beneficiary', 'beneficiary',
            'Van/naar', 'van_naar', 'From/To', 'from_to'
        ]
        for counter_col in counterparty_columns:
            if counter_col in row and row[counter_col] and str(row[counter_col]).strip():
                mapped_data['counterparty'] = str(row[counter_col]).strip()
                break
                
        mapped_data['description'] = ''
        description_columns = [
            'omschrijving',  # Exact BUNQ column name first
            'Description', 'Omschrijving', 'description',
            'Transactieomschrijving', 'transactieomschrijving', 'Transaction Description', 'transaction_description',
            'Memo', 'memo', 'Note', 'note', 'Notes', 'notes',
            'Mededelingen', 'mededelingen', 'Message', 'message'
        ]
        for desc_col in description_columns:
            if desc_col in row and row[desc_col] and str(row[desc_col]).strip():
                mapped_data['description'] = str(row[desc_col]).strip()
                break
                
        mapped_data['account_number'] = ''
        account_columns = [
            'Account', 'rekening', 'Rekening', 'account',
            'IBAN', 'iban', 'Rekeningnummer', 'rekeningnummer',
            'Account Number', 'account_number', 'From Account', 'from_account'
        ]
        for acc_col in account_columns:
            if acc_col in row and row[acc_col] and str(row[acc_col]).strip():
                mapped_data['account_number'] = str(row[acc_col]).strip()
                break
        
        # Add debug info to help user understand what columns were found
        if found_date_col:
            mapped_data['_debug_date_column'] = found_date_col
        if found_amount_col:
            mapped_data['_debug_amount_column'] = found_amount_col
        
    except Exception as e:
        errors.append(f'Verwerkingsfout: {str(e)}')
    
    status = 'error' if errors else 'valid'
    return ImportPreviewItem(
        row_number=row_number,
        mapped_data=mapped_data,
        validation_errors=errors,
        import_status=status
    )

# Import Endpoints
@api_router.post("/import/inspect-columns")
async def inspect_csv_columns(file: UploadFile = File(...)):
    """Inspect CSV file columns for debugging"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Alleen CSV bestanden zijn toegestaan")
    
    try:
        # Read and parse file with proper encoding detection
        content = await file.read()
        
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'iso-8859-1', 'cp1252']
        content_str = None
        
        for encoding in encodings:
            try:
                content_str = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
                
        if content_str is None:
            raise HTTPException(status_code=400, detail="Kan bestand encoding niet detecteren")
        
        # Parse CSV and get first few rows
        rows = parse_csv_file(content_str)
        
        if not rows:
            return {"columns": [], "sample_rows": [], "row_count": 0}
            
        # Get column info
        columns = list(rows[0].keys())
        sample_rows = rows[:3]  # First 3 rows as sample
        
        return {
            "columns": columns,
            "sample_rows": sample_rows,
            "row_count": len(rows),
            "filename": file.filename
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fout bij inspecteren bestand: {str(e)}")

@api_router.post("/import/preview")
async def preview_import(
    file: UploadFile = File(...),
    import_type: str = Form(...)
):
    """Preview import data before processing"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Alleen CSV bestanden zijn toegestaan")
    
    try:
        # Read file content with proper encoding detection
        content = await file.read()
        
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'iso-8859-1', 'cp1252']
        content_str = None
        
        for encoding in encodings:
            try:
                content_str = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
                
        if content_str is None:
            raise HTTPException(status_code=400, detail="Kan bestand encoding niet detecteren")
        
        # Parse CSV
        rows = parse_csv_file(content_str)
        
        if not rows:
            raise HTTPException(status_code=400, detail="CSV bestand is leeg")
        
        # Validate ALL rows first to get accurate statistics, then create preview
        all_validation_results = []
        total_valid_count = 0
        total_error_count = 0
        
        # Process all rows for accurate statistics
        for i, row in enumerate(rows, 1):
            if import_type == 'epd_declaraties':
                item = validate_epd_declaratie_row(row, i)
            elif import_type == 'epd_particulier':
                item = validate_epd_particulier_row(row, i)
            elif import_type == 'bank_bunq':
                item = validate_bunq_row(row, i)
            else:
                raise HTTPException(status_code=400, detail=f"Onbekend import type: {import_type}")
            
            all_validation_results.append(item)
            if item.import_status == 'valid':
                total_valid_count += 1
            else:
                total_error_count += 1
        
        # Take first 20 items for preview display
        preview_items = all_validation_results[:20]
        
        # Column mapping
        column_mapping = {}
        if rows:
            if import_type == 'epd_declaraties':
                column_mapping = {'factuur': 'Factuur Nummer', 'datum': 'Datum', 'verzekeraar': 'Verzekeraar', 'bedrag': 'Bedrag'}
            elif import_type == 'epd_particulier':
                column_mapping = {'factuur': 'Factuur Nummer', 'datum': 'Datum', 'debiteur': 'Debiteur', 'bedrag': 'Bedrag'}
            elif import_type == 'bank_bunq':
                # Filter out None keys and values for BUNQ import
                column_mapping = {
                    key: key for key in rows[0].keys() 
                    if key is not None and key.strip() != ''
                }
        
        # Collect all errors for reporting
        all_errors = []
        for item in all_validation_results:
            if item.import_status == 'error':
                for error in item.validation_errors:
                    all_errors.append(f"Rij {item.row_number}: {error}")

        return ImportPreview(
            file_name=file.filename,
            import_type=import_type,
            total_rows=len(rows),
            valid_rows=total_valid_count,
            error_rows=total_error_count,
            preview_items=preview_items,  # Already limited to first 20
            column_mapping=column_mapping,
            all_errors=all_errors[:50]  # Limit to first 50 errors for display
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fout bij verwerken bestand: {str(e)}")

@api_router.post("/import/execute", response_model=ImportResult)
async def execute_import(
    file: UploadFile = File(...),
    import_type: str = Form(...)
):
    """Execute the import after preview confirmation"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Alleen CSV bestanden zijn toegestaan")
    
    try:
        # Read and parse file with proper encoding detection
        content = await file.read()
        
        # Try different encodings
        encodings = ['utf-8', 'utf-8-sig', 'iso-8859-1', 'cp1252']
        content_str = None
        
        for encoding in encodings:
            try:
                content_str = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
                
        if content_str is None:
            raise HTTPException(status_code=400, detail="Kan bestand encoding niet detecteren")
        rows = parse_csv_file(content_str)
        
        imported_count = 0
        error_count = 0
        errors = []
        created_transactions = []
        
        for i, row in enumerate(rows, 1):
            try:
                # Validate and map data
                if import_type == 'epd_declaraties':
                    item = validate_epd_declaratie_row(row, i)
                elif import_type == 'epd_particulier':
                    item = validate_epd_particulier_row(row, i)
                elif import_type == 'bank_bunq':
                    # For bank data, store as bank transactions for reconciliation
                    item = validate_bunq_row(row, i)
                    if item.import_status == 'valid':
                        bank_trans = BankTransaction(**item.mapped_data)
                        bank_dict = prepare_for_mongo(bank_trans.dict())
                        await db.bank_transactions.insert_one(bank_dict)
                        imported_count += 1
                        created_transactions.append(bank_trans.id)
                    continue
                else:
                    raise HTTPException(status_code=400, detail=f"Onbekend import type: {import_type}")
                
                if item.import_status == 'valid':
                    # Create transaction
                    transaction_obj = Transaction(**item.mapped_data)
                    mongo_dict = prepare_for_mongo(transaction_obj.dict())
                    await db.transactions.insert_one(mongo_dict)
                    imported_count += 1
                    created_transactions.append(transaction_obj.id)
                else:
                    error_count += 1
                    errors.append(f"Rij {i}: {', '.join(item.validation_errors)}")
                    
            except Exception as e:
                error_count += 1
                errors.append(f"Rij {i}: {str(e)}")
        
        return ImportResult(
            success=True,
            imported_count=imported_count,
            error_count=error_count,
            errors=errors[:10],  # Limit to first 10 errors
            created_transactions=created_transactions
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import fout: {str(e)}")

# Bank Reconciliation Endpoints
@api_router.get("/bank-reconciliation/unmatched")
async def get_unmatched_bank_transactions():
    """Get unmatched bank transactions for reconciliation"""
    try:
        bank_transactions = await db.bank_transactions.find({"reconciled": False}).to_list(1000)
        return [BankTransaction(**parse_from_mongo(bt)) for bt in bank_transactions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bank transactions: {str(e)}")

@api_router.post("/bank-reconciliation/match")
async def match_bank_transaction(bank_transaction_id: str, cashflow_transaction_id: str):
    """Match a bank transaction with a cashflow transaction"""
    try:
        # Update bank transaction
        await db.bank_transactions.update_one(
            {"id": bank_transaction_id},
            {"$set": {"reconciled": True}}
        )
        
        # Update cashflow transaction
        await db.transactions.update_one(
            {"id": cashflow_transaction_id},
            {"$set": {"reconciled": True}}
        )
        
        # Create reconciliation record
        reconciliation = BankReconciliation(
            bank_transaction_id=bank_transaction_id,
            bank_date=date.today(),
            bank_amount=0.0,  # Will be filled from actual bank transaction
            bank_description="",
            matched_transaction_id=cashflow_transaction_id,
            reconciliation_status="matched",
            match_confidence=1.0
        )
        
        reconciliation_dict = prepare_for_mongo(reconciliation.dict())
        await db.reconciliations.insert_one(reconciliation_dict)
        
        return {"message": "Transacties succesvol gekoppeld"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error matching transactions: {str(e)}")

@api_router.get("/bank-reconciliation/suggestions/{bank_transaction_id}")
async def get_reconciliation_suggestions(bank_transaction_id: str):
    """Get suggested matches for a bank transaction"""
    try:
        # Get bank transaction
        bank_trans = await db.bank_transactions.find_one({"id": bank_transaction_id})
        if not bank_trans:
            raise HTTPException(status_code=404, detail="Bank transactie niet gevonden")
        
        bank_amount = bank_trans.get('amount', 0)
        bank_date = bank_trans.get('date', '')
        
        # Find potential matches based on amount and date proximity
        date_obj = datetime.fromisoformat(bank_date).date() if bank_date else date.today()
        start_date = (date_obj - timedelta(days=7)).isoformat()
        end_date = (date_obj + timedelta(days=7)).isoformat()
        
        potential_matches = await db.transactions.find({
            "reconciled": False,
            "amount": bank_amount,
            "date": {"$gte": start_date, "$lte": end_date}
        }).to_list(10)
        
        return [Transaction(**parse_from_mongo(trans)) for trans in potential_matches]
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding suggestions: {str(e)}")

# Copy-Paste Import Endpoints
@api_router.post("/copy-paste-import/preview", response_model=CopyPasteImportResult)
async def preview_copy_paste_import(request: CopyPasteImportRequest):
    """Preview copy-paste import data"""
    try:
        if request.import_type == 'verzekeraars':
            expected_columns = ['naam', 'termijn']
            parsed_data = parse_copy_paste_data(request.data, expected_columns)
            
            preview_items = []
            valid_count = 0
            error_count = 0
            
            for i, row in enumerate(parsed_data, 1):
                item = validate_verzekeraar_data(row, i)
                preview_items.append(item.dict())
                if item.import_status == 'valid':
                    valid_count += 1
                else:
                    error_count += 1
        
        elif request.import_type == 'crediteuren':
            expected_columns = ['crediteur', 'bedrag', 'dag']
            parsed_data = parse_copy_paste_data(request.data, expected_columns)
            
            preview_items = []
            valid_count = 0
            error_count = 0
            
            for i, row in enumerate(parsed_data, 1):
                item = validate_crediteur_data(row, i)
                preview_items.append(item.dict())
                if item.import_status == 'valid':
                    valid_count += 1
                else:
                    error_count += 1
        
        else:
            raise HTTPException(status_code=400, detail=f"Onbekend import type: {request.import_type}")
        
        return CopyPasteImportResult(
            success=True,
            imported_count=valid_count,
            error_count=error_count,
            errors=[],
            preview_data=preview_items
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview fout: {str(e)}")

@api_router.post("/copy-paste-import/execute", response_model=ImportResult)
async def execute_copy_paste_import(request: CopyPasteImportRequest):
    """Execute copy-paste import"""
    try:
        imported_count = 0
        error_count = 0
        errors = []
        created_ids = []
        
        if request.import_type == 'verzekeraars':
            expected_columns = ['naam', 'termijn']
            parsed_data = parse_copy_paste_data(request.data, expected_columns)
            
            for i, row in enumerate(parsed_data, 1):
                try:
                    item = validate_verzekeraar_data(row, i)
                    if item.import_status == 'valid':
                        verzekeraar = Verzekeraar(**item.mapped_data)
                        verzekeraar_dict = prepare_for_mongo(verzekeraar.dict())
                        await db.verzekeraars.insert_one(verzekeraar_dict)
                        imported_count += 1
                        created_ids.append(verzekeraar.id)
                    else:
                        error_count += 1
                        errors.extend([f"Rij {i}: {err}" for err in item.validation_errors])
                except Exception as e:
                    error_count += 1
                    errors.append(f"Rij {i}: {str(e)}")
        
        elif request.import_type == 'crediteuren':
            expected_columns = ['crediteur', 'bedrag', 'dag']
            parsed_data = parse_copy_paste_data(request.data, expected_columns)
            
            for i, row in enumerate(parsed_data, 1):
                try:
                    item = validate_crediteur_data(row, i)
                    if item.import_status == 'valid':
                        crediteur = Crediteur(**item.mapped_data)
                        crediteur_dict = prepare_for_mongo(crediteur.dict())
                        await db.crediteuren.insert_one(crediteur_dict)
                        imported_count += 1
                        created_ids.append(crediteur.id)
                    else:
                        error_count += 1
                        errors.extend([f"Rij {i}: {err}" for err in item.validation_errors])
                except Exception as e:
                    error_count += 1
                    errors.append(f"Rij {i}: {str(e)}")
        
        return ImportResult(
            success=True,
            imported_count=imported_count,
            error_count=error_count,
            errors=errors[:10],  # Limit errors
            created_transactions=created_ids
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import fout: {str(e)}")

# Verzekeraars endpoints
@api_router.get("/verzekeraars", response_model=List[Verzekeraar])
async def get_verzekeraars():
    """Get all verzekeraars"""
    try:
        verzekeraars = await db.verzekeraars.find({"actief": True}).to_list(1000)
        return [Verzekeraar(**parse_from_mongo(v)) for v in verzekeraars]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching verzekeraars: {str(e)}")

@api_router.post("/verzekeraars", response_model=Verzekeraar)
async def create_verzekeraar(verzekeraar: VerzekeraarCreate):
    """Create a new verzekeraar"""
    try:
        verzekeraar_obj = Verzekeraar(**verzekeraar.dict())
        mongo_dict = prepare_for_mongo(verzekeraar_obj.dict())
        await db.verzekeraars.insert_one(mongo_dict)
        return verzekeraar_obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating verzekeraar: {str(e)}")

# Crediteuren endpoints  
@api_router.get("/crediteuren", response_model=List[Crediteur])
async def get_crediteuren():
    """Get all crediteuren"""
    try:
        crediteuren = await db.crediteuren.find({"actief": True}).to_list(1000)
        return [Crediteur(**parse_from_mongo(c)) for c in crediteuren]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching crediteuren: {str(e)}")

@api_router.post("/crediteuren", response_model=Crediteur)  
async def create_crediteur(crediteur: CrediteurCreate):
    """Create a new crediteur"""
    try:
        crediteur_obj = Crediteur(**crediteur.dict())
        mongo_dict = prepare_for_mongo(crediteur_obj.dict())
        await db.crediteuren.insert_one(mongo_dict)
        return crediteur_obj
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating crediteur: {str(e)}")

# Verwachte betalingen endpoint
@api_router.get("/verwachte-betalingen")
async def get_verwachte_betalingen():
    """Calculate expected payments based on transactions and crediteuren"""
    try:
        verwachte_betalingen = []
        
        # Get declaratie transactions that are not reconciled
        transactions = await db.transactions.find({
            "type": "income",
            "category": "zorgverzekeraar",
            "reconciled": False
        }).to_list(1000)
        
        # Get verzekeraars for payment terms
        verzekeraars = await db.verzekeraars.find({"actief": True}).to_list(1000)
        verzekeraars_dict = {v['naam']: v['termijn'] for v in verzekeraars}
        
        # Calculate expected payments for declaraties
        for trans in transactions:
            transaction_date = datetime.fromisoformat(trans['date'])
            patient_name = trans.get('patient_name', '')
            
            # Try to match verzekeraar name
            termijn = 30  # Default termijn
            for verzekeraar_naam, verzekeraar_termijn in verzekeraars_dict.items():
                if verzekeraar_naam.lower() in patient_name.lower():
                    termijn = verzekeraar_termijn
                    break
            
            verwachte_datum = transaction_date.date() + timedelta(days=termijn)
            
            verwachte_betaling = {
                'id': str(uuid.uuid4()),
                'transaction_id': trans['id'],
                'type': 'declaratie',
                'beschrijving': f"Declaratie {trans.get('invoice_number', '')} - {patient_name}",
                'bedrag': trans['amount'],
                'verwachte_datum': verwachte_datum.isoformat(),
                'status': 'open' if verwachte_datum >= date.today() else 'overdue'
            }
            verwachte_betalingen.append(verwachte_betaling)
        
        # Add crediteur payments for current month
        crediteuren = await db.crediteuren.find({"actief": True}).to_list(1000)
        current_month = date.today().replace(day=1)
        
        for crediteur in crediteuren:
            try:
                betalings_datum = current_month.replace(day=crediteur['dag'])
                if betalings_datum < date.today():
                    # Next month if day has passed
                    next_month = current_month + timedelta(days=32)
                    betalings_datum = next_month.replace(day=crediteur['dag'])
                
                verwachte_betaling = {
                    'id': str(uuid.uuid4()),
                    'crediteur_id': crediteur['id'],
                    'type': 'crediteur',
                    'beschrijving': f"Betaling {crediteur['crediteur']}",
                    'bedrag': -crediteur['bedrag'],  # Negative for expense
                    'verwachte_datum': betalings_datum.isoformat(),
                    'status': 'open'
                }
                verwachte_betalingen.append(verwachte_betaling)
            except ValueError:
                # Skip invalid days (like 31st in February)
                continue
        
        # Sort by date
        verwachte_betalingen.sort(key=lambda x: x['verwachte_datum'])
        
        return verwachte_betalingen[:50]  # Limit to 50 items
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating expected payments: {str(e)}")

# Legacy routes (keep for compatibility)
@api_router.get("/")
async def root():
    return {"message": "Fysiotherapie Cashflow API - Ready"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()