# Example: Custom Configuration

This example shows how to customize the downloader for different use cases.

## Example 1: Penny Stocks Only

Edit `config.py`:

```python
MIN_PRICE = 0.5
MAX_PRICE = 5.0
START_DATE = "2020-01-01"
```

Then run:
```bash
python downloader.py --reconcile
```

## Example 2: Large Cap Stocks

Edit `config.py`:

```python
MIN_PRICE = 50.0
MAX_PRICE = 500.0
START_DATE = "2015-01-01"
```

Then run:
```bash
python downloader.py --reconcile
```

## Example 3: Update Specific Stocks

```bash
python downloader.py --update --tickers AAPL MSFT GOOGL AMZN TSLA
```

## Example 4: Preview Before Downloading

```bash
# See what stocks would be added
python downloader.py --reconcile --dry-run

# See what data would be updated
python downloader.py --update --dry-run
```

## Example 5: Automated Daily Updates

Create a cron job or scheduled task:

```bash
#!/bin/bash
cd /path/to/YfinanceDownloader
python downloader.py --reconcile
python downloader.py --update
```

## Example 6: Different Data Locations

Edit `config.py`:

```python
DAILY_CSV = "/data/stocks/daily.csv"
HOURLY_CSV = "/data/stocks/hourly.csv"
NASDAQ_SCREENER = "/data/nasdaq_screener.csv"
```
