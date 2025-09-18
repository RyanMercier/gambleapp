# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TrendBet is an attention economy trading platform that allows users to trade the attention scores of public figures, politicians, celebrities, and trending topics using Google Trends data. The platform operates on a tournament-based system with virtual money and real prizes.

## Architecture

**Backend**: Python FastAPI application with PostgreSQL database
- SQLAlchemy ORM for database operations
- JWT authentication system
- Google Trends API integration for real-time attention data
- Background workers for data updates
- WebSocket support for real-time updates

**Frontend**: SvelteKit application with TypeScript
- TailwindCSS for styling
- Chart.js for data visualization
- Component-based architecture

## Development Commands

### Backend Setup & Running
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment file (.env)
echo "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/trendbet" > .env
echo "SECRET_KEY=your-secret-key-here" >> .env

# Initialize/reset database
python database.py reset  # Full reset with schema recreation
python reset_db.py        # Simple data reset

# Run development server
uvicorn main:app --reload --port 8000

# Run background data updater
python background_updater.py

# Test system functionality
python test.py         # Test everything
python test.py db      # Test database only
python test.py trends  # Test Google Trends API only
```

### Frontend Setup & Running
```bash
cd frontend/svelte-gambling

# Install dependencies
npm install

# Run development server
npm run dev  # Starts on http://localhost:5173

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run check
```

## Core Data Models

**Attention-Based Trading System**:
- `AttentionTarget`: Politicians, celebrities, countries, games, stocks, crypto with Google Trends search terms
- `Tournament`: Time-limited competitions with entry fees and prize pools
- `TournamentEntry`: User participation in tournaments with virtual balances
- `Portfolio`: Long/short positions within tournaments using "attention stakes"
- `Trade`: Complete trade history with position types (long/short)

**Key Concepts**:
- **Attention Stakes**: Virtual currency representing betting amount on attention changes
- **Position Types**: Long (bet attention increases) or Short (bet attention decreases)
- **Tournament Context**: All trading happens within tournaments with virtual starting balances ($10,000)
- **Normalized Scoring**: All scores displayed to users are normalized for consistency across timeframes

## TrendBet Scoring System

**Problem Solved**: Google Trends scores are relative within each timeframe (0-100), making comparisons across timeframes impossible. A score of "50" on daily vs weekly charts represents completely different attention levels.

**Our Solution - 7-Day Baseline Normalization**:

### How It Works
1. **Baseline Calculation**: When a new target is created, we immediately fetch both 1-day and 7-day Google Trends data
2. **Reference Point**: The 7-day average becomes our "normalization baseline" for that target
3. **Score Normalization**: All timeframe data is normalized relative to this 7-day baseline using the formula:
   ```
   normalized_score = raw_google_score × (baseline_average / timeframe_peak)
   ```
4. **Consistent Display**: Users only see normalized scores, ensuring consistency across all timeframes

### Example
```
Raw Google Trends Data:
- 7-day average: 40 (becomes our baseline)
- Daily peak: 100, Daily score: 80
- Weekly peak: 60, Weekly score: 30

Normalized Display:
- Daily score: 80 × (40/100) = 32
- Weekly score: 30 × (40/60) = 20

Now scores are directly comparable!
```

### Benefits
- **Position Markers Work**: Entry points show correctly across all chart timeframes
- **Consistent Trading**: Score "50" means the same attention level on any timeframe
- **Meaningful Comparisons**: Users can compare different time periods meaningfully
- **Real-time Accuracy**: New WebSocket data is automatically normalized

### Database Schema
- `attention_history.normalized_score`: User-facing normalized score
- `attention_history.attention_score`: Raw Google Trends score (stored for debugging)
- `attention_targets.normalization_baseline`: 7-day average used for normalization
- `attention_targets.baseline_calculated_at`: When baseline was last calculated

### Maintenance
- **Monthly Re-normalization**: Baselines are recalculated monthly to account for long-term trend changes
- **Manual Trigger**: Admin endpoint `/admin/recalculate-baselines` for manual recalculation
- **Automatic**: New targets get immediate 1d + 7d data loading and baseline calculation

## API Architecture

**Authentication**: JWT-based with `get_current_user` dependency
**Core Endpoints**:
- `/trade` - Open long/short positions with attention stakes
- `/trade/close/{target_id}` - Close positions and realize P&L
- `/portfolio` - User positions across all tournaments
- `/tournaments` - Active tournaments and joining
- `/targets` - Tradeable attention targets
- `/api/search` - Search and create new targets

## Development Workflow

1. **Database Changes**: Modify `models.py`, then run `python database.py reset`
2. **New Features**: Follow tournament-centric design - all user actions happen within tournament context
3. **Testing**: Use `python test.py` to verify database and Google Trends connectivity
4. **Data Updates**: Background worker in `background_updater.py` handles attention score updates

## Key Files

**Backend**:
- `main.py` - FastAPI application and all API endpoints
- `models.py` - SQLAlchemy database models
- `auth.py` - JWT authentication system
- `google_trends_service.py` - Google Trends API integration
- `database.py` - Database setup and utilities
- `background_updater.py` - Automated data updates

**Frontend**:
- `src/lib/AttentionChart.svelte` - Chart.js integration for trend visualization
- `src/lib/TradingWidget.svelte` - Main trading interface component
- `src/lib/api.js` - Backend API communication
- `src/lib/stores.js` - Svelte stores for state management

## Important Notes

- **Tournament-First Design**: All user interactions happen within tournament contexts
- **Virtual Money**: Users trade with virtual tournament balances, not real money in positions
- **Attention Scores**: Core trading metric from Google Trends (0-100), no traditional "share prices"
- **Position Types**: Long/Short betting on attention score increases/decreases
- **Real-time Updates**: WebSocket connections for live P&L and leaderboard updates