# Deployment Checklist for Kubernetes

## Pre-Deployment Checklist

### 1. Code Validation ✅
- [x] Persistence implementation tested locally
- [x] No syntax errors in main.py
- [x] State file successfully created in logs/
- [x] .gitignore updated to exclude logs/

### 2. Environment Preparation
- [ ] Docker image built and pushed to ghcr.io
- [ ] Kubernetes cluster accessible via kubectl
- [ ] kubectl configured and working
- [ ] Twitter API credentials ready
- [ ] Discord webhook URL ready

### 3. Kubernetes Resources
- [ ] Namespace created (if using custom namespace)
- [ ] Secrets created with correct credentials
- [ ] Storage class available (check with: `kubectl get sc`)

## Deployment Steps

### Step 1: Verify Kubernetes Access
```bash
# Check cluster connectivity
kubectl cluster-info

# Check available storage classes
kubectl get storageclass

# Should show at least one storage class
```
- [ ] Cluster accessible
- [ ] Storage class available

### Step 2: Create Secrets
```bash
kubectl create secret generic tweetcordbot-secrets \
  --from-literal=bearer-token="YOUR_TWITTER_BEARER_TOKEN" \
  --from-literal=twitter-username="YOUR_TWITTER_USERNAME" \
  --from-literal=discord-webhook-url="YOUR_DISCORD_WEBHOOK_URL" \
  --namespace=default
```
- [ ] Secrets created successfully
- [ ] Verify: `kubectl get secrets tweetcordbot-secrets`

### Step 3: Deploy PersistentVolumeClaim
```bash
cd kubernetes
kubectl apply -f pvc.yaml
```
- [ ] PVC created
- [ ] PVC bound (check: `kubectl get pvc`)
  - If stuck in "Pending", check storage class configuration

### Step 4: Deploy CronJob
```bash
kubectl apply -f cronjob.yaml
```
- [ ] CronJob created
- [ ] Verify: `kubectl get cronjob tweetcordbot-cronjob`

### Step 5: Manual Test Run
```bash
# Trigger a manual run
kubectl create job --from=cronjob/tweetcordbot-cronjob manual-test-$(date +%s)

# Watch the job
kubectl get jobs -w

# Should transition: ContainerCreating → Running → Completed
```
- [ ] Job created successfully
- [ ] Pod started
- [ ] Pod completed without errors

### Step 6: Verify Logs
```bash
# Get the pod name
POD_NAME=$(kubectl get pods -l app=tweetcordbot --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}')

# View logs
kubectl logs $POD_NAME
```
**Expected log output:**
```
Starting TweetCordBot background worker (mode: once)...
Loaded last tweet ID from state: <tweet_id> OR No state file found. Starting fresh.
Starting tweet monitor for @<username> (user_id=...)
Found X new tweets OR No new tweets found.
Run mode is 'once'. Exiting after single check.
```
- [ ] Logs show successful execution
- [ ] No error messages

### Step 7: Verify State Persistence
```bash
# Check state file was created
kubectl exec $POD_NAME -- cat /app/logs/last_tweet_id.txt

# Should output a tweet ID (e.g., 1234567890123456789)
```
- [ ] State file exists
- [ ] Contains valid tweet ID

### Step 8: Test Persistence Across Runs
```bash
# Trigger another manual run
kubectl create job --from=cronjob/tweetcordbot-cronjob manual-test-2-$(date +%s)

# Wait for completion, then check logs
kubectl logs -l app=tweetcordbot --tail=50 | grep "Loaded last tweet ID"

# Should show: "Loaded last tweet ID from state: <same_id_as_before>"
```
- [ ] Second run loads previous state
- [ ] No duplicate tweets posted to Discord

### Step 9: Verify CronJob Schedule
```bash
kubectl describe cronjob tweetcordbot-cronjob

# Look for:
# Schedule: 0 */8 * * *
# Last Schedule Time: <recent timestamp>
# Active: <none or 1>
```
- [ ] Schedule is correct (every 8 hours)
- [ ] CronJob not suspended

## Post-Deployment Monitoring

### First 24 Hours
- [ ] Check after 8 hours: New job created automatically
- [ ] Check after 16 hours: Second automatic job created
- [ ] Check after 24 hours: Third automatic job created
- [ ] No failed jobs: `kubectl get jobs -l app=tweetcordbot`

