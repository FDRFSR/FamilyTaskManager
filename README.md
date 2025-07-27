# Family Task Manager Bot

Manage your family chores in a modern, robust, and collaborative way directly on Telegram!

## 🚀 Main Features
- **Interactive menu** with emoji and two-level navigation (categories → tasks)
- **⚡ NUOVO: Immediate task completion** - Tasks are auto-assigned and completed in one step
- **📊 NUOVO: Monthly statistics tracking** - Track your progress month by month
- **🎨 NUOVO: Enhanced statistics display** - Beautiful visual charts and progress bars
- **Leaderboard** and **statistics** always up-to-date
- **Automatic member management** (auto-add on every message)
- **Completed task history** and re-assignable tasks
- **Modern UI**: buttons, callbacks, visual feedback
- **Automatic deletion of all bot messages** (text, callbacks, errors, etc.) every 15 minutes for privacy and chat cleanliness
- **Detailed logging** for debugging and monitoring
- **Cloud-ready deploy** (Railway, Heroku, etc.)

## 🛠️ Quick Setup
1. **Clone the repository**
2. Create a Telegram bot and get the token
3. Create a PostgreSQL database (e.g. Railway) and set the `DATABASE_URL` variable
4. Export environment variables:
   ```bash
   export TELEGRAM_TOKEN=your_token
   export DATABASE_URL=postgresql://user:pass@host/db
   ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
6. Start the bot:
   ```bash
   python main.py
   ```

## 📋 Main Commands
- `/start` — Show the main menu
- `/tasks` — List tasks by category
- `/mytasks` — Your assigned tasks
- `/leaderboard` — Family leaderboard
- `/stats` — Your statistics
- `/help` — Help and info

## ⚡ New Immediate Completion Workflow

The bot now features a streamlined workflow for completing tasks:

1. **Browse Categories**: Choose from organized task categories
2. **Select Task**: Pick any task you want to complete  
3. **Instant Assignment**: Task is automatically assigned to you
4. **Immediate Completion**: Confirm completion and earn points instantly
5. **Track Progress**: View monthly statistics and progress charts

### Key Changes:
- ❌ **Removed**: Separate assignment step
- ✅ **Added**: One-click task completion
- ✅ **Added**: Monthly progress tracking  
- ✅ **Added**: Enhanced visual statistics
- ✅ **Added**: Monthly achievement charts

## 📊 Enhanced Statistics Features

### Monthly Tracking
- **Monthly Progress Charts**: Visual representation of your year-long journey
- **Current Month Stats**: See your progress for the current month
- **Historical Data**: All monthly achievements are preserved
- **Visual Progress Bars**: Beautiful progress indicators

### Enhanced Display
- **Performance Badges**: Earn badges based on completion count
- **Top Tasks List**: See your most completed tasks with rankings
- **Level Progress**: Visual progress bars for level advancement
- **Monthly Achievements**: Track monthly point and task completion goals

## 🗄️ Database Structure
- **tasks**: available tasks
- **assigned_tasks**: currently assigned tasks (legacy support)
- **completed_tasks**: completed task history (for points/statistics)
- **families, family_members**: group and member management
- **📊 NUOVO: monthly_stats**: monthly progress tracking for enhanced statistics

## 🧑‍💻 Development & Testing
- All code is modularized (`main.py`, `bot_handlers.py`, `db.py`)
- Automated tests: `test_assignment.py`, `test_bot.py`, etc.
- SQL schema in `schema.sql`

## 🏆 Best Practices
- **⚡ NUOVO: Immediate completion workflow** - Tasks are automatically assigned to the user who selects them and completed immediately
- **📊 Monthly statistics tracking** - Progress is tracked monthly with visual charts
- **🎨 Enhanced UI** - Beautiful statistics display with progress bars and monthly charts
- Completed tasks are archived and then re-assignable
- Statistics and leaderboard are calculated only on actually completed tasks  
- UI always works, even in case of errors

## 📦 Deploy on Railway
- Set environment variables on Railway
- Use the `Procfile` for automatic startup

## 📝 Default Tasks
The following tasks are automatically available after a database reset:

- Pulizia cucina
- Pulizia bagno
- Portare fuori la spazzatura
- Fare il bucato
- Cura del giardino
- Fare la spesa
- Preparare la cena
- Riordinare la camera
- Dare da mangiare agli animali
- Lavare l'auto
- Caricare lavastoviglie
- Stendere il bucato
- Passare l’aspirapolvere
- Svuotare la lavastoviglie
- Riordinare il soggiorno
- Buttare la carta/vetro/plastica
- Fare i letti
- Preparare la tavola
- Sparecchiare la tavola
- Pulire la lettiera del gatto
- Pulire il garage
- Pulire le finestre
- Organizzare gli armadi
- Pulire il frigorifero
- Innaffiare le piante
- Pulire gli specchi
- Cambiare le lenzuola
- Pulire il forno
- Raccogliere le foglie
- Pulire il balcone
- Organizzare la cantina
- Pulire le scarpe
- Spolverare i mobili
- Pulire gli elettrodomestici
- Riordinare la scrivania
- Pulire i tappeti
- Organizzare il garage
- Pulire le scale
- Cambiare i filtri dell'aria
- Pulire i ventilatori
- Organizzare la dispensa

You can customize these by editing the `default_tasks` list in `db.py`.

## 🛠️ Customizing Tasks
To add or modify default tasks, edit the `default_tasks` list in the `_load_tasks_from_db` method of `db.py`. Each task has:
- `id`: unique string (e.g. "cucina_pulizia")
- `name`: display name
- `points`: points awarded
- `time_minutes`: estimated time

## 🧹 Automatic Message Deletion
All messages sent by the bot (including text, callback responses, error messages, etc.) are automatically deleted every 15 minutes to keep the chat clean and protect privacy. This feature is enabled by default and works for all message types generated by the bot.

## 📄 License
MIT

---

**Family Task Manager Bot** — Open source project for smart family task management on Telegram.
