# 🚀 n8n Quick Start - Import & Execute Workflows

## Step 1: Access n8n

Open your browser and go to: **http://localhost:5678**

Login:
- Username: `admin`
- Password: `change_this_password`

---

## Step 2: Import Workflows (3 Workflows)

### Workflow 1: Manual Bill Ingestion (Start Here!)

This is the easiest way to test - click a button to ingest bills.

1. In n8n, click **"Workflows"** in the left sidebar
2. Click **"Add workflow"** (+ button in top right)
3. Click the **⋮ menu** (three dots) in top right
4. Select **"Import from File..."**
5. Browse to: `c:\Users\jorda\Dropbox\2021 - 2022\Programming\Git\justabill\n8n\workflows\manual-bill-ingestion.json`
6. Click **"Import"**
7. Click **"Save"** (top right)

**To Execute:**
- Click the **"Test workflow"** button (bottom left)
- Watch it ingest 3 bills automatically!
- Check execution results in real-time

### Workflow 2: Daily Bill Sync (Automatic)

Runs automatically every day at 6 AM to fetch new bills.

1. Click **"Add workflow"** (+ button)
2. Click the **⋮ menu** → **"Import from File..."**
3. Browse to: `c:\Users\jorda\Dropbox\2021 - 2022\Programming\Git\justabill\n8n\workflows\daily-bill-sync.json`
4. Click **"Import"**
5. Click **"Save"**
6. Toggle **"Active"** (switch in top right) to enable daily runs

**To Test Now:**
- Click **"Execute Workflow"** button
- It will fetch bills updated in the last 24 hours
- Processes them in batches to avoid rate limits

### Workflow 3: Re-summarize Bill (Webhook)

Trigger re-summarization of a bill via HTTP request.

1. Click **"Add workflow"** (+ button)
2. Click the **⋮ menu** → **"Import from File..."**
3. Browse to: `c:\Users\jorda\Dropbox\2021 - 2022\Programming\Git\justabill\n8n\workflows\resummarize-bill.json`
4. Click **"Import"**
5. Click **"Save"**
6. Toggle **"Active"** to enable the webhook

**To Execute:**
```powershell
# Get a bill ID first
$bills = Invoke-RestMethod -Uri "http://localhost:8000/bills"
$billId = $bills.items[0].id

# Trigger re-summarization
$body = @{ bill_id = $billId } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:5678/webhook/resummarize-bill" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

---

## Step 3: Execute Your First Workflow

### Quick Test (Recommended)

1. Open the **"Manual Bill Ingestion"** workflow
2. Click **"Test workflow"** button (bottom left)
3. Watch the execution:
   - Node 1: Manual Trigger ✓
   - Node 2: Define Bills (HR 1, HR 2, S 1) ✓
   - Node 3: Ingest each bill ✓
   - Node 4: Wait between requests ✓

4. Check the results:
   ```powershell
   # See ingested bills
   Invoke-RestMethod -Uri "http://localhost:8000/bills"
   ```

5. Open frontend to view:
   ```powershell
   Start-Process "http://localhost:3000"
   ```

---

## Step 4: Customize the Workflows

### Change Which Bills to Ingest

Edit the **"Manual Bill Ingestion"** workflow:

1. Click on the **"Define Bills to Ingest"** node
2. Modify the JavaScript code:
```javascript
const billsToIngest = [
  { congress: 118, bill_type: 'hr', bill_number: 1 },    // H.R. 1
  { congress: 118, bill_type: 'hr', bill_number: 2 },    // H.R. 2
  { congress: 118, bill_type: 's', bill_number: 1 },     // S. 1
  { congress: 118, bill_type: 'hr', bill_number: 100 },  // Add more!
];
```

3. Click **"Save"**
4. Click **"Test workflow"** to execute with your changes

### Change Daily Sync Schedule

Edit the **"Daily Bill Sync"** workflow:

1. Click on the **"Schedule Trigger"** node
2. Change the cron expression:
   - Every day at 6 AM: `0 6 * * *`
   - Every 6 hours: `0 */6 * * *`
   - Every hour: `0 * * * *`
3. Click **"Save"**

### Adjust Rate Limiting

Edit any workflow with a **"Wait"** node:

1. Click on the **"Wait Between Bills"** node
2. Change delay amount (currently 2 seconds)
3. Increase if hitting rate limits
4. Click **"Save"**

---

## Step 5: Monitor Executions

### View Execution History

1. Click **"Executions"** in the left sidebar
2. See all workflow runs with status:
   - ✓ Green = Success
   - ⨯ Red = Failed
   - ⏸ Gray = Running

3. Click any execution to see:
   - Input/output for each node
   - Timing information
   - Error details (if failed)

### Check Backend Logs

```powershell
# Watch backend process bills
docker logs justabill-backend --tail 50 -f

