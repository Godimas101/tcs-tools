# 🚀 Launch Library Agency Search

Desktop application to search through space agencies from The Space Devs Launch Library API.

## Features

✅ **Live Search** - Results update as you type  
✅ **Search Fields** - Name, abbreviation, country, and description  
✅ **Auto-Caching** - Saves data locally, auto-loads if less than 7 days old  
✅ **CSV Export** - Export your search results  
✅ **Full API Pagination** - Fetches ALL agencies from the API  

## Installation

1. **Install Python dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Run the application:**
   ```powershell
   python agency_search.py
   ```

## Usage

1. **First Time:** Click "Fetch Agencies from API" to download the full list (~500+ agencies)
2. **Search:** Type in the search box - results update live!
   - Search by name: "SpaceX"
   - Search by country: "United States"
   - Search by abbreviation: "NASA"
   - Search in description: "satellite"
3. **Export:** Click "Export Results to CSV" to save filtered results
4. **Next Time:** App auto-loads cached data if it's less than 7 days old

## Data Source

Data provided by [The Space Devs Launch Library API](https://thespacedevs.com/)  
Endpoint: `https://ll.thespacedevs.com/2.3.0/agencies/`

## Files

- `agency_search.py` - Main application
- `agencies.json` - Cached data (auto-generated)
- `requirements.txt` - Python dependencies

## Example Search Queries

- "SpaceX" → Space Exploration Technologies Corp.
- "Russia" → All Russian agencies
- "NASA" → National Aeronautics and Space Administration
- "commercial" → All commercial space companies in descriptions
- "CNSA" → China National Space Administration

Enjoy! 🛸
