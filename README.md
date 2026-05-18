# AURUMFx AI Trading System

AURUMFx AI Trading System is a Python-based AI trading assistant designed for forex and gold market analysis. The project includes market data handling, AI/ML prediction, trading signal generation, risk management, paper trading, backtesting, and a Streamlit dashboard.

## Features

- Forex and gold market analysis
- AI/ML-based market prediction
- Technical indicator feature engineering
- Rule-based trading signal generation
- Risk management support
- Paper trading simulation
- Backtesting support
- Streamlit dashboard interface
- FastAPI backend structure
- Database support

## Tech Stack

- Python
- FastAPI
- Streamlit
- Pandas
- NumPy
- Scikit-learn
- SQLAlchemy
- Plotly

## Project Structure

```text
AURUMFX_AI_TRADING/
├── api/              # FastAPI backend files
├── core/             # Main AI trading logic
├── dashboard/        # Streamlit dashboard
├── data/             # Data files and sample data
├── database/         # Database connection and models
├── scripts/          # Helper scripts
├── utils/            # Utility functions
├── config.py         # Project configuration
├── requirements.txt  # Python dependencies
├── run.py            # Main runner file
└── README.md         # Project documentation


## Installation

git clone YOUR_REPOSITORY_URL
cd AURUMFX_AI_TRADING
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

How to Run

Run the main project: python run.py

Run the Streamlit dashboard: streamlit run dashboard/app.py

## Main Modules
# Core Module

The core/ folder contains the main trading logic of the system. It includes modules for data loading, feature engineering, machine learning prediction, market structure analysis, signal generation, risk management, paper trading, and backtesting.

# API Module

The api/ folder contains the backend API structure. It can be used to connect the trading system with other applications or frontend interfaces.

# Dashboard Module

The dashboard/ folder contains the Streamlit dashboard. It provides a user interface to view market analysis, predictions, trading signals, and system outputs.

# Database Module

The database/ folder contains database-related files such as database connection and models.

# Scripts Module

The scripts/ folder contains helper scripts used for data preparation, testing, or project setup.

# Utils Module

The utils/ folder contains common helper functions such as logging and reusable utility methods.

## Disclaimer

This project is developed for educational and research purposes only. It is not financial advice. Trading in forex, gold, or any financial market involves risk. Users should test and validate strategies properly before using them in real trading.

## Author

Developed by Hamdhi.