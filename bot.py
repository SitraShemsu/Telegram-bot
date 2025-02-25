import sqlite3
import pandas as pd
from fpdf import FPDF
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)

# Bot Token and Admin ID
BOT_TOKEN = "8122286178:AAG6BemHsT1kmb3RqDJOKnrR8WvDNWpVABE"
ADMIN_ID = 304943570  # Replace with your Telegram User ID

# Database connection function
def get_db_connection():
    conn = sqlite3.connect("students.db", check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT NOT NULL
    )''')
    conn.commit()
    return conn

# Conversation states
ID, NAME, DEPARTMENT = range(3)

async def start(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("Welcome! Please enter your Student ID:")
    return ID

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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO students (student_id, name, department) VALUES (?, ?, ?)", (
            context.user_data["student_id"],
            context.user_data["name"],
            context.user_data["department"]
        ))
        conn.commit()
        await update.message.reply_text("✅ Registration successful!")
    except sqlite3.IntegrityError:
        await update.message.reply_text("❌ Error: This Student ID is already registered.")
    finally:
        conn.close()
    return ConversationHandler.END

async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("❌ Registration canceled.")
    return ConversationHandler.END

async def send_student_list(update: Update, context: CallbackContext) -> None:
    if update.message.chat_id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to access the student list.")
        return
    
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM students", conn)
    conn.close()
    
    if df.empty:
        await update.message.reply_text("📂 No students registered yet.")
        return
    
    excel_file = "student_list.xlsx"
    df.to_excel(excel_file, index=False)
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, "Student List", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(40, 10, "Student ID", border=1, align="C")
    pdf.cell(60, 10, "Name", border=1, align="C")
    pdf.cell(60, 10, "Department", border=1, align="C")
    pdf.ln()
    
    pdf.set_font("Arial", size=12)
    for _, row in df.iterrows():
        pdf.cell(40, 10, row['student_id'], border=1, align="C")
        pdf.cell(60, 10, row['name'], border=1, align="C")
        pdf.cell(60, 10, row['department'], border=1, align="C")
        pdf.ln()
    
    pdf_file = "student_list.pdf"
    pdf.output(pdf_file)
    
    await update.message.reply_text("📄 Sending student list...")
    await context.bot.send_document(chat_id=ADMIN_ID, document=open(excel_file, "rb"), caption="📄 Student List (Excel)")
    await context.bot.send_document(chat_id=ADMIN_ID, document=open(pdf_file, "rb"), caption="📄 Student List (PDF)")

# Main function
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            DEPARTMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_department)]
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("list", send_student_list))
    
    app.run_polling()

if __name__ == "__main__":
    main()
