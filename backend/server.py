from fastapi import FastAPI, APIRouter, HTTPException, UploadFile, File, Form, Query
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
    CREDITEUR = "crediteur" 
    VARIABEL = "variabel"
    OVERIG = "overig"

class CorrectionType(str, Enum):
    CREDITFACTUUR_PARTICULIER = "creditfactuur_particulier"
    CREDITDECLARATIE_VERZEKERAAR = "creditdeclaratie_verzekeraar"
    CORRECTIEFACTUUR_VERZEKERAAR = "correctiefactuur_verzekeraar"

# Helper functions
def prepare_for_mongo(data):
    """Convert date/datetime objects to ISO strings for MongoDB storage"""
    if isinstance(data.get('date'), date):
        data['date'] = data['date'].isoformat()
    if isinstance(data.get('bank_date'), date):
        data['bank_date'] = data['bank_date'].isoformat()
    if isinstance(data.get('verwachte_datum'), date):
        data['verwachte_datum'] = data['verwachte_datum'].isoformat()
    if isinstance(data.get('created_at'), datetime):
        data['created_at'] = data['created_at'].isoformat()
    return data

def parse_from_mongo(item):
    """Parse date/datetime strings from MongoDB back to Python objects"""
    if isinstance(item.get('date'), str):
        item['date'] = datetime.fromisoformat(item['date']).date()
    if isinstance(item.get('bank_date'), str):
        item['bank_date'] = datetime.fromisoformat(item['bank_date']).date()
    if isinstance(item.get('verwachte_datum'), str):
        item['verwachte_datum'] = datetime.fromisoformat(item['verwachte_datum']).date()
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

