import sqlite3
import pandas as pd
from fpdf import FPDF
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

import logging
logging.basicConfig(level=logging.DEBUG)

# 🔹 Telegram Bot Token (Replace with your actual bot token)
BOT_TOKEN = "8122286178:AAG6BemHsT1kmb3RqDJOKnrR8WvDNWpVABE"

# 🔹 Admin User ID (Only this user can access student list)
ADMIN_ID = 304943570  # Replace with your Telegram User ID

# 🔹 Database Connection Function (Handles multiple users)
def get_db_connection():
    return sqlite3.connect("students.db", check_same_thread=False)

# 🔹 Conversation States
ID, NAME, DEPARTMENT = range(3)

# ✅ Start Command - Greets User
async def start(update: Update, context: CallbackContext) -> int:
    logging.debug("start function called")
    await update.message.reply_text("Welcome! Please enter your Student ID:")
    return ID

# ✅ Student Registration Process
async def get_id(update: Update, context: CallbackContext) -> int:
    context.user_data["student_id"] = update.message.text
    await update.message.reply_text("Enter your Full Name:")
    return NAME

async def get_name(update: Update, context: CallbackContext) -> int:
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Enter your Department:")
    return DEPARTMENT

# ✅ Save Student Data to Database
async def get_department(update: Update, context: CallbackContext) -> int:
    context.user_data["department"] = update.message.text

    # Connect to database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert student data
    try:
        cursor.execute("""
            INSERT INTO students (student_id, name, department)
            VALUES (?, ?, ?)
        """, (
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

# ✅ Cancel Registration
async def cancel(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text("❌ Registration canceled.")
    return ConversationHandler.END

# ✅ Generate and Send Student List (Admin Only)
async def send_student_list(update: Update, context: CallbackContext) -> None:
    logging.debug("Received /list command")

    if update.message.chat_id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to access the student list.")
        return

    logging.debug("Admin authorization successful")

    conn = get_db_connection()
    try:
        df = pd.read_sql("SELECT * FROM students", conn)
    except Exception as e:
        logging.error(f"Database query failed: {e}")
        await update.message.reply_text("❌ Error fetching data from the database.")
        return
    finally:
        conn.close()

    if df.empty:
        logging.debug("Database is empty, sending no students message")
        await update.message.reply_text("📂 No students registered yet.")
        return

    logging.debug(f"Fetched {len(df)} students from database")

    # 🔹 Export to Excel
    excel_file = "student_list.xlsx"
    df.to_excel(excel_file, index=False)

    # 🔹 Export to PDF
    pdf_file = "student_list.pdf"
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, "Student List", ln=True, align="C")
        pdf.ln(10)  # Line break for space

        # Column headers
        pdf.set_font("Arial", "B", 12)
        pdf.cell(50, 10, "Student ID", border=1, align="C")
        pdf.cell(60, 10, "Name", border=1, align="C")
        pdf.cell(60, 10, "Department", border=1, align="C")
        pdf.ln()

        # Table content
        pdf.set_font("Arial", size=12)
        for _, row in df.iterrows():
            pdf.cell(50, 10, row["student_id"], border=1, align="C")
            pdf.cell(60, 10, row["name"], border=1, align="C")
            pdf.cell(60, 10, row["department"], border=1, align="C")
            pdf.ln()

        pdf.output(pdf_file)
    except Exception as e:
        logging.error(f"PDF generation failed: {e}")
        await update.message.reply_text("❌ Error generating PDF.")
        return

    logging.debug("Files generated successfully")

    try:
        await context.bot.send_document(chat_id=ADMIN_ID, document=open(excel_file, "rb"), caption="📄 Student List (Excel)")
        await context.bot.send_document(chat_id=ADMIN_ID, document=open(pdf_file, "rb"), caption="📄 Student List (PDF)")
        logging.debug("Files sent successfully")
    except Exception as e:
        logging.error(f"Error sending files: {e}")
        await update.message.reply_text("❌ Error sending files.")

# ✅ Main Function - Runs the Bot
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # 🔹 Conversation Handler for Registration
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

    # 🔹 Start Bot
    app.run_polling()

if __name__ == "__main__":
    main()
