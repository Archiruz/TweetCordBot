# Kubernetes Deployment Guide

## Architecture Overview

This bot now supports **two deployment modes**:

1. **CronJob Mode (Recommended for Kubernetes)**: Run once every N hours, scheduled by Kubernetes
2. **Continuous Mode (Legacy)**: Long-lived container with 8-hour sleep loop

## CronJob Deployment (Recommended)

### Prerequisites
- Kubernetes cluster running (your friend's mini PC)
- `kubectl` configured to access the cluster
- Docker image pushed to `ghcr.io/archiruz/tweetcordbot:latest`

### Step 1: Create Namespace (Optional)
```bash
kubectl create namespace tweetcordbot
# If you use a custom namespace, update all YAML files accordingly
```

### Step 2: Create Secrets
**Option A: From command line (Recommended)**
```bash
kubectl create secret generic tweetcordbot-secrets \
  --from-literal=bearer-token="YOUR_TWITTER_BEARER_TOKEN" \
  --from-literal=twitter-username="YOUR_TWITTER_USERNAME" \
  --from-literal=discord-webhook-url="YOUR_DISCORD_WEBHOOK_URL" \
  --namespace=default
```

**Option B: From YAML file**
```bash
cp kubernetes/secrets.yaml.example kubernetes/secrets.yaml
# Edit secrets.yaml with your real credentials
kubectl apply -f kubernetes/secrets.yaml
# IMPORTANT: Delete secrets.yaml after applying (don't commit it!)
rm kubernetes/secrets.yaml
```

### Step 3: Create Persistent Volume Claim
```bash
kubectl apply -f kubernetes/pvc.yaml
```

**Verify PVC is bound:**
```bash
kubectl get pvc tweetcordbot-state-pvc
# Should show STATUS: Bound
```

**Troubleshooting**: If stuck in "Pending":
- Check if your cluster has a default storage class: `kubectl get storageclass`
- If using local-path-provisioner or similar, uncomment `storageClassName` in `pvc.yaml`

### Step 4: Deploy CronJob
```bash
kubectl apply -f kubernetes/cronjob.yaml
```

### Step 5: Verify Deployment
```bash
# Check CronJob is created
kubectl get cronjob tweetcordbot-cronjob

# View schedule
kubectl describe cronjob tweetcordbot-cronjob

# Manual trigger for testing (creates a job immediately)
kubectl create job --from=cronjob/tweetcordbot-cronjob tweetcordbot-manual-test

# Watch job execution
kubectl get jobs -w

# View logs from latest job
kubectl logs -l app=tweetcordbot --tail=100

# View logs from specific job
kubectl get pods
kubectl logs <pod-name>
```

### Step 6: Monitor State File
```bash
# Check if state file is being created
POD_NAME=$(kubectl get pods -l app=tweetcordbot --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')
kubectl exec $POD_NAME -- cat /app/logs/last_tweet_id.txt
```

## Schedule Customization

Edit the `schedule` field in `kubernetes/cronjob.yaml`:

```yaml
schedule: "0 */8 * * *"  # Every 8 hours at minute 0
```

**Common schedules:**
- Every 4 hours: `"0 */4 * * *"`
- Every 6 hours: `"0 */6 * * *"`
- Every 12 hours: `"0 */12 * * *"`
- Daily at 9 AM: `"0 9 * * *"`
- Every 30 minutes: `"*/30 * * * *"`

**Cron syntax:** `minute hour day month weekday`

After changing schedule:
```bash
kubectl apply -f kubernetes/cronjob.yaml
```

## Continuous Mode Deployment (Alternative)

If you prefer the original long-lived pod approach:

### Step 1-3: Same as above (secrets and PVC)

### Step 4: Deploy as regular Deployment
```bash
kubectl apply -f kubernetes/deployment.yaml
```

**Note:** `deployment.yaml` is not included by default. Create it with:
- `RUN_MODE=continuous` environment variable
- Same mounts and secrets as CronJob

## Maintenance

### Update Docker Image
```bash
# Pull new image
kubectl rollout restart cronjob/tweetcordbot-cronjob
# OR manually delete the cronjob and recreate it
kubectl delete cronjob tweetcordbot-cronjob
kubectl apply -f kubernetes/cronjob.yaml
```

### View Historical Jobs
```bash
kubectl get jobs --sort-by=.metadata.creationTimestamp
```

### Cleanup Failed Jobs
```bash
kubectl delete jobs -l app=tweetcordbot --field-selector status.successful=0
```

### Reset State (Force Re-fetch All Tweets)
```bash
# Delete the PVC (will lose tweet tracking)
kubectl delete pvc tweetcordbot-state-pvc
kubectl apply -f kubernetes/pvc.yaml

# OR manually edit the file
POD_NAME=$(kubectl get pods -l app=tweetcordbot -o jsonpath='{.items[0].metadata.name}')
kubectl exec $POD_NAME -- rm /app/logs/last_tweet_id.txt
```

## Troubleshooting

### Bot posts duplicate tweets after restart
**Cause:** State file not persisting across restarts.

**Solution:**
1. Check PVC is bound: `kubectl get pvc`
2. Verify volume mount in pod: `kubectl describe pod <pod-name>`
3. Check file permissions: `kubectl exec <pod-name> -- ls -la /app/logs`

### CronJob not triggering
**Cause:** Invalid cron syntax or suspended CronJob.

**Solution:**
```bash
# Check for errors
kubectl describe cronjob tweetcordbot-cronjob

# Ensure not suspended
kubectl patch cronjob tweetcordbot-cronjob -p '{"spec":{"suspend":false}}'

# Manual trigger
kubectl create job --from=cronjob/tweetcordbot-cronjob test-run
```

### Rate limit errors
**Cause:** Twitter API free tier limits (500k tweets/month).

**Solution:**
- Increase schedule interval (e.g., 12 hours instead of 8)
- The bot automatically waits 15 minutes on 429 errors

### Logs not appearing
```bash
# Check if job completed
kubectl get jobs

# Check pod logs
kubectl get pods -l app=tweetcordbot
kubectl logs <pod-name>

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp
```

## Migration from Docker Compose

If migrating from existing Docker Compose setup:

1. **Export state file** (if running):
   ```bash
   docker cp tweetcord-bot:/app/logs/last_tweet_id.txt ./last_tweet_id.txt
   ```

2. **Deploy Kubernetes resources** (steps above)

3. **Import state to Kubernetes**:
   ```bash
   kubectl create configmap tweetcordbot-initial-state --from-file=last_tweet_id.txt
   
   # Then exec into first pod and copy it
   POD_NAME=$(kubectl get pods -l app=tweetcordbot -o jsonpath='{.items[0].metadata.name}')
   kubectl exec $POD_NAME -- sh -c "mkdir -p /app/logs && echo 'YOUR_LAST_TWEET_ID' > /app/logs/last_tweet_id.txt"
   ```

4. **Stop Docker Compose**:
   ```bash
   docker-compose down
   ```

## Security Best Practices

1. **Never commit secrets.yaml** - use command-line secret creation
2. **Use RBAC** - restrict CronJob permissions if running in shared cluster
3. **Rotate credentials** periodically:
   ```bash
   kubectl create secret generic tweetcordbot-secrets \
     --from-literal=bearer-token="NEW_TOKEN" \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

## Monitoring

### Set up alerts (optional)
- Monitor job failures: CronJob `.status.lastScheduleTime`
- Set up Prometheus/Grafana if available
- Use `kubectl get events` for debugging

### Logs retention
Logs are ephemeral in Kubernetes. To persist:
- Use cluster logging solution (EFK/Loki)
- OR redirect logs to external service in bot code
