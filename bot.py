import os
import sqlite3
import pandas as pd
import tempfile
from fpdf import FPDF
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

import logging
logging.basicConfig(level=logging.DEBUG)

# 🔹 Get Bot Token from Environment Variable (Security Fix)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 🔹 Admin User ID (Only this user can access student list)
ADMIN_ID = 304943570  # Replace with your Telegram User ID

# 🔹 Database Path (Ensures it works in Railway)
DB_PATH = os.path.join(os.getcwd(), "students.db")

# ✅ Function to Get Database Connection
def get_db_connection():
    if not os.path.exists(DB_PATH):
        logging.error(f"🚨 Database file not found at {DB_PATH}")
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# ✅ Ensure Database & Table Exists
def initialize_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE,
        name TEXT,
        department TEXT,
        phone TEXT
    );
    """)
    conn.commit()
    conn.close()

initialize_db()  # ✅ Run this once at startup

# 💚 Conversation States
ID, NAME, DEPARTMENT, PHONE = range(4)

# ✅ Start Command
async def start(update: Update, context: CallbackContext) -> int:
    logging.debug("start function called")
    await update.message.reply_text("Welcome! Please enter your Student ID:")
    return ID

# ✅ Student Registration Steps
async def get_id(update: Update, context: CallbackContext) -> int:
    context.user_data["student_id"] = update.message.text
    await update.message.reply_text("Enter your Full Name:")
    return NAME

async def get_name(update: Update, context: CallbackContext) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Enter your Department:")
    return DEPARTMENT

async def get_department(update: Update, context: CallbackContext) -> int:
    context.user_data["department"] = update.message.text
    await update.message.reply_text("Enter your Phone Number:")
    return PHONE

# ✅ Save Student Data to Database
async def get_phone(update: Update, context: CallbackContext) -> int:
    context.user_data["phone"] = update.message.text
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO students (student_id, name, department, phone)
            VALUES (?, ?, ?, ?)
        """, (
            context.user_data["student_id"],
            context.user_data["name"],
            context.user_data["department"],
            context.user_data["phone"]
        ))
        conn.commit()
        await update.message.reply_text("✅ Registration successful!")
    except sqlite3.IntegrityError:
        await update.message.reply_text("❌ Error: This Student ID is already registered.")
    finally:
        cursor.close()
        conn.close()

    return ConversationHandler.END

# ✅ Cancel Registration
async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("❌ Registration canceled.")
    return ConversationHandler.END

# ✅ Generate and Send Student List (Admin Only)
async def send_student_list(update: Update, context: CallbackContext) -> None:
    logging.debug("send_student_list function called")
    
    if update.message.chat_id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to access the student list.")
        return

    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM students", conn)
    conn.close()

    if df.empty:
        await update.message.reply_text("📂 No students registered yet.")
        return

    # 🔹 Export to Excel (Temp File)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_xlsx:
        df.to_excel(temp_xlsx.name, index=False)
        temp_xlsx_path = temp_xlsx.name

    # 🔹 Export to PDF (Temp File)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Student List", ln=True, align="C")

    # Column headers
    pdf.ln(10)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(30, 10, "ID", border=1, align="C")
    pdf.cell(50, 10, "Name", border=1, align="C")
    pdf.cell(50, 10, "Student ID", border=1, align="C")
    pdf.cell(40, 10, "Department", border=1, align="C")
    pdf.cell(30, 10, "Phone", border=1, align="C")
    pdf.ln()

    # Table content
    pdf.set_font("Arial", size=12)
    for _, row in df.iterrows():
        pdf.cell(30, 10, str(row['id']), border=1, align="C")
        pdf.cell(50, 10, row['name'], border=1, align="C")
        pdf.cell(50, 10, row['student_id'], border=1, align="C")
        pdf.cell(40, 10, row['department'], border=1, align="C")
        pdf.cell(30, 10, row['phone'], border=1, align="C")
        pdf.ln()

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        pdf.output(temp_pdf.name)
        temp_pdf_path = temp_pdf.name

    # 🔹 Send Files to Admin
    await context.bot.send_document(chat_id=ADMIN_ID, document=open(temp_xlsx_path, "rb"), caption="📄 Student List (Excel)")
    await context.bot.send_document(chat_id=ADMIN_ID, document=open(temp_pdf_path, "rb"), caption="📄 Student List (PDF)")

    os.remove(temp_xlsx_path)  # ✅ Cleanup after sending
    os.remove(temp_pdf_path)

# ✅ Main Function - Runs the Bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            DEPARTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_department)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("list", send_student_list))

    app.run_polling()

if __name__ == "__main__":
    main()
