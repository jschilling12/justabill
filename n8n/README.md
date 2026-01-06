# n8n Workflows for Just A Bill

This directory contains n8n workflow exports for automating bill ingestion and summarization.

docker exec justabill-postgres psql -U justabill -d justabill -c "TRUNCATE TABLE bills CASCADE;

## Workflows

### 1. Daily Bill Sync (`daily-bill-sync.json`)
Automatically fetches bills updated in the last 24 hours from Congress.gov API and triggers ingestion.

**Schedule**: Daily at 6:00 AM ET
**Triggers**: Cron
**Actions**:
- Query Congress.gov API for recent bills
- Filter to active statuses
- Call backend `/ingest/bill` endpoint for each bill

### 2. Re-summarize Bill (`resummarize-bill.json`)
On-demand workflow to trigger re-summarization of all sections in a bill.

**Triggers**: Manual or Webhook
**Actions**:
- Call backend `/bills/{id}/resummarize` endpoint

### 3. Dead Letter Queue (`alert-workflow.json`)
Handles errors from ingestion/summarization tasks.

**Triggers**: Webhook (called by Celery on task failure)
**Actions**:
- Log error details
- Send notification (email/Slack/webhook)

## Setup Instructions

### 1. Import Workflows

1. Access n8n at http://localhost:5678
2. Log in with credentials from `.env`:
   - User: `admin` (or value of `N8N_BASIC_AUTH_USER`)
   - Password: (value of `N8N_BASIC_AUTH_PASSWORD`)
3. Go to **Workflows** > **Import from File**
4. Select each `.json` file in this directory
5. Click **Import**

### 2. Configure Credentials

#### Congress.gov API
1. Go to **Credentials** > **New**
2. Type: **Header Auth**
3. Name: `Congress API Key`
4. Header Name: `X-Api-Key`
5. Header Value: Your Congress.gov API key
6. Save

#### Backend API
1. Go to **Credentials** > **New**
2. Type: **HTTP Request** (or use built-in authentication in HTTP Request nodes)
3. For localhost: No auth required
4. For production: Configure JWT or API key as needed

### 3. Configure Workflow Parameters

For each workflow, update the following:

#### Daily Bill Sync
- **HTTP Request nodes**: Update backend URL if not using default `http://backend:8000`
- **Cron node**: Adjust schedule if needed (default: `0 6 * * *` = 6 AM daily)
- **Function node** (`Filter Active Bills`): Adjust bill status filters

#### Re-summarize Bill
- **Webhook node**: Note the webhook URL for manual triggering
- **HTTP Request node**: Update backend URL if needed

#### Alert Workflow
- **Webhook node**: Use this URL in Celery error handlers
- **Notification nodes**: Configure email/Slack/Discord with your credentials

### 4. Activate Workflows

1. Open each workflow
2. Click the toggle in the top-right to **Activate**
3. Verify the workflow is listed as "Active" in the workflows list

### 5. Test Workflows

#### Test Daily Bill Sync
1. Open the workflow
2. Click **Execute Workflow** (manual trigger)
3. Monitor execution in the **Executions** tab
4. Check backend logs for ingestion activity

#### Test Re-summarize Bill
1. Get a bill ID from the database or frontend
2. Send a POST request to the webhook URL:
   ```bash
   curl -X POST http://localhost:5678/webhook/resummarize-bill \
     -H "Content-Type: application/json" \
     -d '{"bill_id": "YOUR_BILL_ID_HERE"}'
   ```

## Workflow Details

### Daily Bill Sync Flow

```
Cron Trigger (6 AM daily)
  ↓
HTTP Request: GET Congress.gov API /bill (recent updates)
  ↓
Function: Parse response, filter active bills, de-duplicate
  ↓
Split In Batches (batch size: 5)
  ↓
For each bill:
  ↓
  HTTP Request: POST /ingest/bill
    {
      "congress": 118,
      "bill_type": "hr",
      "bill_number": 1234
    }
  ↓
  If error: Log and continue (don't break workflow)
  ↓
End
```

### Re-summarize Bill Flow

```
Webhook Trigger: /webhook/resummarize-bill
  ↓
Extract bill_id from payload
  ↓
HTTP Request: POST /bills/{bill_id}/resummarize
  ↓
Return task_id to caller
```

### Error Handling

All workflows include:
- **On Error**: Continue (don't stop workflow on individual failures)
- **Retry**: Up to 3 attempts with exponential backoff
- **Timeout**: 60 seconds per HTTP request
- **Logging**: All errors logged to n8n execution history

## Troubleshooting

### Issue: Workflows not triggering
- **Solution**: Check that workflows are **Activated** (toggle in top-right)
- **Solution**: Verify cron expression is valid
- **Solution**: Check n8n logs: `docker logs justabill-n8n`

### Issue: HTTP requests failing
- **Solution**: Verify backend is running: `curl http://localhost:8000/health`
- **Solution**: Check backend URL in workflow nodes (use `http://backend:8000` in Docker)
- **Solution**: Verify credentials are configured correctly

### Issue: Congress.gov API rate limits
- **Solution**: Add rate limiting in workflow (wait 1 second between requests)
- **Solution**: Reduce batch size in "Split In Batches" node
- **Solution**: Request higher rate limit from api.data.gov

### Issue: Bills not appearing after ingestion
- **Solution**: Check backend logs for ingestion errors
- **Solution**: Verify bill text is available (not all bills have text immediately)
- **Solution**: Check Celery worker logs for summarization errors

## Production Deployment

When deploying to production:

1. **Change webhook URLs** to production domain
2. **Add authentication** to all HTTP endpoints (API keys, JWT, etc.)
3. **Configure error notifications** (Slack, email, PagerDuty)
4. **Monitor execution history** regularly
5. **Set up alerts** for failed workflow executions
6. **Adjust rate limits** based on API quotas

## Monitoring

Monitor workflow health:

1. **Executions tab**: View all workflow runs, success/failure rates
2. **n8n logs**: `docker logs -f justabill-n8n`
3. **Backend logs**: `docker logs -f justabill-backend`
4. **Worker logs**: `docker logs -f justabill-worker`

## Advanced: Webhook Security

To secure webhooks in production:

1. Generate a secret token
2. Add to `.env`: `N8N_WEBHOOK_SECRET=your_secret_here`
3. In n8n webhook nodes:
   - Add **Authentication** > **Header Auth**
   - Header Name: `X-Webhook-Secret`
   - Header Value: `{{$env.N8N_WEBHOOK_SECRET}}`
4. Update Celery/backend to include this header when calling webhooks
