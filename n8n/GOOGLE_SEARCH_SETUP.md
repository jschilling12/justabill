# Google Custom Search API Setup Guide

## Step 1: Get Your Google API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the **Custom Search API**:
   - Navigate to: **APIs & Services** → **Library**
   - Search for "Custom Search API"
   - Click **Enable**
4. Create credentials:
   - Go to: **APIs & Services** → **Credentials**
   - Click **+ CREATE CREDENTIALS** → **API Key**
   - Copy your API key (looks like: `AIzaSyAbc123...`)
   - ⚠️ **Important**: Restrict the key to "Custom Search API" only for security

## Step 2: Create a Custom Search Engine

1. Go to [Programmable Search Engine](https://programmablesearchengine.google.com/controlpanel/all)
2. Click **Add** to create a new search engine
3. Configure:
   - **Search engine name**: `US Bills Search`
   - **What to search**: Select **Search the entire web**
   - Click **Create**
4. Get your Search Engine ID:
   - After creation, click **Customize**
   - Find **Search engine ID** (looks like: `a1b2c3d4e5f6g7h8i`)
   - Copy this ID

## Step 3: Update the n8n Workflow

1. **Import the workflow** (if not already done):
   ```powershell
   docker exec justabill-n8n n8n import:workflow --input=/home/node/.n8n/workflows/bill-popularity-check.json
   ```

2. **Open n8n UI**: http://localhost:5678

3. **Find the workflow**: "Bill Popularity Check"

4. **Edit the "Search Web for Bill" node**:
   - Click on the node
   - Update the query parameters:
     - `key`: Replace `YOUR_GOOGLE_API_KEY` with your actual API key
     - `cx`: Replace `YOUR_SEARCH_ENGINE_ID` with your search engine ID

5. **Save the workflow** (Ctrl+S)

## Step 4: Test the Workflow

1. Click **Execute Workflow** in the n8n UI
2. Watch the execution:
   - "Fetch Recent Law Impact Bills" should return your HR/S bills
   - "Search Web for Bill" should query Google for each bill
   - "Calculate Popularity" should show `hitCount` and `is_popular` values
   - "Update Bill Popularity" should PATCH your backend

3. Check for errors:
   - If you see `403 Forbidden`: Your API key isn't valid or Custom Search API isn't enabled
   - If you see `400 Bad Request`: Check that your search engine ID is correct

## Step 5: Verify Results

Check the backend to see which bills were marked popular:

```powershell
# View all popular bills
docker exec justabill-postgres psql -U justabill -d justabill -c "SELECT bill_type, bill_number, title, is_popular, popularity_score FROM bills WHERE is_popular = true ORDER BY popularity_score DESC;"

# Via API
Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:8000/bills?popular=true" | Select-Object -ExpandProperty Content | ConvertFrom-Json | Select-Object -ExpandProperty items | Format-Table bill_type, bill_number, title, popularity_score
```

Check the frontend:
- Go to http://localhost:3000
- The "🔥 Popular now" section should show bills with their mention counts

## Step 6: Activate for Daily Runs

Once testing is successful:
1. In n8n UI, toggle **Active** in the top-right
2. The workflow will run automatically every day at 8 AM
3. Check execution history: **Executions** tab in n8n

## Quota & Rate Limits

**Free Tier:**
- 100 search queries per day
- 10,000 queries per month (if you upgrade to paid billing)

**Current Usage:**
- Default: Checks up to 50 bills per day = 50 queries
- With batching & 2-second delay: ~2.5 minutes per run

**If You Hit Limits:**
- Reduce `page_size` in "Fetch Recent Law Impact Bills" (e.g., 20 instead of 50)
- Increase `batchSize` in "Split In Batches" to process faster
- Add caching: Only re-check bills updated in last 24 hours

## Troubleshooting

### "Invalid API Key"
- Double-check you enabled **Custom Search API** (not just created a key)
- Make sure you copied the full key (no spaces/line breaks)

### "Invalid Search Engine ID"
- Verify the ID in the Programmable Search Engine console
- It should be alphanumeric without spaces

### "No search results" / `hitCount = 0` for all bills
- Test a query manually: https://www.googleapis.com/customsearch/v1?key=YOUR_KEY&cx=YOUR_CX&q=HR+1+118th+Congress
- If manual query works but workflow doesn't, check the bill number/congress formatting

### Bills aren't showing as popular
- Check the popularity threshold in "Calculate Popularity" node (currently `>= 3`)
- Try lowering to `>= 1` for testing
- Verify Google is actually finding results (check execution output)

## Cost Estimate

**Free Forever:**
- 100 queries/day = up to 100 bills checked daily
- Perfect for this use case (typically <50 active bills)

**If You Need More:**
- $5 per 1,000 additional queries
- Still very cheap: ~$7.50/month for 500 bills/day

## Next Steps

After setup:
1. Let it run for 1 day and observe which bills become popular
2. Adjust the threshold if too many/too few bills are marked
3. Consider adding filters: only check bills updated in last 7 days (saves quota)
