# TrendBet 📈

> The world's first attention economy trading platform where users bet on what (or who) will capture public attention.

## Table of Contents

- [Overview](#overview)
- [Market Validation](#market-validation)
- [Core Concept](#core-concept)
- [Technical Stack](#technical-stack)
- [Features](#features)
- [Architecture](#architecture)
- [Data Sources](#data-sources)
- [Game Mechanics](#game-mechanics)
- [Development Timeline](#development-timeline)
- [Scaling Strategy](#scaling-strategy)
- [Getting Started](#getting-started)
- [Contributing](#contributing)
- [License](#license)

## Overview

TrendBet is a revolutionary platform that gamifies the attention economy. Instead of traditional trading or prediction markets, users trade on **popularity and social influence** across four main categories:

- 🏛️ **Politicians** - Popularity trends + actual stock portfolio performance
- 💰 **Billionaires** - Social media mentions and news coverage
- 🌍 **Countries** - Tourism interest and trending news
- 📈 **Stocks** - Social sentiment and meme potential (not price prediction)

## Market Validation

✅ **Zero Direct Competitors** - Extensive research found no platforms offering attention/popularity trading  
✅ **Proven Market Demand** - $3B+ political betting market, millions using politician tracking sites  
✅ **Multiple Revenue Streams** - Tournament fees, premium features, sponsored events  
✅ **Built-in Virality** - People naturally share predictions about celebrities and politics  
✅ **Global Scalability** - Every country has politicians, celebrities, and tourism  

## Core Concept

### The Attention Economy Trade

Users purchase "shares" in public figures, countries, or trending topics based on predicted attention metrics:

- **Real-time scoring** based on Google Trends + social media mentions
- **Dynamic pricing** that fluctuates with actual attention data
- **Tournament competitions** with cash prizes
- **Cross-category events** (e.g., "Space Race Week" - Musk vs SpaceX vs USA vs NASA)
- **Social trading** features (follow top predictors, copy strategies)

### Why This Works

1. **Always-on engagement** - News cycles, celebrity drama, political events happen 24/7
2. **Network effects** - More players = more interesting predictions and social dynamics
3. **Educational value** - Teaches users about media cycles, public attention, and influence
4. **Cultural relevance** - Taps into existing celebrity and political obsessions

## Technical Stack

### Backend (Python)
- **FastAPI** - Async web framework with auto-generated docs
- **python-socketio** - Real-time chat and live updates
- **PostgreSQL** - Robust database for financial/user data
- **SQLAlchemy + Alembic** - ORM and database migrations
- **Redis** - Caching, sessions, pub/sub for scaling
- **Celery** - Background tasks for data fetching
- **Stripe** - Payment processing for tournaments

### Frontend (JavaScript)
- **SvelteKit** - Reactive framework with great performance
- **TailwindCSS** - Utility-first CSS for rapid UI development
- **Socket.IO Client** - Real-time connection to Python backend
- **Chart.js** - Interactive charts for trending data

### Infrastructure
- **Docker** - Containerization for consistent deployments
- **Redis Pub/Sub** - Cross-server communication for scaling
- **Background Workers** - Scheduled data fetching and processing

## Features

### Core MVP Features
- **Real-time popularity scoring** for politicians using Google Trends + social data
- **Multi-room chat system** (global, category-specific, tournament-specific)
- **Tournament system** with daily, weekly, and monthly competitions
- **User portfolios** and leaderboards
- **Stripe integration** for tournament entry fees
- **Background data pipeline** updating every 5-60 minutes

### Advanced Features (Post-MVP)
- **Cross-category tournaments** and events
- **Social trading** (follow successful predictors)
- **Premium analytics** and alerts
- **Mobile app** with push notifications
- **Crypto payments** and NFT rewards
- **API access** for power users

## Architecture

### Database Schema
```sql
-- Core entities
users (id, username, email, balance, created_at)
politicians (id, name, trend_score, last_updated)
tournaments (id, name, entry_fee, prize_pool, start_date, end_date)
predictions (id, user_id, target_id, target_type, amount, timestamp)

-- Chat system  
chat_rooms (id, name, type, created_at)
messages (id, room_id, user_id, content, message_type, created_at)
user_presence (user_id, room_name, last_seen, is_online)
```

### Real-time Architecture
```python
# Multi-room Socket.IO setup
CHAT_ROOMS = {
    'global': 'Global Chat',
    'politicians': 'Politicians Discussion', 
    'countries': 'Countries & Tourism',
    'billionaires': 'Billionaires & Business',
    'stocks': 'Trending Stocks',
    'tournament_{id}': 'Tournament Specific'
}
```

## Data Sources

### Primary APIs
- **SerpApi** - Google Trends data (reliable alternative to deprecated pytrends)
- **Quiver Quantitative API** - Politician stock trades and portfolio tracking
- **Mention API / Keyhole API** - Social media mentions and sentiment analysis
- **Financial APIs** - Stock data and billionaire net worth tracking

### Data Pipeline
```python
# Background tasks (Celery)
@celery_app.task
async def fetch_politician_trends():
    """Updates politician popularity scores every 5 minutes"""
    
@celery_app.task  
async def fetch_social_mentions():
    """Updates billionaire and stock mention counts every 15 minutes"""
    
@celery_app.task
async def calculate_tournament_results():
    """Processes tournament outcomes and payouts"""
```

## Game Mechanics

### Scoring Algorithm
```python
def calculate_attention_score(google_trends, social_mentions, news_articles):
    """
    Weighted scoring system:
    - Google Trends: 40%
    - Social Media Mentions: 35% 
    - News Article Frequency: 25%
    """
    base_score = (trends * 0.4) + (mentions * 0.35) + (news * 0.25)
    momentum_multiplier = calculate_momentum(historical_data)
    return base_score * momentum_multiplier
```

### Tournament Types
- **Lightning Rounds** - 1-4 hour competitions during major events
- **Daily Battles** - 24-hour tournaments with modest entry fees ($1-5)
- **Weekly Championships** - 7-day tournaments with larger prizes ($10-25 entry)
- **Monthly Majors** - Month-long competitions with significant prize pools ($50-100 entry)
- **Special Events** - Custom tournaments during elections, award shows, major news

### Cross-Category Events
- **Space Race Week** - Elon Musk vs SpaceX stock vs USA country score vs NASA politicians
- **World Cup Fever** - Country tourism vs sports stocks vs athlete mentions
- **Economic Crisis** - Fed Chair vs Warren Buffett vs banking stocks vs USA economy score

## Development Timeline

### Week 1: Backend Foundation
- FastAPI project setup with Socket.IO
- PostgreSQL database and SQLAlchemy models
- User authentication (JWT)
- Basic API endpoints
- SerpApi integration for Google Trends
- Multi-room chat system

### Week 2: Real-time Features
- Socket.IO event handlers for live updates
- Background Celery tasks for data fetching
- Tournament creation and management system
- Real-time popularity score calculations
- Chat message history and presence tracking

### Week 3: Frontend & Integration
- SvelteKit application with Socket.IO client
- Real-time UI updates and live charts
- Tournament participation interface
- Stripe payment integration
- User dashboard and portfolios
- Deployment and initial testing

### Week 4+: Polish & Launch
- Performance optimization
- Error handling and monitoring
- User onboarding flow
- Mobile responsiveness
- Beta testing and feedback
- Public launch preparation

## Scaling Strategy

### Phase 1: MVP (0-1K users)
- Single FastAPI server
- PostgreSQL + Redis on same server
- Simple Socket.IO rooms
- Basic tournament system

### Phase 2: Growth (1K-10K users)
- Load balancer with multiple FastAPI instances
- Redis pub/sub for cross-server Socket.IO
- Dedicated Celery workers
- Database connection pooling
- CDN for static assets

### Phase 3: Scale (10K-100K users)
- Microservices architecture (separate chat service)
- Message queues (RabbitMQ/Kafka)
- Database read replicas
- Caching layers (Redis + CDN)
- Geographic distribution

### Phase 4: Enterprise (100K+ users)
- Auto-scaling infrastructure
- Advanced analytics and ML predictions
- Mobile apps (React Native/Flutter)
- API marketplace for third-party developers
- International expansion

## Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Node.js 18+ (for frontend)

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/trendbet
cd trendbet

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Database setup
createdb trendbet
alembic upgrade head

# Frontend setup  
cd ../frontend
npm install

# Environment variables
cp .env.example .env
# Edit .env with your API keys and database credentials
```

### Development

```bash
# Start backend (from backend directory)
uvicorn main:app --reload --port 8000

# Start Celery worker (separate terminal)
celery -A celery_app worker --loglevel=info

# Start Celery beat scheduler (separate terminal)  
celery -A celery_app beat --loglevel=info

# Start frontend (from frontend directory)
npm run dev
```

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost/trendbet
REDIS_URL=redis://localhost:6379

# APIs
SERPAPI_KEY=your_serpapi_key
QUIVER_API_KEY=your_quiver_api_key
MENTION_API_KEY=your_mention_api_key

# Payments
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_webhook_secret

# Security
SECRET_KEY=your_jwt_secret_key
```

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Process
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Contact

**Project Creator**: [Your Name]  
**Email**: your.email@example.com  
**Twitter**: [@yourusername](https://twitter.com/yourusername)

**Project Link**: [https://github.com/yourusername/trendbet](https://github.com/yourusername/trendbet)

---

*TrendBet - Where attention becomes currency* 📈✨