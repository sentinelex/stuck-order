# Stuck Orders Analysis Dashboard

A Streamlit web application to analyze orders that are stuck in `eticket_issued` status even after their travel end date has passed.



## Features

### Overview Dashboard
- Total stuck orders count
- Number of unique users affected
- Number of verticals affected
- Average days orders have been stuck

### Vertical Analysis
- Bar chart showing distribution across verticals
- Pie chart for visual percentage breakdown
- Detailed statistics table per vertical

### Time Analysis
- Distribution histogram of days stuck
- Box plot showing days stuck by vertical
- Order creation timeline
- Travel end date timeline

### User Impact Analysis
- Top 20 users with most stuck orders
- User-level breakdown table

### Detailed Data View
- Searchable and sortable order table
- Filter by vertical, days stuck, and order status
- Download filtered data as CSV

### Key Insights
- Most affected vertical
- Longest stuck order details
- Count of orders stuck for more than 30 days

## Installation

1. Ensure you have Python installed (recommended: Python 3.9+)

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or if using virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Usage

1. Start the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser and navigate to:
```
http://localhost:8501
```

3. Upload your CSV file containing stuck orders data

4. Explore the interactive dashboard with filters and visualizations

## CSV Format

The uploaded CSV should contain the following columns:

| Column | Description | Example |
|--------|-------------|---------|
| `order_created_timestamp` | When the order was created | 2025-11-23 09:52:53 UTC |
| `order_id` | Unique order identifier | 1329301741 |
| `account_id` | User/account identifier | 28484142 |
| `order_type_name` | Vertical (event, hotel, flight, etc.) | event |
| `order_status_name` | Current order status | eticket_issued |
| `travel_start_ts` | When the travel/event starts | 2025-11-23 16:59:59 UTC |
| `travel_end_ts` | When the travel/event ends | 2025-11-23 10:05:04.691 UTC |

## Example Query

Use this query to retrieve stuck orders data from BigQuery:

```sql
-- Add your BigQuery query here to retrieve stuck orders
-- The query should return orders where:
-- - order_status_name != 'finished'
-- - travel_end_ts < CURRENT_TIMESTAMP()
-- - order_status_name NOT IN ('cancelled', 'refunded', etc.)
```

## Data Glossary

- **account_id**: User identifier (same as user_id)
- **order_type_name**: The vertical/product type (event, hotel, flight, train, hotel_homes, airport_transfer, car, etc.)
- **days_stuck**: Calculated field showing number of days since travel ended
- **order_to_travel_days**: Days between order creation and travel start

## Filters

The dashboard provides several filters in the sidebar:

1. **Select Verticals**: Choose which product types to analyze
2. **Days Stuck Range**: Filter by how long orders have been stuck
3. **Order Status**: Filter by current order status

## Troubleshooting

### Installation Issues

If you encounter issues installing dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt --no-cache-dir
```

### Port Already in Use

If port 8501 is already in use:
```bash
streamlit run app.py --server.port 8502
```

### Performance with Large Files

For files with 42k+ rows, the app is optimized but initial load may take a few seconds. All subsequent interactions will be fast due to Streamlit's caching.

## Technical Details

- **Framework**: Streamlit 1.31.0
- **Data Processing**: Pandas 2.2.0
- **Visualizations**: Plotly 5.18.0
- **Calculations**: NumPy 1.26.3

## Notes

- All timestamps are expected in UTC format
- The app automatically calculates "days stuck" based on current time vs travel_end_ts
- Empty or malformed CSV files will show an error message
- Maximum file upload size is determined by Streamlit's default (200MB)
