# 🎯 TrendBet - Attention Economy Trading Platform

> **Trade attention like stocks!** The world's first platform where you can long/short public figures, politicians, celebrities, and trending topics based on their real-time attention scores.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com)
[![SvelteKit](https://img.shields.io/badge/SvelteKit-Latest-orange.svg)](https://kit.svelte.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)](https://postgresql.org)

---

## 🚀 **What is TrendBet?**

TrendBet revolutionizes prediction markets by letting you **trade attention directly**. Instead of traditional stocks, you trade the public attention of politicians, celebrities, countries, games, and crypto projects.

### **Core Concept**
```
Google Trends Data → Attention Scores → Long/Short Positions → Tournament Winners
```

- **📈 Long Position**: Bet attention score will INCREASE
- **📉 Short Position**: Bet attention score will DECREASE  
- **🏆 Tournament System**: Compete with $10k virtual money per tournament
- **💰 Real Prizes**: Winners get real money from entry fees

---

## 🎮 **How It Works**

### **1. Tournament-Based Trading**
- Join tournaments with **real entry fees** ($0 for free tournaments)
- Everyone gets **$10,000 virtual money** per tournament
- Trade attention using your virtual balance
- **Highest portfolio value wins** real prize money

### **2. Attention-Based Market**
```
Target Examples:
🏛️ Politicians: Trump, Biden, AOC, DeSantis
🌟 Celebrities: Taylor Swift, Musk, Kardashians  
🌍 Countries: USA, China, Ukraine, Taiwan
🎮 Games: Fortnite, Call of Duty, Minecraft
📈 Stocks: Tesla, GameStop, Apple, NVIDIA
₿ Crypto: Bitcoin, Ethereum, Dogecoin
```

### **3. Trading Mechanics**
- **Long**: Profit when attention score increases
- **Short**: Profit when attention score decreases
- **Close**: Realize P&L and return virtual money
- **Flatten**: Close all positions instantly

### **4. Prize Structure**
- **🥇 1st Place**: 50% of prize pool
- **🥈 2nd Place**: 30% of prize pool  
- **🥉 3rd Place**: 20% of prize pool
- **💼 Platform Fee**: 10% of entry fees

---

## 🛠️ **Technical Stack**

### **Backend** (Python)
```
FastAPI + SQLAlchemy + PostgreSQL
├── Real-time Google Trends integration
├── Tournament management system
├── Long/Short position tracking
├── P&L calculation engine
├── RESTful API with WebSocket support
└── Background data workers
```

### **Frontend** (JavaScript)
```
SvelteKit + TailwindCSS + Chart.js
├── AttentionChart component for trends visualization
├── Tournament selection interface
├── Long/Short trading controls
├── Real-time portfolio tracking
├── Daily P&L display
└── Mobile-responsive design
```

### **Data Pipeline**
```
Google Trends → Attention Scores → Position Values → P&L Calculation
```

---

## 🔥 **Current Features**

### **✅ Core Trading System**
- [x] **Attention-Based Trading**: Pure attention scores, no traditional "share prices"
- [x] **Long/Short Positions**: Bet on attention going up or down
- [x] **Position Management**: Open, close, and flatten positions
- [x] **Real-time P&L**: Live profit/loss calculations
- [x] **Tournament Integration**: All trades happen within tournament context

### **✅ User Interface**
- [x] **AttentionChart Component**: Real-time trend visualization
- [x] **Browse Page**: Search and discover targets with single "Trade" button
- [x] **Trade Page**: Full trading interface with chart + controls
- [x] **Portfolio Dashboard**: Track all positions across tournaments
- [x] **Daily P&L Display**: Top navigation shows daily gains/losses

### **✅ Tournament System**  
- [x] **Multiple Tournaments**: Daily, weekly, monthly competitions
- [x] **Free Tournaments**: $0 entry for practice and testing
- [x] **Paid Tournaments**: Real entry fees with cash prizes
- [x] **Virtual Balances**: $10,000 starting balance per tournament
- [x] **Leaderboards**: Real-time ranking by portfolio value

### **✅ Data & Backend**
- [x] **Custom Google API Integration**: Live Google Trends data
- [x] **Search System**: Create tradeable targets from any search term
- [x] **Background Workers**: Automated data updates
- [x] **RESTful API**: Complete FastAPI backend
- [x] **User Authentication**: JWT-based auth system

---

## 🏗️ **Database Schema**

### **Core Models**
```sql
-- Attention targets (politicians, celebrities, etc.)
attention_targets (
  id, name, type, search_term, current_attention_score, 
  description, last_updated, is_active
)

-- User tournament entries with virtual balances
tournament_entries (
  user_id, tournament_id, entry_fee, starting_balance, 
  current_balance, final_pnl, rank, payout_amount
)

-- Long/Short positions within tournaments
portfolios (
  user_id, target_id, tournament_id, position_type, 
  attention_stakes, average_entry_score
)

-- Complete trade history with position types
trades (
  user_id, target_id, tournament_id, trade_type, position_type,
  stake_amount, attention_score_at_entry, pnl, timestamp
)

-- Tournament competitions
tournaments (
  id, name, target_type, duration, entry_fee, prize_pool,
  start_date, end_date, is_active, is_finished
)
```

---

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.9+
- Node.js 18+
- PostgreSQL 13+

### **Backend Setup**
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment
echo "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/trendbet" > .env
echo "SECRET_KEY=your-secret-key-here" >> .env

# Run server
uvicorn main:app --reload --port 8000
```

### **Frontend Setup**
```bash
cd frontend/svelte-gambling

# Install dependencies
npm install

# Run development server
npm run dev  # Starts on http://localhost:5173
```

### **First Test**
1. Go to http://localhost:5173
2. Register an account
3. Browse targets and click "Trade" 
4. Select free tournament
5. Open long/short positions
6. Watch real-time P&L updates!

---

## 🔧 **API Endpoints**

### **Trading Endpoints**
```
POST /trade                     # Open long/short positions
POST /trade/close/{target_id}   # Close specific positions
GET  /portfolio                 # User positions across tournaments
GET  /user/daily-pnl           # Today's P&L summary
GET  /user/tournament-balances  # Virtual balances per tournament
```

### **Data Endpoints**
```
GET  /targets                   # List all tradeable targets
GET  /targets/{id}/chart        # Historical attention data
POST /api/search               # Search and create new targets
GET  /api/autocomplete/{type}   # Autocomplete suggestions
```

### **Tournament Endpoints**
```
GET  /tournaments              # Active tournaments
POST /tournaments/join         # Join tournament with entry fee
GET  /leaderboard             # Platform-wide rankings
```

### **User Management**
```
POST /auth/register           # Create account  
POST /auth/login             # User authentication
GET  /auth/me               # Current user profile
```

---

## 💰 **Business Model**

### **Revenue Streams**
1. **Tournament Fees**: 10% of all entry fees
2. **Premium Tournaments**: Higher entry fees for bigger prizes

### **Tournament Economics**
```
Example $10 Entry Tournament with 100 Players:
├── Total Entry Fees: $1,000
├── Prize Pool: $900 (90%)
├── Platform Revenue: $100 (10%)
└── Prize Distribution:
    ├── 1st Place: $450 (50%)
    ├── 2nd Place: $270 (30%)
    └── 3rd Place: $180 (20%)
```

### **Scalability**
- **Global Appeal**: Every country has politicians and celebrities
- **Viral Potential**: People love trading celebrity attention
- **Low Marginal Cost**: Data from Google Trends API
- **Network Effects**: More users = bigger prizes = more users

---

## 📊 **System Architecture**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   SvelteKit     │    │    FastAPI       │    │   PostgreSQL    │
│   Frontend      │◄──►│    Backend       │◄──►│   Database      │
│                 │    │                  │    │                 │
│ • Browse Page   │    │ • Trading API    │    │ • Tournaments   │
│ • Trade Page    │    │ • Auth System    │    │ • Positions     │
│ • Portfolio     │    │ • Tournament Mgmt│    │ • Trade History │
│ • Tournaments   │    │ • Data Pipeline  │    │ • User Data     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌────────▼────────┐              │
         └──────────────►│ Google Trends   │◄─────────────┘
                        │ Data Provider   │
                        └─────────────────┘
```

---

## 🌟 **Key Differentiators**

### **vs Traditional Prediction Markets**
- ✅ **Attention-Based**: Trade real Google Trends data
- ✅ **Continuous**: Markets never close, attention changes 24/7
- ✅ **Viral Topics**: Trade whatever's trending right now
- ✅ **Global Scale**: Every country has celebrities and politicians

### **vs Stock Trading Platforms**
- ✅ **Lower Barrier**: Start with any tournament entry fee
- ✅ **Equal Playing Field**: Everyone gets same virtual starting balance
- ✅ **Social Element**: Compete against other traders directly
- ✅ **Real-time Data**: Attention changes faster than stock prices

---

## 📈 **Market Opportunity**

- **$3B+** global prediction market size
- **Zero direct competitors** in attention trading
- **Massive TAM**: Every famous person/trending topic is tradeable
- **Network Effects**: More users → bigger prizes → more users
- **Global Scalability**: Works in any country with internet
 
 ---

## 📱 **API Usage Examples**

### **Open Long Position**
```bash
curl -X POST http://localhost:8000/trade \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "target_id": 1,
    "trade_type": "buy",
    "shares": 10,
    "tournament_id": 1
  }'
```

### **Get Portfolio**
```bash
curl -X GET http://localhost:8000/portfolio \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### **Join Tournament**
```bash
curl -X POST http://localhost:8000/tournaments/join \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tournament_id": 1}'
```

---

## 🎪 **Fun Examples**

### **Political Season Trading**
```
🏛️ Election Tournament: "2024 Republican Primary"
├── Entry Fee: $25
├── Virtual Balance: $10,000
├── Duration: 30 days
└── Targets: Trump, DeSantis, Ramaswamy, Haley

Strategy: Long Trump, Short DeSantis based on debate performance
```

### **Celebrity Drama Trading**
```
🌟 Celebrity Tournament: "Hollywood Weekly"  
├── Entry Fee: $10
├── Virtual Balance: $10,000
├── Duration: 7 days
└── Targets: Taylor Swift, Kanye, Kardashians, Musk

Strategy: Short Kanye during Twitter meltdowns, Long Taylor during album drops
```

### **Crypto Hype Trading**
```
₿ Crypto Tournament: "Meme Coin Madness"
├── Entry Fee: $50  
├── Virtual Balance: $10,000
├── Duration: 3 days
└── Targets: Bitcoin, Dogecoin, Shiba Inu, Pepe

Strategy: Long whatever Elon tweets about, Short everything else
```

---

## 🔮 **Vision**

> *"In the attention economy, everything is tradeable. TrendBet makes the invisible market of public attention visible, quantifiable, and tradeable. We're not just predicting the future - we're letting you profit from the world's collective focus."*

**Built with ❤️ for traders who see opportunity in chaos.**