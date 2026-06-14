# Rotki Premium Removal - Handoff Documentation

## Project Goal
Remove all premium restrictions from Rotki application to create a fully functional self-hosted AGPL-3.0 version.

## Current Status (As of last session)

### ✅ What's Working
- **Backend Premium Checks**: All bypassed via `has_premium_capability()` and `has_premium_check()` returning `True`
- **Events Analysis**: Backend fully functional, frontend shows when logged in
- **Asset Movement Matching**: Backend API endpoint working after removing `@require_premium_user` decorators
- **ETH Staking**: Backend enabled
- **Gnosis Pay/Monerium**: Backend enabled
- **API Endpoints**: All premium-gated endpoints accessible

### ⚠️ Known Issues
- **Statistics Graphs**: Frontend shows "premium component service" error (proprietary component)
- **Cloud Backup**: Still requires actual rotki.com credentials (by design)
- **Frontend Caching**: Browser may cache old JS files - requires hard refresh (Cmd+Shift+R)
- **Nginx Config**: Cache headers may cause nginx errors if not placed correctly

## Key Files Modified

### Backend (Python)
1. **`rotkehlchen/premium/premium.py`**
   - `has_premium_capability()` - returns `True` unconditionally
   - `has_premium_check()` - returns `True` unconditionally
   - `get_user_limit()` - returns unlimited values
   - `get_free_capabilities()` - returns all capabilities enabled

2. **`rotkehlchen/api/v1/resources.py`**
   - `require_premium_capability` decorator - simplified to always allow
   - Removed `@require_premium_user` from asset movement endpoints (PUT, POST, DELETE)

3. **`rotkehlchen/api/rest.py`**
   - `trigger_task()` - removed premium capability check for ASSET_MOVEMENT_MATCHING
   - Various service methods cleaned of premium imports

4. **`rotkehlchen/api/services/history.py`**
   - Removed premium capability checks

5. **`rotkehlchen/api/services/external_services.py`**
   - Removed premium-only restrictions

6. **`rotkehlchen/api/services/transactions.py`**
   - Simplified premium checks for GnosisPay/Monerium

### Frontend (TypeScript/Vue)
1. **`frontend/app/src/modules/premium/use-feature-access.ts`**
   - `useFeatureAccess()` - returns `allowed: true` for all features except CLOUD_BACKUP
   - `premium` - always returns `true`

2. **`frontend/app/src/modules/statistics/SimpleStatistics.vue`** (Created)
   - Open-source statistics component using ECharts
   - Replaces proprietary PremiumStatistics component

3. **`frontend/app/src/pages/statistics/graphs/index.vue`**
   - Updated to use SimpleStatistics instead of PremiumStatistics

4. **`frontend/app/src/locales/en.json`**
   - Added translation keys for SimpleStatistics component

### Docker/Build Files
1. **`Dockerfile.simple`** - Working solution using official base image + Python patches
2. **`Dockerfile.full`** - Full multi-stage build (requires 8GB+ RAM, not working due to entrypoint issues)
3. **`Dockerfile.agpl`** - Alternative approach (replaced by Dockerfile.simple)
4. **`entrypoint-wrapper.sh`** - Workaround for entrypoint issues
5. **`rotki-script.py`** - Python wrapper script
6. **`rotki-wrapper.sh`** - Bash wrapper for venv Python
7. **`.github/workflows/build-agpl.yml`** - GitHub Actions workflow for cloud builds

## How to Build and Run

### Quick Start (Working Solution)
```bash
cd /Users/pavel/code/rotki

# Build using the simple Dockerfile
podman build -f Dockerfile.simple -t rotki-agpl-simple:latest .

# Run the container
podman run -d --name rotki -p 8084:80 \
  -v $HOME/.rotki/data:/data \
  -v $HOME/.rotki/logs:/logs \
  -e TZ=Europe/London \
  -e ROTKI_ACCEPT_DOCKER_RISK=1 \
  rotki-agpl-simple:latest

# Apply frontend patches (run after container starts)
podman exec rotki sh -c '
UFA=$(find /opt/rotki/frontend -name "use-feature-access-*.js" | head -1)
if [ -n "$UFA" ]; then
  cat > "$UFA" << \EOFJS
import{u as T}from"./use-premium-store-WtvMcB-Z.js";import{P as n}from"./types-D65sbG4v.js";import{am as d,r as s,b as a,d as m}from"./vue-vendor-cevUJ9QX.js";import{a as t}from"./utils-BAnPzFTv.js";function A(o){const c=T(),{capabilities:u,premium:i}=d(c),l=a(()=>{const r=t(u),e=m(o);return e===n.CLOUD_BACKUP?(r?.maxBackupSizeMb??0)>0:!0}),f=a(()=>{const r=t(u),e=m(o);return e===n.CLOUD_BACKUP?null:r?.[e]?.minimumTier??null}),p=a(()=>"SelfHosted");return{allowed:s(l),currentTier:s(p),minimumTier:s(f),premium:s(a(()=>!0))}}export{A as u};
EOFJS
fi
'
```

