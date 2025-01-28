from fastapi import FastAPI
import requests
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler

from sentiment import router as sentiment_router

load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


stock_data_cache = {}

scheduler = BackgroundScheduler()

def fetch_stock_data():
    """Fetch stock data from Finnhub API and store it in cache."""
    symbols = os.getenv("STOCK_SYMBOLS", "AAPL,MSFT,GOOGL,AMZN,TSLA").split(",")
    api_key = os.getenv("FINNHUB_API_KEY")
    for symbol in symbols:
        try:
            response = requests.get(
                "https://finnhub.io/api/v1/quote",
                params={"symbol": symbol, "token": api_key},
            )
            response.raise_for_status()
            data = response.json()
            if symbol in stock_data_cache:
                stock_data_cache[symbol].append({
                    "price": data["c"],
                    "high": data["h"],
                    "low": data["l"],
                    "open": data["o"],
                    "previous_close": data["pc"],
                    "timestamp": data["t"],  # add timestamp for each entry
                })
            else:
                # If no data exists for the symbol, create a new list with the current data
                stock_data_cache[symbol] = [{
                    "price": data["c"],
                    "high": data["h"],
                    "low": data["l"],
                    "open": data["o"],
                    "previous_close": data["pc"],
                    "timestamp": data["t"],  # add timestamp for each entry
                }]
        except Exception as e:
            print(f"Error fetching data for {symbol}: {e}")

app.include_router(sentiment_router, prefix="/sentiment")            

# Start scheduler on startup
@app.on_event("startup")
def startup_event():
    fetch_stock_data()  # Fetch data immediately on startup
    scheduler.add_job(fetch_stock_data, "interval", minutes=5)  # Fetch every 5 minutes
    scheduler.start()

@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Stock Backend API!"}

@app.get("/stocks")
def get_all_stocks():
    """Get data for all stocks."""
    return stock_data_cache

@app.get("/stocks/{symbol}")
def get_stock(symbol: str):
    """Get data for a specific stock."""
    if symbol not in stock_data_cache:
        return {"error": "Stock not found"}
    return {symbol: stock_data_cache[symbol]}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)