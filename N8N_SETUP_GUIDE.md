# n8n Integration Setup Guide

## 🎯 Overview
n8n is your workflow automation tool that will:
- Fetch bills daily from Congress.gov
- Trigger bill ingestion in your backend
- Handle resummarization requests
- Manage error notifications

## 🚀 Quick Start

### Step 1: Access n8n
1. Open your browser and go to: **http://localhost:5678**
2. Login credentials:
   - **Username:** `admin`
   - **Password:** `change_this_password`

### Step 2: Set Up Credentials

#### A. Congress API Credential
1. Click on **"Credentials"** in the left sidebar
2. Click **"+ New Credential"**
3. Search for and select **"HTTP Header Auth"**
4. Configure:
   - **Name:** `Congress API Key`
   - **Header Name:** `X-Api-Key`
   - **Value:** `UqVRHkePi1qDb025sZdyiwvhW7QceuSu63VvKuTx`
5. Click **"Save"**

#### B. Backend API Credential (Optional - for secured endpoints)
1. Click **"+ New Credential"**
2. Select **"HTTP Header Auth"** or **"Basic Auth"** (depending on your backend auth)
3. For now, we'll use direct HTTP calls without auth since backend is internal

### Step 3: Import Workflows

#### Method 1: Through n8n UI
1. Click **"Workflows"** in the left sidebar
2. Click **"+ New Workflow"**
3. Click the **menu (⋮)** in the top right
4. Select **"Import from File"**
5. Import these two workflows:
   - `c:\Users\jorda\Dropbox\2021 - 2022\Programming\Git\justabill\n8n\workflows\daily-bill-sync.json`
   - `c:\Users\jorda\Dropbox\2021 - 2022\Programming\Git\justabill\n8n\workflows\resummarize-bill.json`

#### Method 2: Copy Workflows from Container
```powershell
# The workflows are already in the n8n volume
# Just activate them in the UI
```

### Step 4: Configure Daily Bill Sync Workflow

1. Open the **"Daily Bill Sync"** workflow
2. Click on the **"Schedule Trigger"** node
3. Set the schedule (recommended: daily at 6 AM):
   - **Mode:** `Every day at specific time`
   - **Hour:** `6`
   - **Minute:** `0`

4. Click on the **"Fetch Recent Bills"** HTTP Request node
5. Update the URL if needed:
   ```
   https://api.congress.gov/v3/bill?api_key=UqVRHkePi1qDb025sZdyiwvhW7QceuSu63VvKuTx&fromDateTime={{$today.minus({days: 1}).toFormat('yyyy-MM-dd')}}T00:00:00Z&limit=20
   ```

6. Click on the **"Ingest Bill"** HTTP Request node
7. Verify the URL points to your backend:
   ```
   http://backend:8000/ingest/bill
   ```

8. Click **"Save"** and **"Activate"** the workflow (toggle in top right)

### Step 5: Configure Resummarize Workflow

