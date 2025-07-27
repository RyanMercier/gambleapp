# TrendBet 📈

> The world's first attention economy trading platform where users trade attention like stocks across Politicians, Billionaires, Countries, and Meme Stocks.

## 🎯 Core Concept

**TrendBet is NOT a prediction market like Polymarket.** Instead, it's an **attention trading platform** where:

- **Attention = Stock Price**: Google Trends data drives share prices up and down
- **Real Trading**: Buy and sell "attention shares" with real money
- **Portfolio Management**: Track your positions and P&L like a real trading platform  
- **Tournaments**: Compete in daily/weekly/monthly trading competitions
- **10% Platform Fee**: We take 10% of all entry fees and trading volume

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- SerpAPI key (free tier available at [serpapi.com](https://serpapi.com))

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/trendbet
cd trendbet

# Copy environment template
cp .env.example .env

# Add your SerpAPI key to .env
# SERPAPI_KEY=your_actual_key_here

# Start the platform
chmod +x scripts/start.sh
./scripts/start.sh
```

The platform will be available at:
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 📊 How It Works

### 1. Attention Data → Share Prices
```
Google Trends Score (0-100) → Real-time share price adjustments
📈 High attention = Higher price
📉 Low attention = Lower price
```

### 2. Four Trading Categories
- **🏛️ Politicians**: Trump, Biden, DeSantis, etc.
- **💰 Billionaires**: Musk, Bezos, Gates, etc.  
- **🌍 Countries**: USA, China, Japan, etc.
- **📈 Meme Stocks**: Tesla, GameStop, Bitcoin, etc.

### 3. Tournament Structure
- **⚡ Daily**: 24hr competitions ($10 entry)
- **📅 Weekly**: 7-day battles ($25 entry)
- **🗓️ Monthly**: Championship tournaments ($50 entry)

**Prize Distribution**: 50% to 1st place, 30% to 2nd, 20% to 3rd
**Platform Revenue**: 10% of all entry fees

## 🛠️ Technical Architecture

### Backend (Python)
```
FastAPI + SQLAlchemy + PostgreSQL
├── Real-time SerpAPI integration
├── Background workers for data updates  
├── Tournament management system
├── Portfolio and P&L calculations
└── RESTful API with WebSocket support
```

### Frontend (JavaScript)
```
SvelteKit + TailwindCSS + Chart.js
├── Real-time attention charts
├── Trading interface
├── Portfolio dashboard
├── Tournament leaderboards
└── Search & discovery
```

### Data Pipeline
```
SerpAPI (Google Trends) → Price Calculation → Database → Real-time Updates
```

## 🔥 Key Features

### ✅ Implemented
- [x] **Attention Trading Engine**: Buy/sell shares based on Google Trends
- [x] **Search Any Term**: Instantly create tradeable attention targets
- [x] **Real-time Charts**: Chart.js visualization of attention trends
- [x] **Portfolio Management**: Track positions, P&L, performance
- [x] **Tournament System**: Daily/weekly/monthly competitions
- [x] **SerpAPI Integration**: Live Google Trends data
- [x] **User Authentication**: JWT-based auth system
- [x] **Responsive Design**: Mobile-optimized trading interface

### 🚧 Planned Enhancements  
- [ ] **Mobile App**: React Native trading app
- [ ] **Advanced Analytics**: ML-powered attention predictions
- [ ] **Social Features**: Follow top traders, share strategies
- [ ] **API Access**: Third-party integrations
- [ ] **Crypto Payments**: Accept Bitcoin/Ethereum
- [ ] **Advanced Charts**: TradingView integration
- [ ] **News Integration**: Auto-create targets from trending news

## 🏗️ Database Schema

```sql
-- Core attention targets that can be traded
attention_targets (id, name, type, search_term, current_price, attention_score)

-- User portfolios with share positions  
portfolios (user_id, target_id, shares_owned, average_price)

-- All trading activity
trades (user_id, target_id, type, shares, price, timestamp)

-- Tournament competitions
tournaments (id, name, type, duration, entry_fee, prize_pool, start/end dates)
tournament_entries (user_id, tournament_id, entry_fee, final_pnl, rank)

-- Historical attention data for charts
attention_history (target_id, attention_score, share_price, timestamp)
```

## 📈 Business Model

### Revenue Streams
1. **Tournament Fees**: 10% of all entry fees
2. **Trading Commissions**: Small % of trade volume (future)
3. **Premium Features**: Advanced analytics, alerts (future)
4. **API Access**: Paid tiers for developers (future)

### Market Opportunity
- **$3B+** prediction market size
- **Zero direct competitors** in attention trading
- **Viral potential**: People love trading celebrity/political attention
- **Global scalability**: Every country has politicians and celebrities

## 🚀 Deployment

### Production Setup
```bash
# Build for production
docker-compose -f docker-compose.prod.yml up -d

# Set up load balancer (nginx)
# Configure SSL certificates
# Set up monitoring (Grafana + Prometheus)
# Configure database backups
```

### Environment Variables
```bash
# Required
SERPAPI_KEY=your_serpapi_key
DATABASE_URL=postgresql://user:pass@host:5432/trendbet

# Optional  
SECRET_KEY=your-jwt-secret
REDIS_URL=redis://localhost:6379
STRIPE_SECRET_KEY=sk_live_... # For payments
```

## 🧪 Development

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with hot reload
uvicorn main:app --reload --port 8000

# Run background workers
python serpapi_service.py
python tournament_management.py
```

### Frontend Development  
```bash
cd frontend/svelte-gambling
npm install
npm run dev # Starts on port 3000
```

### Database Management
```bash
# Reset database
./scripts/reset.sh

# Seed test data
./scripts/seed.sh

# View logs
docker-compose logs -f backend
```

## 🔧 API Endpoints

### Core Trading
```
POST /search              # Search any term, create tradeable target
GET  /targets             # List all attention targets  
GET  /targets/{id}/chart  # Historical price/attention data
POST /trade               # Execute buy/sell orders
GET  /portfolio           # User positions and P&L
```

### Tournaments
```
GET  /tournaments         # Active tournaments
POST /tournaments/join    # Join tournament
GET  /leaderboard         # Platform leaderboard
```

### User Management
```
POST /auth/register       # Create account
POST /auth/login          # Authenticate user
GET  /auth/me            # Get user profile
```

## 🤝 Contributing

We welcome contributions! Areas where help is needed:

1. **Frontend**: React Native mobile app
2. **Backend**: ML attention prediction models  
3. **DevOps**: Kubernetes deployment configs
4. **Design**: UI/UX improvements
5. **Data**: Additional data sources beyond Google Trends

### Development Process
```bash
# 1. Fork the repository
# 2. Create feature branch
git checkout -b feature/amazing-feature

# 3. Make changes and test
./scripts/reset.sh  # Reset for testing
npm test            # Run frontend tests
pytest              # Run backend tests

# 4. Submit pull request
```

## 📋 Roadmap

### Q1 2024: Core Platform
- [x] MVP attention trading engine
- [x] Tournament system  
- [x] Mobile-responsive design
- [ ] Beta launch with 100 users

### Q2 2024: Growth Features  
- [ ] Mobile app launch
- [ ] Advanced charting with TradingView
- [ ] Social trading features
- [ ] Crypto payment integration

### Q3 2024: Scale & Monetization
- [ ] API marketplace launch
- [ ] Premium analytics features  
- [ ] International expansion
- [ ] Series A fundraising

### Q4 2024: Advanced Features
- [ ] ML attention predictions
- [ ] Options/derivatives trading
- [ ] White-label platform for other markets
- [ ] IPO preparation

## 📞 Contact & Support

- **Website**: https://trendbet.io
- **Email**: hello@trendbet.io  
- **Discord**: https://discord.gg/trendbet
- **Twitter**: [@TrendBetHQ](https://twitter.com/trendbethq)

## 📄 License

Private

---

**TrendBet** - *Where Attention Becomes Currency* 📈✨

*Built with FastAPI, SvelteKit, and a deep understanding of the attention economy.*