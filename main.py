import os
import sys
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, JobQueue
import asyncio
from bot_handlers import FamilyTaskBot
from db import FamilyTaskDB
from utils import delete_old_messages, setup_enhanced_logging

# Setup enhanced logging
setup_enhanced_logging()
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
    if not TELEGRAM_TOKEN:
        logger.critical("TELEGRAM_TOKEN non impostato nelle variabili d'ambiente! Impossibile avviare il bot.")
        sys.exit(1)

    db = FamilyTaskDB()
    bot = FamilyTaskBot()
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_command))
    application.add_handler(CommandHandler("leaderboard", bot.leaderboard))
    application.add_handler(CommandHandler("stats", bot.stats))
    application.add_handler(CommandHandler("tasks", bot.show_tasks))
    application.add_handler(CommandHandler("mytasks", bot.my_tasks))
    application.add_handler(CallbackQueryHandler(bot.button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message))

    # Job per cancellare i messaggi ogni 15 minuti
    job_queue = application.job_queue
    job_queue.run_repeating(delete_old_messages, interval=900, first=900)

    logger.info("Bot Family Task Manager avviato. In ascolto...")
    application.run_polling()
