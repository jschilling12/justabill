# Bill Popularity Detection Workflow

## Overview
This n8n workflow automatically detects "popular" bills by checking web mentions and updates the backend popularity flags. Bills with ≥3 web mentions are marked as popular.

## Workflow: `bill-popularity-check.json`

### What it does
1. **Schedule Trigger**: Runs daily at 8 AM
2. **Fetch Recent Law Impact Bills**: Gets the latest HR/S bills from `/bills?law_impact_only=true`
3. **Extract Bills**: Converts the response into individual items
4. **Split In Batches**: Processes 5 bills at a time
5. **Search Web for Bill**: Queries a search API for mentions (e.g., Google Custom Search, Bing, NewsAPI)
6. **Calculate Popularity**: Counts hits; marks as popular if ≥3
7. **Update Bill Popularity**: PATCHes `/bills/{id}/popularity` with `is_popular` and `popularity_score`
8. **Wait**: 2-second delay between batches for rate limiting

### Search API Options

The example workflow uses **Google Custom Search API**. You can replace it with:

#### Option 1: Google Custom Search API (current example)
- Get API key: https://developers.google.com/custom-search/v1/overview
- Create a custom search engine: https://programmablesearchengine.google.com/
- Replace `YOUR_GOOGLE_API_KEY` and `YOUR_SEARCH_ENGINE_ID` in the "Search Web for Bill" node
- Query format: `HR 504 119th Congress`
- Free tier: 100 queries/day

#### Option 2: Bing Web Search API
- Get API key: https://www.microsoft.com/en-us/bing/apis/bing-web-search-api
- Endpoint: `https://api.bing.microsoft.com/v7.0/search`
- Headers: `Ocp-Apim-Subscription-Key: YOUR_KEY`
- Query param: `?q=HR+504+119th+Congress`
- Free tier: 1000 queries/month

#### Option 3: NewsAPI
- Get API key: https://newsapi.org/
- Endpoint: `https://newsapi.org/v2/everything`
- Query param: `?q=HR+504+119th+Congress&apiKey=YOUR_KEY`
- Best for recent news mentions
- Free tier: 100 requests/day

#### Option 4: SerpAPI
- Get API key: https://serpapi.com/
- Endpoint: `https://serpapi.com/search`
- Params: `?q=HR+504&api_key=YOUR_KEY`
- Aggregates multiple search engines
- Free tier: 100 searches/month

### Customizing Popularity Threshold

In the **Calculate Popularity** node, adjust the threshold:

```javascript
// Current: ≥3 mentions = popular
isPopular = hitCount >= 3;

// More selective: ≥10 mentions
isPopular = hitCount >= 10;

// Very popular only: ≥50 mentions
isPopular = hitCount >= 50;
```

### Setting Up in n8n

1. Import the workflow:
   ```bash
   docker exec justabill-n8n n8n import:workflow --input=/home/node/.n8n/workflows/bill-popularity-check.json
   ```

2. Open workflow in n8n UI (`http://localhost:5678`)

3. Configure the **Search Web for Bill** node:
   - Replace `YOUR_GOOGLE_API_KEY` with your actual API key
   - Replace `YOUR_SEARCH_ENGINE_ID` with your custom search engine ID
   - Or swap the entire node for a different search provider

4. Test manually:
   - Click **Execute workflow**
   - Check the "Calculate Popularity" node output to see which bills got marked popular
   - Verify in backend logs: `PATCH /bills/{id}/popularity`

5. Activate for daily runs:
   - Click **Active** toggle in the top-right
   - The workflow will run daily at 8 AM

### Verifying Results

#### In the Backend
```bash
# Check which bills are marked popular
docker exec justabill-postgres psql -U justabill -d justabill -c "SELECT bill_type, bill_number, title, is_popular, popularity_score FROM bills WHERE is_popular = true ORDER BY popularity_score DESC LIMIT 10;"
```

#### In the Frontend
- Go to `http://localhost:3000`
- The "🔥 Popular now" section will display popular bills
- Each bill shows a badge with mention count

#### Via API
```powershell
Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:8000/bills?popular=true&page_size=10" | Select-Object -ExpandProperty Content | ConvertFrom-Json | Select-Object -ExpandProperty items | Select-Object bill_type, bill_number, title, popularity_score
```

### Troubleshooting

**No popular bills showing up?**
- Check n8n execution logs for API errors
- Verify your search API key is valid
- Try lowering the popularity threshold (e.g., `hitCount >= 1`)
- Manually mark a bill as popular for testing:
  ```powershell
  $body = @{ is_popular = $true; popularity_score = 10 } | ConvertTo-Json
  Invoke-WebRequest -Method PATCH -Uri "http://localhost:8000/bills/BILL_ID_HERE/popularity" -Body $body -ContentType "application/json"
  ```

**Search API rate limits exceeded?**
- Increase the **Wait** node delay (e.g., 5 seconds)
- Reduce batch size in **Split In Batches** (e.g., 3 instead of 5)
- Use a different search provider with higher limits

**"Loop doesnt actually connect to a Node" error?**
- Make sure **Wait** node connects back to **Split In Batches** (Loop port, not Done port)

### Cost Considerations

With default settings (50 bills/day, 1 search per bill):
- Google Custom Search API (free tier): 100/day → ✅ sufficient
- NewsAPI (free tier): 100/day → ✅ sufficient
- Bing API (free tier): ~33/day → ⚠️ may need paid tier or run every 2-3 days

For higher volume, consider caching results or only checking bills updated in last 7 days.