### Verify No Duplicates
- [ ] Monitor Discord channel for 24-48 hours
- [ ] Confirm no duplicate tweet posts
- [ ] Verify only new tweets are posted

### Clean Up Test Jobs
```bash
# Delete manual test jobs
kubectl delete jobs -l app=tweetcordbot manual-test-*
```
- [ ] Test jobs cleaned up

## Troubleshooting Checklist

### If Pod Fails to Start
- [ ] Check image pull: `kubectl describe pod <pod-name> | grep -A5 "Events:"`
- [ ] Verify image exists: `docker pull ghcr.io/archiruz/tweetcordbot:latest`
- [ ] Check secrets: `kubectl get secrets tweetcordbot-secrets -o yaml`

### If Job Completes But No Tweets Posted
- [ ] Check logs for API errors: `kubectl logs <pod-name> | grep "ERROR"`
- [ ] Verify Twitter credentials are valid
- [ ] Test webhook manually:
  ```bash
  curl -X POST -H "Content-Type: application/json" \
    -d '{"content":"test"}' YOUR_DISCORD_WEBHOOK_URL
  ```

### If State Not Persisting
- [ ] Check PVC is bound: `kubectl get pvc`
- [ ] Verify volume mount: `kubectl describe pod <pod-name> | grep -A10 "Mounts:"`
- [ ] Check file permissions:
  ```bash
  kubectl exec <pod-name> -- ls -la /app/logs/
  ```

### If CronJob Not Triggering
- [ ] Check CronJob status: `kubectl describe cronjob tweetcordbot-cronjob`
- [ ] Verify not suspended: `kubectl patch cronjob tweetcordbot-cronjob -p '{"spec":{"suspend":false}}'`
- [ ] Check timezone settings (CronJobs use UTC)

## Rollback Plan

### If Issues Occur
1. **Suspend CronJob immediately:**
   ```bash
   kubectl patch cronjob tweetcordbot-cronjob -p '{"spec":{"suspend":true}}'
   ```
   - [ ] CronJob suspended

2. **Review logs of failed jobs:**
   ```bash
   kubectl get jobs
   kubectl logs <failed-job-pod>
   ```
   - [ ] Logs reviewed
   - [ ] Issue identified

3. **Fix issue and test:**
   - [ ] Code/config fixed
   - [ ] Manual test successful

4. **Resume CronJob:**
   ```bash
   kubectl patch cronjob tweetcordbot-cronjob -p '{"spec":{"suspend":false}}'
   ```
   - [ ] CronJob resumed

### If Need to Revert to Docker Compose
```bash
# On mini PC
cd /path/to/TweetCordBot
docker-compose up -d
```
- [ ] Docker Compose deployment started
- [ ] Kubernetes CronJob suspended or deleted

## Maintenance Schedule

### Weekly
- [ ] Review job history: `kubectl get jobs --sort-by=.metadata.creationTimestamp`
- [ ] Check for failed jobs: `kubectl get jobs -l app=tweetcordbot --field-selector status.successful=0`
- [ ] Verify state file still valid

### Monthly
- [ ] Review resource usage: `kubectl top pods -l app=tweetcordbot`
- [ ] Check PVC usage: `kubectl exec <latest-pod> -- du -sh /app/logs/`
- [ ] Rotate logs if needed

### Quarterly
- [ ] Update Docker image to latest version
- [ ] Review and optimize schedule if needed
- [ ] Test disaster recovery (delete PVC and recreate)

## Success Criteria

✅ **Deployment Successful When:**
- [ ] CronJob runs every 8 hours without errors
- [ ] New tweets are posted to Discord within 8 hours
- [ ] No duplicate tweets after mini PC restart
- [ ] State persists across pod restarts
- [ ] Logs show consistent "Loaded last tweet ID from state" messages
- [ ] Failed jobs history is empty or minimal

## Emergency Contacts

- GitHub Issues: https://github.com/Archiruz/TweetCordBot/issues
- Documentation: See `kubernetes/DEPLOYMENT.md`
- Architecture Guide: See `docs/ARCHITECTURE.md`

---

**Date Deployed:** _________________

**Deployed By:** _________________

**Kubernetes Cluster:** _________________

**Notes:**
_______________________________________________________
_______________________________________________________
_______________________________________________________