1. Open the **"Resummarize Bill"** workflow
2. Click on the **"Webhook"** node
3. Note the webhook URL (you'll use this to trigger resummarization)
4. Click **"Save"** and **"Activate"**

### Step 6: Test the Setup

#### Test Daily Sync Workflow
```powershell
# Trigger manually from n8n UI
# Click "Execute Workflow" button in the workflow editor
```

Or use PowerShell to test the backend directly:
```powershell
# Test ingesting a specific bill
$body = @{
    congress = 118
    bill_type = "hr"
    bill_number = 1
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/ingest/bill" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

#### Test Resummarize Webhook
```powershell
# Get the webhook URL from n8n (looks like http://localhost:5678/webhook/resummarize-bill)
$webhookUrl = "http://localhost:5678/webhook/resummarize-bill"

$body = @{
    bill_id = "your-bill-id-here"
} | ConvertTo-Json

Invoke-RestMethod -Uri $webhookUrl `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

---

## 📋 Workflow Details

### Daily Bill Sync Workflow
**Purpose:** Automatically fetch and ingest bills updated in the last 24 hours

**Nodes:**
1. **Schedule Trigger** - Runs daily at specified time
2. **Fetch Recent Bills** - Calls Congress.gov API
3. **Parse Response** - Extracts bill data
4. **Loop Through Bills** - Processes each bill
5. **Ingest Bill** - Calls backend `/ingest/bill` endpoint
6. **Error Handler** - Logs failures

**Configuration:**
- Runs daily (configurable)
- Fetches bills updated in last 24 hours
- Automatically triggers summarization via backend
- Handles rate limiting and errors

### Resummarize Bill Workflow
**Purpose:** Re-generate summaries for a specific bill on demand

**Trigger:** Webhook at `http://localhost:5678/webhook/resummarize-bill`

**Payload:**
```json
{
  "bill_id": "uuid-of-bill-to-resummarize"
}
```

---

## 🔧 Advanced Configuration

### Environment Variables
Update these in your `.env` file if you want to change n8n settings:

```env
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=change_this_password  # Change this!
N8N_HOST=localhost
N8N_PORT=5678
```

Then restart n8n:
```powershell
docker-compose restart n8n
```

### Adding Email Notifications
1. In n8n, add an **Email** node to the workflows
2. Configure SMTP settings in n8n credentials
3. Connect the Email node to error handlers

### Custom Workflows
Create new workflows for:
- **Bill Status Updates** - Monitor status changes
- **Daily Digest Email** - Send summary of new bills
- **Slack Notifications** - Alert on important bills
- **Data Export** - Backup bill data periodically

---

## 🧪 Testing Your Setup

### Test 1: Manual Bill Ingestion via n8n
1. Open Daily Bill Sync workflow
2. Click **"Execute Workflow"** button
3. Watch the execution in real-time
4. Check backend logs: `docker logs justabill-backend --tail 50`
5. Verify bills in database: `Invoke-RestMethod -Uri "http://localhost:8000/bills"`

### Test 2: Webhook Trigger
```powershell
# First, get a bill ID from the database
$bills = Invoke-RestMethod -Uri "http://localhost:8000/bills"
$billId = $bills.items[0].id

# Trigger resummarization via n8n webhook
$body = @{ bill_id = $billId } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:5678/webhook/resummarize-bill" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

### Test 3: Full Integration Flow
```powershell
# Run the demo script which will create test data
python scripts/demo.py

# Then check n8n execution history to see if workflows triggered
```

---

## 📊 Monitoring & Debugging

### View Workflow Executions
1. In n8n, click **"Executions"** in left sidebar
2. See all workflow runs with status (success/error)
3. Click on any execution to see detailed logs

### Check Backend Logs
```powershell
# See what bills are being ingested
docker logs justabill-backend --tail 50 -f

# See worker processing
docker logs justabill-worker --tail 50 -f
```

### Common Issues

**Issue: Workflow fails with "Connection refused"**
- Solution: Workflows should use internal Docker network names:
  - Use `http://backend:8000` NOT `http://localhost:8000`
  - Use `http://n8n:5678` for internal webhooks

**Issue: Congress API rate limit**
- Solution: Add delay between requests in n8n
- Add a **Wait** node with 1-2 second delay between API calls

**Issue: Webhook not triggering**
- Solution: Make sure workflow is **Activated** (toggle in top right)
- Check webhook URL is correct
- Test with curl or Invoke-RestMethod first

---

## 🎯 Next Steps

### Immediate
1. ✅ Access n8n at http://localhost:5678
2. ✅ Set up Congress API credential
3. ✅ Import both workflows
4. ✅ Activate Daily Bill Sync workflow
5. ✅ Test by clicking "Execute Workflow"

### Optional
1. Change n8n admin password
2. Set up email notifications
3. Create custom workflows
4. Schedule daily sync for optimal time
5. Add Slack/Discord integrations

---

## 💡 Pro Tips

1. **Test workflows manually first** before activating schedules
2. **Use the n8n execution view** to debug issues
3. **Start with a small subset** of bills (e.g., limit=5) when testing
4. **Monitor backend logs** during first few runs
5. **Set up error notifications** early to catch issues

---

## 🔗 Workflow URLs

After setup, you'll have these endpoints:

- **n8n UI:** http://localhost:5678
- **Daily Sync Webhook:** http://localhost:5678/webhook/daily-bill-sync
- **Resummarize Webhook:** http://localhost:5678/webhook/resummarize-bill
- **Backend API:** http://localhost:8000
- **Frontend:** http://localhost:3000

---

## ✅ Success Checklist

- [ ] n8n UI accessible at http://localhost:5678
- [ ] Congress API credential created
- [ ] Daily Bill Sync workflow imported
- [ ] Resummarize workflow imported
- [ ] Both workflows activated
- [ ] Test execution successful
- [ ] Bills appear in http://localhost:8000/bills
- [ ] Workflow executions visible in n8n

Once all checked, you're fully integrated! 🎉
