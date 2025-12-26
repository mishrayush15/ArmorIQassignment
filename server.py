from fastapi import FastAPI
from pydantic import BaseModel,  EmailStr
import sqlite3

app = FastAPI()
conn = sqlite3.connect("bank.db", check_same_thread=False)
cursor = conn.cursor()

class CreateAccountRequest(BaseModel):
    name: str
    email: EmailStr
    initial_balance: float

class DepositRequest(BaseModel):
    email: EmailStr
    amount: float

class WithdrawRequest(BaseModel):
    email: EmailStr
    amount: float


def init_db():
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        balance REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER,
        type TEXT,
        amount REAL
    )
    """)

    conn.commit()


@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/health")
def health_check():
    return {"msg" : "Server is healthy!"}

@app.post("/create-account")
def create_account(data: CreateAccountRequest):

    cursor.execute(
        "SELECT id FROM accounts WHERE email = ?",
        (data.email,)
    )
    existing = cursor.fetchone()

    if existing:
        return {"error": "Account with this email already exists"}

    cursor.execute(
        "INSERT INTO accounts (name, email, balance) VALUES (?, ?, ?)",
        (data.name, data.email, data.initial_balance)
    )
    conn.commit()

    account_id = cursor.lastrowid

    return {
        "message": "Account created successfully",
        "account_id": account_id
    }

@app.post("/deposit")
def deposit_money(data: DepositRequest):

    cursor.execute(
        "SELECT id, balance FROM accounts WHERE email = ?",
        (data.email,)
    )
    account = cursor.fetchone()

    if not account:
        return {"error": "Account not found"}

    account_id = account[0]

    cursor.execute(
        "UPDATE accounts SET balance = balance + ? WHERE id = ?",
        (data.amount, account_id)
    )

    cursor.execute(
        "INSERT INTO transactions (account_id, type, amount) VALUES (?, ?, ?)",
        (account_id, "deposit", data.amount)
    )

    conn.commit()

    return {
        "message": "Deposit successful",
        "amount": data.amount
    }

@app.post("/withdraw")
def withdraw_money(data: WithdrawRequest):

    cursor.execute(
        "SELECT id, balance FROM accounts WHERE email = ?",
        (data.email,)
    )
    account = cursor.fetchone()

    if not account:
        return {"error": "Account not found"}

    account_id, balance = account

    if balance < data.amount:
        return {"error": "Insufficient balance"}

    cursor.execute(
        "UPDATE accounts SET balance = balance - ? WHERE id = ?",
        (data.amount, account_id)
    )

    cursor.execute(
        "INSERT INTO transactions (account_id, type, amount) VALUES (?, ?, ?)",
        (account_id, "withdraw", data.amount)
    )

    conn.commit()

    return {
        "message": "Withdrawal successful",
        "amount": data.amount
    }

@app.get("/balance")
def get_balance(email: EmailStr):
    
    cursor.execute(
        "SELECT balance FROM accounts WHERE email = ?",
        (email,)
    )
    result = cursor.fetchone()

    if not result:
        return {"error": "Account not found"}

    return {
        "email": email,
        "balance": result[0]
    }

@app.get("/transactions")
def get_transactions(email: EmailStr):

    cursor.execute(
        "SELECT id FROM accounts WHERE email = ?",
        (email,)
    )
    account = cursor.fetchone()

    if not account:
        return {"error": "Account not found"}

    account_id = account[0]

    cursor.execute(
        """
        SELECT type, amount
        FROM transactions
        WHERE account_id = ?
        ORDER BY id DESC
        """,
        (account_id,)
    )

    rows = cursor.fetchall()

    transactions = []
    for row in rows:
        transactions.append({
            "type": row[0],
            "amount": row[1]
        })

    return {
        "email": email,
        "transactions": transactions
    }