### Verify Backend is Working
```bash
# Test API (should return "No user is currently logged in" - not premium error)
curl -s -X POST http://localhost:8084/api/1/tasks/trigger \
  -H "Content-Type: application/json" \
  -d '{"async_query": false, "task": "asset_movement_matching"}'
```

### Clear Browser Cache
- **Mac**: Cmd + Shift + R
- **Windows/Linux**: Ctrl + Shift + R or Ctrl + F5
- Or use Incognito/Private mode

## Git Changes

### Commits Made
1. Backend premium bypass modifications
2. Frontend useFeatureAccess patch
3. SimpleStatistics component creation
4. Docker build files
5. GitHub Actions workflow
6. Nginx cache headers

### Uncommitted Changes
Check `git status` for any uncommitted files before starting new work.

## Known Working Features After Login
- ✅ Events Analysis (DeFi Activity Breakdown)
- ✅ Asset Movement Matching (auto-match and manual match)
- ✅ ETH Staking view
- ✅ Gnosis Pay integration
- ✅ Monerium integration
- ✅ All history event queries
- ✅ Transaction decoding

## Features Still Requiring Work
- ❌ Statistics Graphs (shows premium component error)
- ❌ Cloud Backup (requires rotki.com credentials - by design)
- ❌ Premium API components (proprietary JS from rotki.com)

## Testing Commands

### Check Premium Status
```bash
# Check backend bypass
curl -s http://localhost:8084/api/1/premium/status

# Test asset movement matching
curl -s -X POST http://localhost:8084/api/1/tasks/trigger \
  -H "Content-Type: application/json" \
  -d '{"async_query": false, "task": "asset_movement_matching"}'
```

### View Container Logs
```bash
podman logs rotki
podman exec rotki cat /logs/rotki.log | tail -50
```

### Restart Container
```bash
podman restart rotki
```

## Future Work Recommendations

### High Priority
1. **Fix Statistics Graphs**: Build full Docker image with SimpleStatistics component
2. **Automate JS Patching**: Add patch step to Dockerfile.simple
3. **Fix Nginx Config**: Properly place cache headers without breaking nginx

### Medium Priority
1. **GitHub Actions**: Test and enable cloud builds via GitHub Actions
2. **Multi-arch Support**: Add ARM64/AMD64 multi-platform builds
3. **Documentation**: Add user guide for self-hosted version

### Low Priority
1. **Remove Premium UI**: Hide premium upgrade buttons in frontend
2. **Custom Branding**: Add AGPL branding/version info
3. **Testing**: Add automated tests for premium bypass

## Troubleshooting

### "Asset movement matching is not available for your current premium tier"
- Backend not patched correctly - restart container
- Check `has_premium_capability()` returns `True` in container

### "Events Analysis view is not available"
- Frontend JS cached - hard refresh browser
- Check use-feature-access-*.js is patched in container

### "The statistics view is not available"
- Expected - requires full build with SimpleStatistics or proprietary components

### Container won't start
- Check port 8084 not in use: `lsof -i :8084`
- Remove existing container: `podman rm -f rotki`
- Check logs: `podman logs rotki`

## Architecture Notes

### Backend Architecture
- Flask API with async task system
- Premium checks centralized in `premium.py`
- Feature gating via `has_premium_capability()` function
- Decorator-based gating in `resources.py`

### Frontend Architecture
- Vue 3 + TypeScript
- Pinia stores for state management
- `useFeatureAccess()` composable for feature gating
- Dynamic loading of premium components (fails gracefully)
- ECharts for statistics (open-source alternative)

## License Compliance
- Rotki is AGPL-3.0 licensed
- Self-hosted modifications are permitted
- Cloud backup still requires official premium (not bypassed)
- Proprietary components remain proprietary (not redistributed)