# Watch worker generate summaries
docker logs justabill-worker --tail 50 -f
```

---

## 🎯 Common Workflows & Examples

### Example 1: Ingest a Specific Bill

**Via n8n:**
1. Edit "Manual Bill Ingestion" workflow
2. Change the bills array to just one bill:
```javascript
const billsToIngest = [
  { congress: 118, bill_type: 'hr', bill_number: 3684 }
];
```
3. Test workflow

**Via PowerShell:**
```powershell
$body = @{
    congress = 118
    bill_type = "hr"
    bill_number = 3684
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/ingest/bill" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

### Example 2: Bulk Ingest Top 50 Recent Bills

**Via n8n:**
1. Use the "Daily Bill Sync" workflow
2. Click "Execute Workflow"
3. It will fetch and process up to 50 recent bills

### Example 3: Schedule Custom Sync Times

**Create a new workflow:**
1. Copy "Daily Bill Sync"
2. Change schedule to run multiple times per day
3. Adjust filters to get different bill types

---

## 🔍 Troubleshooting

### Workflow fails with "Connection refused"

**Problem:** Using `localhost` instead of Docker network names

**Solution:** Update HTTP Request nodes to use:
- ✓ `http://backend:8000` (correct)
- ✗ `http://localhost:8000` (wrong - won't work from n8n container)

### Bills not showing up

**Check:**
```powershell
# Verify bills in database
Invoke-RestMethod -Uri "http://localhost:8000/bills"

# Check backend logs
docker logs justabill-backend --tail 100
```

### Rate limit errors (403 Forbidden)

**Solution:**
1. Increase wait time between requests
2. Reduce batch size in "Split In Batches" node
3. Reduce limit in Congress API call (currently 50)

### Webhook not triggering

**Check:**
1. Workflow is **Active** (toggle in top right)
2. Using correct webhook URL
3. Test with curl:
```powershell
Invoke-RestMethod -Uri "http://localhost:5678/webhook/resummarize-bill" `
    -Method Post `
    -ContentType "application/json" `
    -Body '{"bill_id":"test"}'
```

---

## 📊 Current Setup Status

✅ **Congress API Key:** Configured and working
✅ **Backend:** Running at http://localhost:8000
✅ **n8n:** Running at http://localhost:5678
✅ **Database:** Initialized with tables
✅ **Test Bill:** H.R. 1 already ingested (162 sections)

**Ready to go!** Just import the workflows and click "Test workflow"

---

## 🎉 Success Checklist

- [ ] n8n accessible at http://localhost:5678
- [ ] "Manual Bill Ingestion" workflow imported
- [ ] "Daily Bill Sync" workflow imported  
- [ ] "Re-summarize Bill" workflow imported
- [ ] Tested "Manual Bill Ingestion" workflow
- [ ] Bills visible in http://localhost:8000/bills
- [ ] Bills visible in http://localhost:3000
- [ ] "Daily Bill Sync" activated for automatic runs

---

## 🚀 Next Steps After Import

1. **Test Manual Ingestion** - Easiest way to verify everything works
2. **Activate Daily Sync** - Get new bills automatically every day
3. **Open Frontend** - View and vote on bills at http://localhost:3000
4. **Add LLM Key** - Enable section summaries (optional but recommended)
5. **Customize Workflows** - Adjust schedules, bill filters, etc.

**Start Here:** Import "Manual Bill Ingestion" and click "Test workflow"! 🎯
