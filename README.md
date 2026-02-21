# 🍕 FreeFood UCD

**Never miss free food on campus again.**

FreeFood UCD automatically monitors UCD society Instagram accounts for free food announcements and sends instant notifications via WhatsApp or email.

---

## 🎯 What It Does

- **Monitors** Instagram posts and stories from UCD societies
- **Detects** free food mentions using NLP
- **Extracts** event details (time, location, society)
- **Notifies** students instantly via WhatsApp or email
- **Displays** upcoming events in a clean, mobile-first interface

---

## 🏗️ Architecture

```
Frontend (Next.js) → API (FastAPI) → Database (PostgreSQL)
                                   ↓
                          Scraper Service (Playwright)
                                   ↓
                          Event Processor (NLP)
                                   ↓
                          Notification Service (Twilio/SendGrid)
```

**Key Features:**
- Microservice architecture for fault tolerance
- Event-driven processing with message queues
- Async scraping with anti-detection measures
- Real-time notifications with delivery tracking
- Mobile-first, minimal UI design

---

## 📚 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and technical architecture
- **[FRONTEND_DESIGN_SPEC.md](FRONTEND_DESIGN_SPEC.md)** - UI/UX design system and components
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Step-by-step development guide

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose

### Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/freefood-ucd.git
cd freefood-ucd

# Start services with Docker
docker-compose up -d

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Visit:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern async Python web framework
- **PostgreSQL** - Primary database
- **Redis** - Caching and message queue
- **Celery** - Background task processing
- **SQLAlchemy** - ORM with async support

### Scraping
- **Playwright** - Headless browser automation
- **Python** - Scraping logic and NLP

### Frontend
- **Next.js 14** - React framework with App Router
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Accessible component library
- **Zustand** - State management
- **React Query** - Data fetching

### Notifications
- **Twilio** - WhatsApp Business API
- **SendGrid** - Email delivery

### Infrastructure
- **Docker** - Containerization
- **Docker Compose** - Local orchestration
- **Prometheus** - Metrics collection
- **Grafana** - Monitoring dashboards

---

## 📱 Features

### For Students
- ✅ Real-time free food alerts
- ✅ Filter by society or date
- ✅ WhatsApp and email notifications
- ✅ Mobile-optimized interface
- ✅ No app installation required

### For Societies
- ✅ Automatic detection from Instagram
- ✅ No extra work required
- ✅ Increased event attendance
- ✅ Better student engagement

---

## 🎨 Design Philosophy

**Inspiration:** Notion, Splitwise, Monzo

**Principles:**
- Clean and minimal
- Fast and responsive
- Mobile-first
- Utility-focused (not social media styled)
- Professional appearance

**Visual Style:**
- Light grey background (#f9fafb)
- White cards with subtle shadows
- Green accent for "Free Food" badges
- Clear typography hierarchy
- Generous spacing

---

## 🔐 Privacy & Security

- **No personal data selling** - Your information stays private
- **Opt-in notifications** - You control what you receive
- **Easy unsubscribe** - One-click opt-out
- **GDPR compliant** - Right to deletion and data export
- **Secure authentication** - JWT tokens with refresh rotation
- **Rate limiting** - Protection against abuse

---

## 📊 Project Status

### Phase 1: MVP (Current)
- [x] Architecture design
- [x] Frontend design system
- [x] Implementation guide
- [ ] Backend API
- [ ] Instagram scraper
- [ ] NLP extraction
- [ ] Notification system
- [ ] Frontend implementation

### Phase 2: UCD Rollout
- [ ] Beta testing with 50 users
- [ ] Monitor all UCD societies
- [ ] Optimize scraping reliability
- [ ] Public launch

### Phase 3: Expansion
- [ ] Other Irish universities
- [ ] UK campuses
- [ ] Advanced filtering
- [ ] Calendar integration

---

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- **Python:** Follow PEP 8, use Black formatter
- **TypeScript:** Follow Airbnb style guide, use Prettier
- **Commits:** Use conventional commits format

---

## 🐛 Known Issues & Limitations

### Instagram Scraping
- **Fragile:** Instagram changes can break scraping
- **Rate limits:** Must respect Instagram's limits
- **Detection risk:** Aggressive scraping may trigger blocks
- **Stories:** 24-hour lifespan, may miss some

### Mitigation Strategies
- Separate microservice for scraper (isolated failures)
- Slow, human-like scraping patterns
- Rotating user agents and delays
- Circuit breakers and retry logic
- Comprehensive monitoring and alerts

---

## 📈 Metrics & Monitoring

### Key Metrics
- Scraping success rate (target: >95%)
- Event detection accuracy (target: >80%)
- Notification delivery time (target: <2 min)
- False positive rate (target: <10%)
- System uptime (target: >99%)

### Monitoring Tools
- Prometheus for metrics collection
- Grafana for visualization
- Sentry for error tracking
- Custom health checks

---

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e

# Load tests
locust -f tests/load_test.py
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

Built with ❤️ by students, for students.

**Maintainer:** [Your Name]

---

## 🙏 Acknowledgments

- UCD societies for making campus life better
- Open source community for amazing tools
- Beta testers for valuable feedback

---

## 📞 Contact

- **Email:** hello@freefooducd.ie
- **Instagram:** @freefooducd
- **Issues:** [GitHub Issues](https://github.com/yourusername/freefood-ucd/issues)

---

## ⚠️ Disclaimer

This project is not affiliated with or endorsed by University College Dublin or Instagram. It is an independent student project designed to help students discover free food events on campus.

Use of this service is subject to Instagram's Terms of Service. We recommend using a dedicated monitoring account and respecting rate limits to avoid account restrictions.

---

**Made with 🍕 in Dublin**