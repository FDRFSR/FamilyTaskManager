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
        print("=" * 60)
        print("🚨 CONFIGURAZIONE MANCANTE")
        print("=" * 60)
        print()
        print("❌ TELEGRAM_TOKEN non impostato nelle variabili d'ambiente!")
        print()
        print("🔧 Per configurare il bot:")
        print("1. Crea un bot Telegram con @BotFather")
        print("2. Ottieni il token del bot")
        print("3. Imposta la variabile d'ambiente:")
        print("   export TELEGRAM_TOKEN=il_tuo_token_qui")
        print()
        print("💡 Il bot può funzionare in modalità demo senza DATABASE_URL,")
        print("   ma TELEGRAM_TOKEN è essenziale per comunicare con Telegram.")
        print()
        print("📖 Consulta il README.md per istruzioni complete.")
        print("=" * 60)
        sys.exit(1)

    try:
        db = FamilyTaskDB()
        if db.fallback_mode:
            print("=" * 60)
            print("⚠️  MODALITÀ FALLBACK ATTIVATA")
            print("=" * 60)
            print()
            print("🔶 DATABASE_URL non configurato - usando modalità demo")
            print()
            print("✅ Funzionalità disponibili:")
            print("• ✅ Interfaccia utente completa")
            print("• ✅ Assegnazione task temporanea")
            print("• ✅ Gestione membri di base")
            print("• ✅ Menu e bottoni funzionanti")
            print()
            print("❌ Funzionalità limitate:")
            print("• ❌ Dati non persistenti (reset al riavvio)")
            print("• ❌ Statistiche e classifica limitate")
            print("• ❌ Storia completamenti non salvata")
            print()
            print("🔧 Per funzionalità complete, configura DATABASE_URL:")
            print("   export DATABASE_URL=postgresql://user:pass@host/db")
            print()
            print("=" * 60)
    except Exception as e:
        logger.critical(f"Errore critico nell'inizializzazione del database: {e}")
        print(f"❌ Errore nell'inizializzazione: {e}")
        sys.exit(1)

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

    if db.fallback_mode:
        logger.warning("Bot avviato in MODALITÀ FALLBACK (senza database persistente)")
    else:
        logger.info("Bot avviato con database completo")
    
    logger.info("Bot Family Task Manager in ascolto...")
    application.run_polling()
