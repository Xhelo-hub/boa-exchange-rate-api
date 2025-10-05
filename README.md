data.# Bank of Albania Exchange Rate API

A Python API that scrapes exchange rates from the Bank of Albania website and synchronizes them with QuickBooks Online based on transaction dates.

## Features

- **Exchange Rate Scraping**: Automatically retrieves daily exchange rates from Bank of Albania
- **QuickBooks Online Integration**: Posts exchange rates to QuickBooks Online
- **Date-based Synchronization**: Updates rates based on transaction dates
- **REST API**: FastAPI-based web service for easy integration
- **Scheduled Updates**: Automatic daily rate updates
- **Error Handling**: Comprehensive error handling and logging

## Project Structure

```
boa-exchange-rate-api/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── boa_scraper/           # Bank of Albania scraper module
│   │   ├── __init__.py
│   │   ├── scraper.py         # Main scraping logic
│   │   └── models.py          # Data models for exchange rates
│   ├── quickbooks/            # QuickBooks Online integration
│   │   ├── __init__.py
│   │   ├── client.py          # QB Online API client
│   │   └── sync.py            # Synchronization logic
│   ├── api/                   # FastAPI routes and endpoints
│   │   ├── __init__.py
│   │   ├── routes.py          # API endpoints
│   │   └── schemas.py         # Pydantic models
│   └── utils/                 # Utility functions
│       ├── __init__.py
│       ├── logger.py          # Logging configuration
│       └── scheduler.py       # Task scheduling
├── config/
│   ├── settings.py            # Application settings
│   └── .env.example           # Environment variables template
├── tests/                     # Test suite
│   ├── __init__.py
│   ├── test_scraper.py
│   ├── test_quickbooks.py
│   └── test_api.py
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd boa-exchange-rate-api
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # For development
   ```

4. **Configure environment variables:**
   ```bash
   cp config/.env.example config/.env
   # Edit config/.env with your settings
   ```

## Configuration

Create a `.env` file in the `config/` directory with the following variables:

```env
# QuickBooks Online API Credentials
QB_CLIENT_ID=your_quickbooks_client_id
QB_CLIENT_SECRET=your_quickbooks_client_secret
QB_ACCESS_TOKEN=your_access_token
QB_REFRESH_TOKEN=your_refresh_token
QB_COMPANY_ID=your_company_id
QB_SANDBOX=true  # Set to false for production

# Application Settings
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
SCHEDULE_TIME=09:00  # Daily update time (24h format)

# Bank of Albania Settings
BOA_BASE_URL=https://www.bankofalbania.org
BOA_TIMEOUT=30
```

## Usage

### Running the API Server

```bash
# Development server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Production server
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### API Endpoints

- **GET `/health`** - Health check endpoint
- **GET `/rates`** - Get current exchange rates
- **GET `/rates/{date}`** - Get exchange rates for a specific date
- **POST `/sync`** - Manually trigger QuickBooks synchronization
- **GET `/sync/status`** - Get synchronization status

### Example API Usage

```python
import requests

# Get current exchange rates
response = requests.get("http://localhost:8000/rates")
rates = response.json()

# Get rates for specific date
response = requests.get("http://localhost:8000/rates/2023-10-05")
rates = response.json()

# Trigger manual sync
response = requests.post("http://localhost:8000/sync")
sync_result = response.json()
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test file
pytest tests/test_scraper.py -v
```

### Code Quality

```bash
# Format code
black src/ tests/

# Check code style
flake8 src/ tests/

# Type checking
mypy src/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

## Deployment

### Docker (Optional)

```dockerfile
# Create Dockerfile for containerized deployment
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY config/ ./config/

EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Production Considerations

- Set up proper logging and monitoring
- Configure HTTPS with SSL certificates
- Set up database for persistent storage (optional)
- Configure proper backup and disaster recovery
- Set up health checks and alerting

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue on GitHub or contact the development team.

## Changelog

### v0.1.0
- Initial project setup
- Bank of Albania scraper implementation
- QuickBooks Online integration
- FastAPI REST API
- Automated scheduling
- Basic test suite