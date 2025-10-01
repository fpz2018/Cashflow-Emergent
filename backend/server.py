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
from datetime import datetime, date, timezone
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