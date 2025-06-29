# Family Task Manager Bot

Gestisci le task familiari in modo moderno, robusto e collaborativo direttamente su Telegram!

## 🚀 Funzionalità principali
- **Menu interattivo** con emoji e navigazione a due livelli (categorie → task)
- **Assegnazione e completamento task** con persistenza su PostgreSQL Railway
- **Leaderboard** e **statistiche** sempre aggiornate
- **Gestione membri** automatica (aggiunta su ogni messaggio)
- **Storico task completate** e riassegnazione task già svolte
- **UI moderna**: pulsanti, callback, feedback visivi
- **Logging** dettagliato per debugging e monitoring
- **Pronto per deploy cloud** (Railway, Heroku, ecc.)

## 🛠️ Setup rapido
1. **Clona il repository**
2. Crea un bot Telegram e ottieni il token
3. Crea un database PostgreSQL (es. Railway) e imposta la variabile `DATABASE_URL`
4. Esporta le variabili d'ambiente:
   ```bash
   export TELEGRAM_TOKEN=il_tuo_token
   export DATABASE_URL=postgresql://user:pass@host/db
   ```
5. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
6. Avvia il bot:
   ```bash
   python main.py
   ```

## 📋 Comandi principali
- `/start` — Mostra il menu principale
- `/tasks` — Elenco task per categoria
- `/mytasks` — Le tue task assegnate
- `/leaderboard` — Classifica famiglia
- `/stats` — Le tue statistiche
- `/help` — Aiuto e info

## 🗄️ Struttura database
- **tasks**: elenco task disponibili
- **assigned_tasks**: task attualmente assegnate
- **completed_tasks**: storico task completate (per punti/statistiche)
- **families, family_members**: gestione gruppi e membri

## 🧑‍💻 Sviluppo e test
- Tutto il codice è modularizzato (`main.py`, `bot_handlers.py`, `db.py`)
- Test automatici: `test_assignment.py`, `test_bot.py`, ecc.
- Schema SQL in `schema.sql`

## 🏆 Best practice
- Task completate vengono storicizzate e poi riassegnabili
- Statistiche e leaderboard calcolate solo su task realmente completate
- UI sempre funzionante, anche in caso di errori

## 📦 Deploy su Railway
- Imposta le variabili d'ambiente su Railway
- Usa il `Procfile` per avvio automatico

## 📄 Licenza
MIT

---

**Family Task Manager Bot** — Progetto open source per la gestione smart delle attività familiari su Telegram.