# Nieuwe models voor uitgebreide cashflow management
class BankSaldo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    date: date
    saldo: float
    description: str = "Banksaldo"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OverigeOmzet(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    amount: float
    date: date
    category: str = "overige_omzet"
    recurring: bool = False  # Is dit een terugkerende omzet?
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Correction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    correction_type: CorrectionType
    original_transaction_id: Optional[str] = None  # Link naar originele transactie
    original_invoice_number: Optional[str] = None  # Om te matchen als ID niet bekend is
    amount: float  # Correctiebedrag
    description: str
    date: date
    patient_name: Optional[str] = None
    matched: bool = False  # Is gekoppeld aan originele transactie
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CorrectionCreate(BaseModel):
    correction_type: CorrectionType
    original_invoice_number: Optional[str] = None
    amount: float
    description: str
    date: date
    patient_name: Optional[str] = None

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
def extract_clean_name(raw_name: str) -> str:
    """Extract clean name by removing everything before and including the dash"""
    if not raw_name:
        return ''
    
    raw_name = raw_name.strip()
    
    # If there's a dash, take everything after it
    if '-' in raw_name:
        return raw_name.split('-', 1)[1].strip()
    
    # If no dash, return the original (already clean)
    return raw_name

def parse_dutch_currency(value: str) -> float:
    """Parse Dutch currency format (€ -1.008,50 or -48,50) to float"""
    if not value:
        return 0.0
    
    # Remove currency symbols and spaces
    cleaned = value.replace('€', '').replace(' ', '').strip()
    
    # Handle Dutch number format with dots as thousands and comma as decimal
    if '.' in cleaned and ',' in cleaned:
        # Format like 1.008,50 - dot is thousands separator, comma is decimal
        # Remove dots (thousands separators) and replace comma with dot
        cleaned = cleaned.replace('.', '').replace(',', '.')
    elif ',' in cleaned:
        # Only comma present - check if it's decimal separator
        comma_pos = cleaned.rfind(',')
        if len(cleaned) - comma_pos <= 3:  # Last comma is decimal separator
            cleaned = cleaned.replace(',', '.')
        else:
            # Multiple commas or weird format, remove all commas
            cleaned = cleaned.replace(',', '')
    elif '.' in cleaned:
        # Only dots present - could be thousands separator or decimal
        dot_pos = cleaned.rfind('.')
        if len(cleaned) - dot_pos <= 3:  # Last dot might be decimal
            # If it's like "1.008" it's probably thousands, if it's "48.50" it's decimal
            # Check if there are multiple dots or if the number before last dot is > 999
            parts = cleaned.split('.')
            if len(parts) > 2 or (len(parts) == 2 and len(parts[0]) > 3):
                # Multiple dots or large number before dot = thousands separator
                cleaned = ''.join(parts[:-1]) + '.' + parts[-1]
            # Otherwise leave as is (could be decimal)
    
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

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
            
        # Parse amount using improved Dutch currency parser
        amount_str = row.get('bedrag', '').strip()
        if amount_str:
            try:
                parsed_amount = parse_dutch_currency(amount_str)
                if parsed_amount <= 0:
                    errors.append('Bedrag moet groter zijn dan 0')
                else:
                    mapped_data['amount'] = parsed_amount
            except Exception:
                errors.append(f'Ongeldig bedrag: {amount_str}')
        else:
            errors.append('Bedrag is verplicht')
            
        # Verzekeraar - extract clean name (remove factuurnummer prefix)
        verzekeraar_raw = row.get('verzekeraar', '').strip()
        verzekeraar_clean = extract_clean_name(verzekeraar_raw)
        mapped_data['patient_name'] = verzekeraar_clean
            
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
            
        # Parse amount using improved Dutch currency parser
        amount_str = row.get('bedrag', '').strip()
        if amount_str:
            try:
                parsed_amount = parse_dutch_currency(amount_str)
                if parsed_amount <= 0:
                    errors.append('Bedrag moet groter zijn dan 0')
                else:
                    mapped_data['amount'] = parsed_amount
            except Exception:
                errors.append(f'Ongeldig bedrag: {amount_str}')
        else:
            errors.append('Bedrag is verplicht')
            
        # Extract clean patient name (remove factuurnummer prefix)
        debiteur = row.get('debiteur', '').strip()
        patient_name = extract_clean_name(debiteur)
        
        mapped_data['patient_name'] = patient_name
        mapped_data['description'] = f"Particuliere factuur {mapped_data.get('invoice_number', '')} - {patient_name}"
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
                found_amount_col = amount_col
                break
                
        if amount_str:
            try:
                # Use improved Dutch currency parser to handle BUNQ format
                parsed_amount = parse_dutch_currency(amount_str)
                mapped_data['amount'] = parsed_amount  # Keep original sign (positive for income, negative for expenses)
                mapped_data['original_amount'] = parsed_amount  # Keep original for reconciliation
            except Exception:
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
@api_router.post("/import/debug-preview")
async def debug_import_preview(
    file: UploadFile = File(...),
    import_type: str = Form(...)
):
    """Debug preview with detailed error reporting and sample rows"""
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
        
        # Parse CSV and get sample data
        rows = parse_csv_file(content_str)
        
        if not rows:
            return {"error": "Geen geldige rijen gevonden", "sample_rows": [], "total_rows": 0}
        
        # Process first 10 rows for detailed debugging
        debug_results = []
        for i, row in enumerate(rows[:10], 1):
            if import_type == 'bank_bunq':
                item = validate_bunq_row(row, i)
            elif import_type == 'epd_declaraties':
                item = validate_epd_declaratie_row(row, i)
            elif import_type == 'epd_particulier':
                item = validate_epd_particulier_row(row, i)
            else:
                raise HTTPException(status_code=400, detail=f"Onbekend import type: {import_type}")
            
            debug_results.append({
                'row_number': i,
                'original_row': row,
                'mapped_data': item.mapped_data,
                'validation_errors': item.validation_errors,
                'status': item.import_status
            })
        
        # Get column info
        columns = list(rows[0].keys()) if rows else []
        
        return {
            'file_name': file.filename,
            'total_rows': len(rows),
            'columns_found': columns,
            'debug_results': debug_results,
            'sample_raw_rows': rows[:5]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug fout: {str(e)}")

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
        bank_transactions = await db.bank_transactions.find({"reconciled": False}).sort([("date", -1)]).to_list(1000)
        return [BankTransaction(**parse_from_mongo(bt)) for bt in bank_transactions]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bank transactions: {str(e)}")

@api_router.post("/bank-reconciliation/match")
async def match_bank_transaction(
    bank_transaction_id: str = Query(...),
    cashflow_transaction_id: str = Query(...)
):
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
        
        # Get bank transaction details for reconciliation record
        bank_trans = await db.bank_transactions.find_one({"id": bank_transaction_id})
        bank_amount = bank_trans.get('amount', 0.0) if bank_trans else 0.0
        bank_description = bank_trans.get('description', '') if bank_trans else ''
        bank_date_str = bank_trans.get('date', '') if bank_trans else date.today().isoformat()
        
        # Create reconciliation record
        reconciliation = BankReconciliation(
            bank_transaction_id=bank_transaction_id,
            bank_date=bank_date_str if isinstance(bank_date_str, str) else date.today(),
            bank_amount=bank_amount,
            bank_description=bank_description,
            matched_transaction_id=cashflow_transaction_id,
            reconciliation_status="matched",
            match_confidence=1.0
        )
        
        reconciliation_dict = prepare_for_mongo(reconciliation.dict())
        await db.reconciliations.insert_one(reconciliation_dict)
        
        return {"message": "Transacties succesvol gekoppeld"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error matching transactions: {str(e)}")

@api_router.post("/bank-reconciliation/match-crediteur")
async def match_bank_transaction_with_crediteur(
    bank_transaction_id: str = Query(...),
    crediteur_id: str = Query(...)
):
    """Match a bank transaction with a crediteur"""
    try:
        # Get bank transaction and crediteur details
        bank_trans = await db.bank_transactions.find_one({"id": bank_transaction_id})
        crediteur = await db.crediteuren.find_one({"id": crediteur_id})
        
        if not bank_trans or not crediteur:
            raise HTTPException(status_code=404, detail="Bank transactie of crediteur niet gevonden")
        
        # Create expense transaction for the crediteur payment
        expense_transaction = Transaction(
            type="expense",
            category="crediteur",
            amount=crediteur['bedrag'],
            description=f"Maandelijkse betaling {crediteur['crediteur']}",
            date=bank_trans['date'] if isinstance(bank_trans['date'], str) else bank_trans['date'].isoformat(),
            patient_name=crediteur['crediteur'],
            invoice_number=f"CRED-{crediteur_id[:8]}",
            notes=f"Automatisch gekoppeld aan bank transactie {bank_transaction_id[:8]}",
            reconciled=True
        )
        
        # Save expense transaction
        expense_dict = prepare_for_mongo(expense_transaction.dict())
        await db.transactions.insert_one(expense_dict)
        
        # Mark bank transaction as reconciled
        await db.bank_transactions.update_one(
            {"id": bank_transaction_id},
            {"$set": {"reconciled": True}}
        )
        
        # Create reconciliation record
        bank_date_str = bank_trans.get('date', '')
        reconciliation = BankReconciliation(
            bank_transaction_id=bank_transaction_id,
            bank_date=bank_date_str if isinstance(bank_date_str, str) else date.today(),
            bank_amount=bank_trans.get('amount', 0),
            bank_description=bank_trans.get('description', ''),
            matched_transaction_id=expense_transaction.id,
            reconciliation_status="matched_crediteur",
            match_confidence=0.9
        )
        
        reconciliation_dict = prepare_for_mongo(reconciliation.dict())
        await db.reconciliations.insert_one(reconciliation_dict)
        
        return {
            "message": "Bank transactie succesvol gekoppeld aan crediteur",
            "created_expense_id": expense_transaction.id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error matching with crediteur: {str(e)}")

@api_router.get("/bank-reconciliation/suggestions/{bank_transaction_id}")
async def get_reconciliation_suggestions(bank_transaction_id: str):
    """Get suggested matches for a bank transaction (transactions + crediteuren)"""
    try:
        # Get bank transaction
        bank_trans = await db.bank_transactions.find_one({"id": bank_transaction_id})
        if not bank_trans:
            raise HTTPException(status_code=404, detail="Bank transactie niet gevonden")
        
        bank_amount = bank_trans.get('amount', 0)  # Keep original sign!
        bank_original_amount = bank_trans.get('original_amount', bank_trans.get('amount', 0))
        bank_date = bank_trans.get('date', '')
        bank_description = bank_trans.get('description', '').lower()
        bank_counterparty = bank_trans.get('counterparty', '').lower()
        
        suggestions = []
        
        # Find potential cashflow transaction matches
        if bank_date:
            date_obj = datetime.fromisoformat(bank_date).date() if isinstance(bank_date, str) else bank_date
            start_date = (date_obj - timedelta(days=7)).isoformat()  # Stricter: only 7 days
            end_date = (date_obj + timedelta(days=7)).isoformat()
            
            # CRITICAL: Only match transactions with same sign (positive with positive, negative with negative)
            # AND make matching much stricter
            
            # Match by exact amount first (same sign!)
            exact_matches = await db.transactions.find({
                "reconciled": False,
                "amount": bank_amount,  # Exact amount match including sign
                "date": {"$gte": start_date, "$lte": end_date}
            }).to_list(3)
            
            for match in exact_matches:
                suggestions.append({
                    **Transaction(**parse_from_mongo(match)).dict(),
                    "match_type": "transaction",
                    "match_score": 95,
                    "match_reason": "Exacte bedrag en datum match"
                })
            
            # Only look for similar amounts if no exact matches and be MUCH stricter
            if len(suggestions) == 0:
                # Very strict tolerance: only €1 or 1% difference, whichever is smaller
                amount_tolerance = min(abs(bank_amount) * 0.01, 1.0)  
                
                # Determine sign-based range
                if bank_amount >= 0:
                    # For positive amounts, only match positive transactions
                    min_amount = bank_amount - amount_tolerance
                    max_amount = bank_amount + amount_tolerance
                    sign_filter = {"$gte": 0}
                else:
                    # For negative amounts, only match negative transactions  
                    min_amount = bank_amount - amount_tolerance  # More negative
                    max_amount = bank_amount + amount_tolerance  # Less negative
                    sign_filter = {"$lt": 0}
                
                similar_matches = await db.transactions.find({
                    "reconciled": False,
                    "amount": {
                        "$gte": min_amount,
                        "$lte": max_amount,
                        **sign_filter  # Ensure same sign
                    },
                    "date": {"$gte": start_date, "$lte": end_date}
                }).to_list(2)  # Only 2 suggestions for similar matches
                
                for match in similar_matches:
                    # Double check that signs match
                    if (bank_amount >= 0 and match['amount'] >= 0) or (bank_amount < 0 and match['amount'] < 0):
                        suggestions.append({
                            **Transaction(**parse_from_mongo(match)).dict(),
                            "match_type": "transaction", 
                            "match_score": 75,
                            "match_reason": f"Zeer vergelijkbaar bedrag (±€{amount_tolerance:.2f})"
                        })
        
        # Find potential crediteur matches - ONLY for negative bank transactions (outgoing payments)
        if bank_amount < 0:  # Only match crediteuren with outgoing bank transactions
            crediteuren = await db.crediteuren.find({"actief": True}).to_list(20)
            print(f"DEBUG: Found {len(crediteuren)} crediteuren for matching negative transaction")
            print(f"DEBUG: Bank amount: {bank_amount}, description: '{bank_description}', counterparty: '{bank_counterparty}'")
            
            bank_abs_amount = abs(bank_amount)  # Get absolute value for comparison with crediteur amounts
            
            for crediteur in crediteuren:
                crediteur_amount = crediteur.get('bedrag', 0)
                crediteur_naam = crediteur.get('crediteur', '').lower()
                
                # Much stricter amount matching - must be very close (within €2 or 2%)
                amount_tolerance = min(crediteur_amount * 0.02, 2.0)
                amount_diff = abs(bank_abs_amount - crediteur_amount)
                amount_match = amount_diff <= amount_tolerance
                
                if amount_match:
                    print(f"DEBUG: Amount match for {crediteur_naam}: €{bank_abs_amount} vs €{crediteur_amount} (diff: €{amount_diff:.2f})")
                
                # Match by name/description
                name_match = False
                if crediteur_naam:
                    # Check various name matching scenarios
                    if (crediteur_naam in bank_description or 
                        crediteur_naam in bank_counterparty or
                        bank_counterparty in crediteur_naam or
                        any(word in bank_description for word in crediteur_naam.split() if len(word) > 3)):
                        name_match = True
                        print(f"DEBUG: Name match for {crediteur_naam}")
                
                # Calculate match score - much higher standards
                score = 0
                reasons = []
                if amount_match and name_match:
                    score = 95
                    reasons = ["Exacte bedrag match", "Naam match"]
                elif amount_match:
                    score = 85
                    reasons = ["Exacte bedrag match"]
                elif name_match and amount_diff <= crediteur_amount * 0.1:  # Name match with reasonable amount
                    score = 70
                    reasons = ["Naam match", f"Redelijk bedrag (verschil: €{amount_diff:.2f})"]
                
                # Only suggest if score is high enough (minimum 70)
                if score >= 70:
                    suggestions.append({
                        "id": crediteur['id'],
                        "type": "expense",
                        "category": "crediteur",
                        "amount": crediteur_amount,
                        "description": f"Maandelijkse betaling {crediteur_naam}",
                        "patient_name": crediteur_naam,
                        "invoice_number": f"Crediteur-{crediteur['dag']}e",
                        "match_type": "crediteur",
                        "match_score": score,
                        "match_reason": ", ".join(reasons),
                        "crediteur_dag": crediteur.get('dag', 1)
                    })
        else:
            print(f"DEBUG: Skipping crediteur matching for positive bank transaction: €{bank_amount}")
        
        # Sort by match score
        suggestions.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return suggestions[:8]  # Return top 8 matches
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding suggestions: {str(e)}")

# Nieuwe endpoints voor uitgebreide cashflow management

# Bank Saldo endpoints
@api_router.get("/bank-saldo", response_model=List[BankSaldo])
async def get_bank_saldos():
    """Get all bank saldos"""
    try:
        saldos = await db.bank_saldos.find().sort([("date", -1)]).to_list(100)
        return [BankSaldo(**parse_from_mongo(saldo)) for saldo in saldos]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching bank saldos: {str(e)}")

@api_router.post("/bank-saldo", response_model=BankSaldo)
async def create_bank_saldo(description: str = Form(...), amount: float = Form(...), date: str = Form(...)):
    """Create a bank saldo entry"""
    try:
        saldo_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        # Check if saldo for this date already exists
        existing = await db.bank_saldos.find_one({"date": saldo_date.isoformat()})
        if existing:
            raise HTTPException(status_code=400, detail="Bank saldo voor deze datum bestaat al")
        
        saldo = BankSaldo(
            date=saldo_date,
            saldo=amount,
            description=description
        )
        
        saldo_dict = prepare_for_mongo(saldo.dict())
        await db.bank_saldos.insert_one(saldo_dict)
        
        return saldo
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating bank saldo: {str(e)}")

# Overige Omzet endpoints
@api_router.get("/overige-omzet", response_model=List[OverigeOmzet])
async def get_overige_omzet():
    """Get all overige omzet entries"""
    try:
        omzet = await db.overige_omzet.find().sort([("date", -1)]).to_list(1000)
        return [OverigeOmzet(**parse_from_mongo(o)) for o in omzet]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching overige omzet: {str(e)}")

@api_router.post("/overige-omzet", response_model=OverigeOmzet)
async def create_overige_omzet(description: str = Form(...), amount: float = Form(...), date: str = Form(...), recurring: bool = Form(False)):
    """Create overige omzet entry"""
    try:
        omzet_date = datetime.strptime(date, "%Y-%m-%d").date()
        
        omzet = OverigeOmzet(
            description=description,
            amount=amount,
            date=omzet_date,
            recurring=recurring
        )
        
        omzet_dict = prepare_for_mongo(omzet.dict())
        await db.overige_omzet.insert_one(omzet_dict)
        
        return omzet
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating overige omzet: {str(e)}")

# Correcties endpoints
@api_router.get("/correcties", response_model=List[Correction])
async def get_correcties():
    """Get all corrections"""
    try:
        correcties = await db.correcties.find().sort([("date", -1)]).to_list(1000)
        return [Correction(**parse_from_mongo(correctie)) for correctie in correcties]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching correcties: {str(e)}")

@api_router.post("/correcties", response_model=Correction)
async def create_correctie(correctie: CorrectionCreate):
    """Create a correction"""
    try:
        correction = Correction(**correctie.dict())
        
        # Try to automatically match with original transaction
        if correctie.original_invoice_number:
            # Find original transaction by invoice number
            original = await db.transactions.find_one({
                "invoice_number": correctie.original_invoice_number
            })
            
            if original:
                correction.original_transaction_id = original['id']
                correction.matched = True
                
                # Update original transaction with corrected amount
                corrected_amount = original['amount'] - correction.amount
                await db.transactions.update_one(
                    {"id": original['id']},
                    {"$set": {"amount": corrected_amount}}
                )
        
        correction_dict = prepare_for_mongo(correction.dict())
        await db.correcties.insert_one(correction_dict)
        
        return correction
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating correctie: {str(e)}")

@api_router.post("/correcties/{correctie_id}/match")
async def match_correctie_manual(
    correctie_id: str,
    original_transaction_id: str = Query(...)
):
    """Manually match correction to original transaction"""
    try:
        # Get correction and original transaction
        correctie = await db.correcties.find_one({"id": correctie_id})
        original = await db.transactions.find_one({"id": original_transaction_id})
        
        if not correctie or not original:
            raise HTTPException(status_code=404, detail="Correctie of originele transactie niet gevonden")
        
        # Update correction
        await db.correcties.update_one(
            {"id": correctie_id},
            {"$set": {
                "original_transaction_id": original_transaction_id,
                "matched": True
            }}
        )
        
        # Update original transaction amount
        corrected_amount = original['amount'] - correctie['amount']
        await db.transactions.update_one(
            {"id": original_transaction_id},
            {"$set": {"amount": corrected_amount}}
        )
        
        return {"message": "Correctie succesvol gekoppeld", "new_amount": corrected_amount}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error matching correctie: {str(e)}")

@api_router.get("/correcties/unmatched", response_model=List[Correction])
async def get_unmatched_correcties():
    """Get corrections that haven't been matched yet"""
    try:
        correcties = await db.correcties.find({"matched": False}).sort([("date", -1)]).to_list(1000)
        return [Correction(**parse_from_mongo(correctie)) for correctie in correcties]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching unmatched correcties: {str(e)}")

@api_router.get("/correcties/suggestions/{correctie_id}")
async def get_correction_suggestions(correctie_id: str):
    """Get suggested transactions to match with correction"""
    try:
        correctie = await db.correcties.find_one({"id": correctie_id})
        if not correctie:
            raise HTTPException(status_code=404, detail="Correctie niet gevonden")
        
        suggestions = []
        
        # Find transactions with similar amounts (within 10%)
        correction_amount = abs(correctie.get('amount', 0))  # Use absolute value for comparison
        tolerance = correction_amount * 0.1
        
        # Determine which category to search based on correction type
        search_category = None
        if correctie.get('correction_type') == 'creditfactuur_particulier':
            search_category = "particulier"
        elif correctie.get('correction_type') in ['creditdeclaratie_verzekeraar', 'correctiefactuur_verzekeraar']:
            search_category = "zorgverzekeraar"
        
        # Use aggregation pipeline to get better distributed results
        correction_date_obj = datetime.fromisoformat(correctie['date']).date() if isinstance(correctie['date'], str) else correctie['date']
        correction_date_timestamp = datetime.combine(correction_date_obj, datetime.min.time()).timestamp()
        
        # Build aggregation pipeline
        pipeline = [
            {
                "$match": {
                    "amount": {
                        "$gte": correction_amount - tolerance,
                        "$lte": correction_amount + tolerance + 1000
                    }
                }
            }
        ]
        
        # Add category filter if specified
        if search_category:
            pipeline[0]["$match"]["category"] = search_category
            
        # Add computed fields for better sorting
        pipeline.extend([
            {
                "$addFields": {
                    "date_timestamp": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": {"$dateFromString": {"dateString": "$date"}}}
                    }
                }
            },
            {
                "$sort": {
                    "date": -1,  # Sort by date descending (newest first)
                    "amount": 1   # Then by amount ascending (smaller amounts first for better matches)
                }
            },
            {
                "$limit": 50
            }
        ])
        
        # Execute aggregation
        similar_transactions = await db.transactions.aggregate(pipeline).to_list(50)
        
        for transaction in similar_transactions:
            score = 0
            reasons = []
            
            # Amount similarity scoring (compare absolute values)
            transaction_amount = abs(transaction['amount'])
            amount_diff = abs(transaction_amount - correction_amount)
            if amount_diff <= tolerance:
                score += 50
                reasons.append("Vergelijkbaar bedrag")
            
            # Enhanced patient name matching
            correction_patient = correctie.get('patient_name', '').lower().strip()
            transaction_patient = transaction.get('patient_name', '').lower().strip()
            
            if correction_patient and transaction_patient:
                # Exact match
                if correction_patient == transaction_patient:
                    score += 40
                    reasons.append("Exacte naam match")
                # Contains match (one way or the other)
                elif (correction_patient in transaction_patient or 
                      transaction_patient in correction_patient):
                    score += 30
                    reasons.append("Gedeeltelijke naam match")
                # Split names and check for word matches
                else:
                    correction_words = set(correction_patient.replace(',', ' ').split())
                    transaction_words = set(transaction_patient.replace(',', ' ').split())
                    
                    # Remove common words that don't help matching
                    common_words = {'van', 'de', 'der', 'den', 'het', 'een', 'en', 'te', 'voor', 'naar', 'bij'}
                    correction_words = correction_words - common_words
                    transaction_words = transaction_words - common_words
                    
                    # Calculate word overlap
                    matching_words = correction_words & transaction_words
                    if len(matching_words) >= 2:  # At least 2 matching words
                        score += 25
                        reasons.append(f"Naam woorden match ({len(matching_words)} woorden)")
                    elif len(matching_words) >= 1 and len(correction_words) <= 2:  # For short names
                        score += 15
                        reasons.append("Enkele naam match")
            
            # Date proximity bonus (but don't exclude based on date)
            try:
                correction_date = datetime.fromisoformat(correctie['date']).date() if isinstance(correctie['date'], str) else correctie['date']
                transaction_date = datetime.fromisoformat(transaction['date']).date() if isinstance(transaction['date'], str) else transaction['date']
                
                date_diff = abs((correction_date - transaction_date).days)
                if date_diff <= 90:
                    score += 20 - (date_diff / 5)  # Closer dates get higher scores
                    reasons.append(f"Datum nabij ({date_diff} dagen)")
                elif date_diff <= 365:
                    score += 10 - (date_diff / 30)  # Small bonus for same year
                    reasons.append(f"Zelfde jaar ({date_diff} dagen verschil)")
            except:
                pass
            
            if score > 20:  # Lowered threshold from 40 to 20 to show more matches
                suggestions.append({
                    **Transaction(**parse_from_mongo(transaction)).dict(),
                    "match_score": round(score),
                    "match_reason": ", ".join(reasons)
                })
        
        # Sort by match score
        suggestions.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return suggestions[:20]  # Return top 20 matches (increased from 5)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding suggestions: {str(e)}")

# Correcties Bulk Import - Creditfactuur Particulier
@api_router.post("/correcties/import-creditfactuur")
async def import_creditfactuur_particulier(request: CopyPasteImportRequest):
    """Import creditfacturen voor particuliere patiënten"""
    try:
        # Expected columns for creditfactuur particulier
        expected_columns = [
            "factuur",   # Credit invoice number
            "datum",     # Date of credit
            "debiteur",  # Patient/debtor name  
            "bedrag"     # Credit amount (negative)
        ]
        
        corrections = parse_copy_paste_data(request.data, expected_columns)
        
        if not corrections:
            raise HTTPException(status_code=400, detail="Geen geldige creditfacturen gevonden")
        
        # Process each creditfactuur
        successful_imports = 0
        failed_imports = []
        auto_matched = 0
        
        for i, correction_data in enumerate(corrections):
            try:
                correction_type = "creditfactuur_particulier"
                
                # Parse date (support multiple formats)
                correction_date = correction_data.get('datum')
                if isinstance(correction_date, str):
                    # Try different date formats
                    date_formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]
                    for date_format in date_formats:
                        try:
                            correction_date = datetime.strptime(correction_date, date_format).date()
                            break
                        except ValueError:
                            continue
                    else:
                        # If no format worked, try parsing with dateutil
                        from dateutil import parser
                        correction_date = parser.parse(correction_date, dayfirst=True).date()
                
                # Extract clean patient name (remove factuurnummer prefix)
                debiteur = correction_data.get('debiteur', '')
                patient_name = extract_clean_name(debiteur)
                
                # Create correction object
                correction = Correction(
                    correction_type=correction_type,
                    original_invoice_number='',  # Will try to match by patient name
                    amount=parse_dutch_currency(correction_data.get('bedrag', '0')),  # Keep original sign
                    description=f"Creditfactuur {correction_data.get('factuur', '')} - {patient_name}",
                    date=correction_date,
                    patient_name=patient_name
                )
                
                # Try automatic matching
                if correction.original_invoice_number:
                    # Find original transaction by invoice number - ONLY particuliere facturen
                    original = await db.transactions.find_one({
                        "invoice_number": correction.original_invoice_number,
                        "category": "particulier"  # ONLY match particuliere facturen
                    })
                    
                    if original:
                        correction.original_transaction_id = original['id']
                        correction.matched = True
                        auto_matched += 1
                        
                        # Update original transaction with corrected amount (subtract absolute value)
                        corrected_amount = original['amount'] + correction.amount  # correction.amount is negative, so this subtracts
                        await db.transactions.update_one(
                            {"id": original['id']},
                            {"$set": {"amount": corrected_amount}}
                        )
                
                # Enhanced automatic matching if invoice number match failed
                if not correction.matched and correction.patient_name:
                    # Try to match by patient name and amount similarity - ONLY particuliere facturen
                    potential_matches = await db.transactions.find({
                        "patient_name": {"$regex": correction.patient_name, "$options": "i"},
                        "amount": {"$gte": correction.amount * 0.8, "$lte": correction.amount * 5},  # Amount range
                        "category": "particulier"  # ONLY match particuliere facturen
                    }).limit(5).to_list(5)
                    
                    for potential in potential_matches:
                        # Score the match
                        name_similarity = len(set(correction.patient_name.lower().split()) & 
                                           set(potential.get('patient_name', '').lower().split()))
                        amount_ratio = min(correction.amount / potential['amount'], 
                                         potential['amount'] / correction.amount)
                        
                        if name_similarity >= 2 and amount_ratio >= 0.8:  # Good match
                            correction.original_transaction_id = potential['id']
                            correction.matched = True
                            auto_matched += 1
                            
                            # Update original transaction
                            corrected_amount = potential['amount'] - correction.amount
                            await db.transactions.update_one(
                                {"id": potential['id']},
                                {"$set": {"amount": corrected_amount}}
                            )
                            break
                
                # Save correction
                correction_dict = prepare_for_mongo(correction.dict())
                await db.correcties.insert_one(correction_dict)
                successful_imports += 1
                
            except Exception as e:
                failed_imports.append(f"Rij {i+2}: {str(e)}")
                continue
        
        return {
            "message": f"Import voltooid: {successful_imports} creditfacturen geïmporteerd",
            "successful_imports": successful_imports,
            "failed_imports": len(failed_imports),
            "auto_matched": auto_matched,
            "errors": failed_imports[:10],
            "total_corrections": len(corrections)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing creditfacturen: {str(e)}")

# Correcties Bulk Import - Creditdeclaratie Verzekeraar
@api_router.post("/correcties/import-creditdeclaratie")
async def import_creditdeclaratie_verzekeraar(request: CopyPasteImportRequest):
    """Import creditdeclaraties voor zorgverzekeraars"""
    try:
        expected_columns = [
            "factuur",          # Credit invoice number
            "datum",             # Date of credit
            "verzekeraar",       # Insurance company name
            "factuur_origineel", # Original invoice number to match
            "bedrag"             # Credit amount (negative)
        ]
        
        corrections = parse_copy_paste_data(request.data, expected_columns)
        
        if not corrections:
            raise HTTPException(status_code=400, detail="Geen geldige creditdeclaraties gevonden")
        
        successful_imports = 0
        failed_imports = []
        auto_matched = 0
        
        for i, correction_data in enumerate(corrections):
            try:
                correction_date = correction_data.get('datum')
                if isinstance(correction_date, str):
                    # Try different date formats
                    date_formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]
                    for date_format in date_formats:
                        try:
                            correction_date = datetime.strptime(correction_date, date_format).date()
                            break
                        except ValueError:
                            continue
                    else:
                        # If no format worked, try parsing with dateutil
                        from dateutil import parser
                        correction_date = parser.parse(correction_date, dayfirst=True).date()
                
                correction = Correction(
                    correction_type="creditdeclaratie_verzekeraar",
                    original_invoice_number=correction_data.get('factuur_origineel', ''),
                    amount=parse_dutch_currency(correction_data.get('bedrag', '0')),  # Keep original sign
                    description=f"Creditdeclaratie {correction_data.get('factuur', '')} - {correction_data.get('verzekeraar', '')}",
                    date=correction_date,
                    patient_name=''
                )
                
                # Try automatic matching by original invoice number
                if correction.original_invoice_number:
                    original = await db.transactions.find_one({
                        "invoice_number": correction.original_invoice_number,
                        "category": "zorgverzekeraar"
                    })
                    
                    if original:
                        correction.original_transaction_id = original['id']
                        correction.matched = True
                        auto_matched += 1
                        
                        corrected_amount = original['amount'] + correction.amount  # correction.amount is negative
                        await db.transactions.update_one(
                            {"id": original['id']},
                            {"$set": {"amount": corrected_amount}}
                        )
                
                correction_dict = prepare_for_mongo(correction.dict())
                await db.correcties.insert_one(correction_dict)
                successful_imports += 1
                
            except Exception as e:
                failed_imports.append(f"Rij {i+2}: {str(e)}")
                continue
        
        return {
            "message": f"Import voltooid: {successful_imports} creditdeclaraties geïmporteerd",
            "successful_imports": successful_imports,
            "failed_imports": len(failed_imports),
            "auto_matched": auto_matched,
            "errors": failed_imports[:10],
            "total_corrections": len(corrections)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing creditdeclaraties: {str(e)}")

# Correcties Bulk Import - Correctiefactuur Verzekeraar
@api_router.post("/correcties/import-correctiefactuur")
async def import_correctiefactuur_verzekeraar(request: CopyPasteImportRequest):
    """Import correctiefacturen voor zorgverzekeraars"""
    try:
        expected_columns = [
            "factuur",          # Correction invoice number
            "datum",             # Date of correction
            "verzekeraar",       # Insurance company name
            "factuur_origineel", # Original invoice number to match
            "bedrag"             # Correction amount (negative)
        ]
        
        corrections = parse_copy_paste_data(request.data, expected_columns)
        
        if not corrections:
            raise HTTPException(status_code=400, detail="Geen geldige correctiefacturen gevonden")
        
        successful_imports = 0
        failed_imports = []
        auto_matched = 0
        
        for i, correction_data in enumerate(corrections):
            try:
                correction_date = correction_data.get('datum')
                if isinstance(correction_date, str):
                    # Try different date formats
                    date_formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]
                    for date_format in date_formats:
                        try:
                            correction_date = datetime.strptime(correction_date, date_format).date()
                            break
                        except ValueError:
                            continue
                    else:
                        # If no format worked, try parsing with dateutil
                        from dateutil import parser
                        correction_date = parser.parse(correction_date, dayfirst=True).date()
                
                correctie_bedrag = parse_dutch_currency(correction_data.get('bedrag', '0'))
                
                correction = Correction(
                    correction_type="correctiefactuur_verzekeraar",
                    original_invoice_number=correction_data.get('factuur_origineel', ''),
                    amount=correctie_bedrag,
                    description=f"Correctiefactuur {correction_data.get('factuur', '')} - {correction_data.get('verzekeraar', '')}",
                    date=correction_date,
                    patient_name=''
                )
                
                # Try automatic matching by original invoice number
                if correction.original_invoice_number:
                    original = await db.transactions.find_one({
                        "invoice_number": correction.original_invoice_number,
                        "category": "zorgverzekeraar"
                    })
                    
                    if original:
                        correction.original_transaction_id = original['id']
                        correction.matched = True
                        auto_matched += 1
                        
                        # Add correction amount (correctie_bedrag is negative)
                        corrected_amount = original['amount'] + correctie_bedrag
                        await db.transactions.update_one(
                            {"id": original['id']},
                            {"$set": {"amount": corrected_amount}}
                        )
                
                correction_dict = prepare_for_mongo(correction.dict())
                await db.correcties.insert_one(correction_dict)
                successful_imports += 1
                
            except Exception as e:
                failed_imports.append(f"Rij {i+2}: {str(e)}")
                continue
        
        return {
            "message": f"Import voltooid: {successful_imports} correctiefacturen geïmporteerd",
            "successful_imports": successful_imports,
            "failed_imports": len(failed_imports),
            "auto_matched": auto_matched,
            "errors": failed_imports[:10],
            "total_corrections": len(corrections)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error importing correctiefacturen: {str(e)}")

# Data Cleanup Endpoints
@api_router.delete("/cleanup/all-data")
async def cleanup_all_data():
    """DANGEROUS: Delete all data for fresh start"""
    try:
        # Delete all collections
        await db.transactions.delete_many({})
        await db.crediteuren.delete_many({})
        await db.verzekeraars.delete_many({})
        await db.correcties.delete_many({})
        await db.bank_transactions.delete_many({})
        await db.bank_saldos.delete_many({})
        await db.overige_omzet.delete_many({})
        
        return {
            "message": "Alle data succesvol verwijderd",
            "deleted_collections": [
                "transactions", "crediteuren", "verzekeraars", 
                "correcties", "bank_transactions", "bank_saldos", "overige_omzet"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during cleanup: {str(e)}")

@api_router.delete("/cleanup/corrections")
async def cleanup_corrections():
    """Delete all corrections data"""
    try:
        result = await db.correcties.delete_many({})
        return {
            "message": f"Alle correcties verwijderd: {result.deleted_count} items",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting corrections: {str(e)}")

@api_router.delete("/cleanup/transactions")
async def cleanup_transactions():
    """Delete all transactions data"""
    try:
        result = await db.transactions.delete_many({})
        return {
            "message": f"Alle transacties verwijderd: {result.deleted_count} items",
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting transactions: {str(e)}")

@api_router.delete("/cleanup/bank-transactions")
async def cleanup_bank_transactions():
    """Delete all bank transactions data"""
    try:
        result = await db.bank_transactions.delete_many({})
        return {
            "message": f"Alle bank transacties verwijderd: {result.deleted_count} items", 
            "deleted_count": result.deleted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting bank transactions: {str(e)}")

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

# Cashflow planning endpoints
@api_router.get("/cashflow-forecast")
async def get_cashflow_forecast(days: int = 30):
    """Get daily cashflow forecast for the next N days"""
    try:
        forecast_days = []
        start_date = date.today()
        
        # Get current bank balance from database
        bank_saldos = await db.bank_saldos.find().sort([("date", -1)]).to_list(1)
        if bank_saldos:
            current_balance = bank_saldos[0].get('saldo', 0.0)
        else:
            current_balance = 0.0  # Default if no bank saldo set
        
        print(f"DEBUG: Starting balance from bank_saldos: €{current_balance}")
        
        # Get all verwachte betalingen
        verwachte_betalingen = []
        
        # Declaratie betalingen (inkomsten) - Only include recent unreconciled income that will result in future payments
        # Don't include old transactions that are unlikely to be paid
        min_transaction_date = start_date - timedelta(days=60)  # Only transactions from last 60 days
        
        transactions = await db.transactions.find({
            "type": "income",
            "reconciled": False,
            "date": {"$gte": min_transaction_date.isoformat()}  # Only recent transactions
        }).to_list(500)  # Reduced limit
        
        print(f"DEBUG: Found {len(transactions)} recent unreconciled income transactions for forecast (last 60 days)")
        
        verzekeraars = await db.verzekeraars.find({"actief": True}).to_list(1000)
        verzekeraars_dict = {v['naam']: v['termijn'] for v in verzekeraars}
        
        for trans in transactions:
            transaction_date = datetime.fromisoformat(trans['date']).date()
            patient_name = trans.get('patient_name', '')
            
            # Find termijn
            termijn = 30  # Default
            for verzekeraar_naam, verzekeraar_termijn in verzekeraars_dict.items():
                if verzekeraar_naam.lower() in patient_name.lower():
                    termijn = verzekeraar_termijn
                    break
            
            # Calculate expected payment date
            verwachte_datum = transaction_date + timedelta(days=termijn)
            
            # Determine payment terms based on category
            if trans.get('category') == 'particulier':
                # Particuliere patiënten betalen meestal direct
                verwachte_datum = transaction_date + timedelta(days=7)  # 1 week
            
            # Only include if payment date is in the future (within forecast period)
            if verwachte_datum >= start_date and verwachte_datum <= start_date + timedelta(days=days):
                # Apply any corrections to this transaction
                original_amount = trans['amount']
                corrected_amount = original_amount
                
                # Find corrections for this transaction
                corrections = await db.correcties.find({
                    "original_transaction_id": trans['id'],
                    "matched": True
                }).to_list(10)
                
                for correction in corrections:
                    corrected_amount += correction.get('amount', 0)  # Corrections are usually negative
                
                # Only include if there's still an amount to expect after corrections
                if corrected_amount > 0:
                    verwachte_betalingen.append({
                        'datum': verwachte_datum,
                        'bedrag': corrected_amount,  # Use corrected amount
                        'type': 'inkomst',
                        'beschrijving': f"Declaratie {trans.get('invoice_number', '')} (gecorrigeerd: €{corrected_amount:.2f})" if corrected_amount != original_amount else f"Declaratie {trans.get('invoice_number', '')}"
                    })
        
        # Crediteur betalingen (uitgaven)
        crediteuren = await db.crediteuren.find({"actief": True}).to_list(1000)
        for crediteur in crediteuren:
            # Calculate next few months of payments
            for month_offset in range(0, 3):  # Next 3 months
                try:
                    target_date = start_date.replace(day=1) + timedelta(days=32 * month_offset)
                    target_date = target_date.replace(day=crediteur['dag'])
                    
                    if target_date >= start_date and target_date <= start_date + timedelta(days=days):
                        verwachte_betalingen.append({
                            'datum': target_date,
                            'bedrag': -crediteur['bedrag'],  # Negative for expense
                            'type': 'uitgave',
                            'beschrijving': f"Betaling {crediteur['crediteur']}"
                        })
                except ValueError:
                    # Skip invalid dates (like 31st in February)
                    continue
        
        # Add overige omzet (other revenue)
        overige_omzet_items = await db.overige_omzet.find({"recurring": True}).to_list(100)
        for omzet in overige_omzet_items:
            # For recurring revenue, add monthly occurrences
            omzet_date = datetime.fromisoformat(omzet['date']).date() if isinstance(omzet['date'], str) else omzet['date']
            
            # Calculate next occurrences in forecast period
            current_month = start_date.replace(day=omzet_date.day)
            for month_offset in range(0, 3):  # Next 3 months
                try:
                    next_occurrence = current_month + timedelta(days=32 * month_offset)
                    next_occurrence = next_occurrence.replace(day=omzet_date.day)
                    
                    if start_date <= next_occurrence <= start_date + timedelta(days=days):
                        verwachte_betalingen.append({
                            'datum': next_occurrence,
                            'bedrag': omzet['amount'],
                            'type': 'inkomst',
                            'beschrijving': f"Overige omzet: {omzet['description']}"
                        })
                except ValueError:
                    continue
        
        # Add geclassificeerde vaste kosten (from bank reconciliation)
        # These should repeat monthly based on historical classification patterns
        vaste_kosten_categories = await db.vaste_kosten.find({"active": True}).to_list(1000)
        
        # Group by category and calculate monthly average
        vaste_kosten_monthly = {}
        for kost in vaste_kosten_categories:
            category = kost['category_name']
            if category not in vaste_kosten_monthly:
                vaste_kosten_monthly[category] = []
            vaste_kosten_monthly[category].append(kost['amount'])
        
        # Add monthly recurring vaste kosten to forecast
        for category, amounts in vaste_kosten_monthly.items():
            monthly_average = sum(amounts) / len(amounts) if amounts else 0
            if monthly_average > 0:
                # Add monthly on the 15th of each month (or start date if we're already past 15th)
                current_month_start = start_date.replace(day=1)
                for month_offset in range(0, 2):  # Current and next month
                    try:
                        target_date = current_month_start + timedelta(days=32 * month_offset)
                        target_date = target_date.replace(day=15)  # 15th of month
                        
                        if target_date < start_date:
                            # If 15th already passed this month, use next month
                            continue
                            
                        if start_date <= target_date <= start_date + timedelta(days=days):
                            verwachte_betalingen.append({
                                'datum': target_date,
                                'bedrag': -monthly_average,  # Negative for expense
                                'type': 'uitgave',
                                'beschrijving': f"Vaste kosten: {category} (gemiddeld)"
                            })
                    except ValueError:
                        continue
        
        # Add geclassificeerde variabele kosten (estimated based on recent pattern)
        variabele_kosten_categories = await db.variabele_kosten.find({"active": True}).to_list(1000)
        
        # Group by category and calculate recent pattern (last 90 days)
        recent_cutoff = start_date - timedelta(days=90)
        variabele_kosten_recent = {}
        
        for kost in variabele_kosten_categories:
            kost_date = datetime.fromisoformat(kost['date']).date() if isinstance(kost['date'], str) else kost['date']
            if kost_date >= recent_cutoff:  # Only recent variable costs
                category = kost['category_name']
                if category not in variabele_kosten_recent:
                    variabele_kosten_recent[category] = []
                variabele_kosten_recent[category].append(kost['amount'])
        
        # Estimate variabele kosten frequency (monthly estimate)
        for category, amounts in variabele_kosten_recent.items():
            if len(amounts) > 0:
                monthly_estimate = sum(amounts) * (30 / 90)  # Scale to monthly
                if monthly_estimate > 10:  # Only include if significant
                    # Add estimated variabele kosten in middle of month
                    target_date = start_date + timedelta(days=15)
                    if target_date <= start_date + timedelta(days=days):
                        verwachte_betalingen.append({
                            'datum': target_date,
                            'bedrag': -monthly_estimate,  # Negative for expense
                            'type': 'uitgave',
                            'beschrijving': f"Variabele kosten: {category} (geschat)"
                        })
        
        print(f"DEBUG: Total verwachte betalingen (including classified costs): {len(verwachte_betalingen)} items")
        
        # Generate daily forecast
        for day_offset in range(days):
            forecast_date = start_date + timedelta(days=day_offset)
            
            # Calculate payments for this day
            daily_inkomsten = sum(
                p['bedrag'] for p in verwachte_betalingen 
                if p['datum'] == forecast_date and p['bedrag'] > 0
            )
            daily_uitgaven = sum(
                p['bedrag'] for p in verwachte_betalingen 
                if p['datum'] == forecast_date and p['bedrag'] < 0
            )
            daily_net = daily_inkomsten + daily_uitgaven
            
            # Update running balance
            current_balance += daily_net
            
            forecast_days.append({
                'date': forecast_date.isoformat(),
                'expected_income': daily_inkomsten,  # Frontend expects this name
                'expected_expenses': daily_uitgaven,  # Keep negative for frontend
                'inkomsten': daily_inkomsten,  # Keep for backward compatibility
                'uitgaven': abs(daily_uitgaven),  # Keep for backward compatibility
                'net_cashflow': daily_net,
                'ending_balance': current_balance,  # Frontend expects this name
                'verwachte_saldo': current_balance,  # Keep for backward compatibility
                'payments': [
                    p for p in verwachte_betalingen 
                    if p['datum'] == forecast_date
                ]
            })
        
        return {
            'start_date': start_date.isoformat(),
            'forecast_days': forecast_days,
            'total_expected_income': sum(p['bedrag'] for p in verwachte_betalingen if p['bedrag'] > 0),
            'total_expected_expenses': sum(p['bedrag'] for p in verwachte_betalingen if p['bedrag'] < 0),
            'net_expected': sum(p['bedrag'] for p in verwachte_betalingen)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating cashflow forecast: {str(e)}")

@api_router.get("/dashboard-summary")
async def get_dashboard_summary():
    """Get comprehensive dashboard summary with key metrics"""
    try:
        today = date.today()
        
        # Basic cashflow summary
        cashflow_summary = await get_cashflow_summary()
        
        # Onbekende bank transacties
        unmatched_bank = await db.bank_transactions.count_documents({"reconciled": False})
        
        # Verwachte betalingen vandaag en deze week
        verwachte_betalingen = await get_verwachte_betalingen()
        today_payments = [p for p in verwachte_betalingen if p.get('verwachte_datum') == today.isoformat()]
        
        week_end = today + timedelta(days=7)
        week_payments = [
            p for p in verwachte_betalingen 
            if today.isoformat() <= p.get('verwachte_datum', '') <= week_end.isoformat()
        ]
        
        # Overdue betalingen
        overdue_payments = [
            p for p in verwachte_betalingen
            if p.get('verwachte_datum', '') < today.isoformat() and p.get('status') != 'betaald'
        ]
        
        # Cashflow forecast voor komende week
        forecast = await get_cashflow_forecast(7)
        
        return {
            'cashflow_summary': cashflow_summary,
            'verwachte_betalingen_vandaag': len(today_payments),
            'verwachte_betalingen_week': len(week_payments),
            'overdue_betalingen': len(overdue_payments),
            'onbekende_bank_transacties': unmatched_bank,
            'week_forecast': forecast['forecast_days'],
            'total_verwachte_inkomsten': sum(p.get('bedrag', 0) for p in week_payments if p.get('bedrag', 0) > 0),
            'total_verwachte_uitgaven': abs(sum(p.get('bedrag', 0) for p in week_payments if p.get('bedrag', 0) < 0))
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting dashboard summary: {str(e)}")

# Kosten Classificatie Endpoints
@api_router.post("/bank-reconciliation/classify/{bank_transaction_id}")
async def classify_bank_transaction(
    bank_transaction_id: str,
    classification_type: str = Query(..., regex="^(vast|variabel)$"),
    category_name: str = Query(..., description="Naam van de kosten categorie")
):
    """Classificeer een niet-gematchte banktransactie als vaste of variabele kosten"""
    try:
        # Find the bank transaction
        bank_transaction = await db.bank_transactions.find_one({"id": bank_transaction_id})
        if not bank_transaction:
            raise HTTPException(status_code=404, detail="Bank transactie niet gevonden")
        
        if bank_transaction.get('reconciled', False):
            raise HTTPException(status_code=400, detail="Deze transactie is al gereconcilieerd")
        
        # Ensure it's a negative amount (expense)
        transaction_amount = bank_transaction['amount']
        if transaction_amount > 0:
            raise HTTPException(status_code=400, detail="Alleen uitgaven (negatieve bedragen) kunnen worden geclassificeerd")
        
        # Create the classification record
        classification = {
            'id': str(uuid.uuid4()),
            'bank_transaction_id': bank_transaction_id,
            'classification_type': classification_type,  # 'vast' of 'variabel'
            'category_name': category_name,
            'amount': abs(transaction_amount),  # Store as positive amount
            'date': bank_transaction.get('date'),
            'description': bank_transaction.get('description', ''),
            'counterparty': bank_transaction.get('counterparty_name', ''),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'active': True
        }
        
        # Store in appropriate collection
        if classification_type == 'vast':
            await db.vaste_kosten.insert_one(classification)
        elif classification_type == 'variabel':
            await db.variabele_kosten.insert_one(classification)
        
        # Mark bank transaction as reconciled
        await db.bank_transactions.update_one(
            {"id": bank_transaction_id},
            {"$set": {
                "reconciled": True,
                "reconciled_date": datetime.now(timezone.utc).isoformat(),
                "classification_type": classification_type,
                "classification_id": classification['id']
            }}
        )
        
        return {
            "message": f"Transactie succesvol geclassificeerd als {classification_type}e kosten",
            "classification_id": classification['id'],
            "classification_type": classification_type,
            "category_name": category_name,
            "amount": classification['amount']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error classifying transaction: {str(e)}")

@api_router.get("/vaste-kosten")
async def get_vaste_kosten():
    """Get all vaste kosten categorieën"""
    try:
        kosten = await db.vaste_kosten.find({"active": True}).sort([("created_at", -1)]).to_list(1000)
        
        # Group by category_name and sum amounts
        categories = {}
        for kost in kosten:
            category = kost['category_name']
            if category not in categories:
                categories[category] = {
                    'category_name': category,
                    'total_amount': 0,
                    'transaction_count': 0,
                    'transactions': []
                }
            categories[category]['total_amount'] += kost['amount']
            categories[category]['transaction_count'] += 1
            categories[category]['transactions'].append({
                'id': kost['id'],
                'date': kost['date'],
                'amount': kost['amount'],
                'description': kost['description'],
                'counterparty': kost.get('counterparty', ''),
                'bank_transaction_id': kost['bank_transaction_id']
            })
        
        return list(categories.values())
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching vaste kosten: {str(e)}")

@api_router.get("/variabele-kosten") 
async def get_variabele_kosten():
    """Get all variabele kosten categorieën"""
    try:
        kosten = await db.variabele_kosten.find({"active": True}).sort([("created_at", -1)]).to_list(1000)
        
        # Group by category_name and sum amounts
        categories = {}
        for kost in kosten:
            category = kost['category_name']
            if category not in categories:
                categories[category] = {
                    'category_name': category,
                    'total_amount': 0,
                    'transaction_count': 0,
                    'transactions': []
                }
            categories[category]['total_amount'] += kost['amount']
            categories[category]['transaction_count'] += 1
            categories[category]['transactions'].append({
                'id': kost['id'],
                'date': kost['date'],
                'amount': kost['amount'],
                'description': kost['description'],
                'counterparty': kost.get('counterparty', ''),
                'bank_transaction_id': kost['bank_transaction_id']
            })
        
        return list(categories.values())
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching variabele kosten: {str(e)}")

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