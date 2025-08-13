# 🚀 GlyphMind AI Backend - Render.com Deployment Guide

## 📋 Prerequisites

1. **Render.com Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Your GlyphMind AI code in a GitHub repository
3. **API Keys** (optional): Google Search, YouTube, OpenAI, etc.

## 🔧 Deployment Steps

### Step 1: Connect Repository to Render

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select the repository containing your GlyphMind AI code

### Step 2: Configure Web Service

**Basic Settings:**
- **Name**: `glyphmind-backend` (or your preferred name)
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: `main`
- **Root Directory**: `backend` (important!)

**Build & Deploy:**
- **Python Runtime**: `3.11.9` (recommended for stability)
- **Build Command**: `pip install --upgrade pip && pip install -r requirements-minimal.txt`
- **Start Command**: `python render_start.py`

**Alternative (if build fails):**
- **Build Command**: `pip install --upgrade pip && pip install fastapi uvicorn[standard] pydantic aiohttp requests beautifulsoup4 aiosqlite python-dotenv`
- **Start Command**: `python render_start.py`

### Step 3: Configure Environment Variables

Add these environment variables in Render dashboard:

**Required:**
- `ENVIRONMENT=production`
- `DATA_DIR=/opt/render/project/src/data`
- `LOG_LEVEL=info`

**Optional API Keys:**
- `GOOGLE_SEARCH_API_KEY=your_google_api_key`
- `GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id`
- `YOUTUBE_API_KEY=your_youtube_api_key`
- `OPENAI_API_KEY=your_openai_api_key`
- `ANTHROPIC_API_KEY=your_anthropic_api_key`

**CORS Configuration:**
- `ALLOWED_ORIGINS=https://your-space.hf.space,https://another-domain.com`

### Step 4: Deploy

1. Click "Create Web Service"
2. Render will automatically build and deploy your backend
3. Monitor the deploy logs for any issues
4. Once deployed, note your backend URL: `https://your-service.onrender.com`

## 🔍 Verification

### Test Endpoints

1. **Health Check**: `GET https://your-service.onrender.com/health`
   ```json
   {
     "status": "healthy",
     "timestamp": "2024-01-01T12:00:00.000Z",
     "environment": "production",
     "port": "10000",
     "data_dir": "/opt/render/project/src/data"
   }
   ```

2. **Root Endpoint**: `GET https://your-service.onrender.com/`
   ```json
   {
     "message": "🧠 GlyphMind AI Backend",
     "status": "running",
     "docs": "/docs",
     "health": "/health"
   }
   ```

3. **API Documentation**: Visit `https://your-service.onrender.com/docs`

4. **Chat Endpoint**: `POST https://your-service.onrender.com/chat`
   ```json
   {
     "text": "Hello, GlyphMind!"
   }
   ```

## 📊 Monitoring

### Render Dashboard
- **Logs**: View real-time logs in Render dashboard
- **Metrics**: Monitor CPU, memory, and response times
- **Health**: Automatic health checks via `/health` endpoint

### Log Levels
- `DEBUG`: Detailed debugging info
- `INFO`: General information (recommended)
- `WARNING`: Warning messages only
- `ERROR`: Error messages only

## 🔧 Troubleshooting

### Common Issues

#### 1. Build Failures (Most Common)

**Problem A**: `pydantic-core` Rust compilation error
```
error: failed to create directory `/usr/local/cargo/registry/cache/`
Caused by: Read-only file system (os error 30)
```
**Solution**: 
- Use `requirements-minimal.txt` instead: `pip install -r requirements-minimal.txt`
- Or use direct install: `pip install fastapi uvicorn[standard] pydantic aiohttp requests beautifulsoup4 aiosqlite python-dotenv`
- Set Python version to 3.11.9 in Render settings

**Problem B**: Python 3.13 compatibility issues
**Solution**:
- Add `.python-version` file with `3.11.9`
- Or set in Render dashboard: Environment → Python Version → `3.11.9`

**Problem C**: General pip install fails
**Solution**: 
- Check `requirements.txt` for invalid packages
- Try upgrading pip first: `pip install --upgrade pip && pip install -r requirements.txt`
- Use minimal requirements for debugging

#### 2. App Won't Start
**Problem**: Service fails to start
**Solution**:
- Check `render_start.py` for syntax errors
- Verify `PORT` environment variable is being used
- Check startup logs for specific errors

#### 3. Database Errors
**Problem**: SQLite database issues
**Solution**:
- Verify `DATA_DIR` is set correctly
- Check file permissions
- Monitor disk usage

#### 4. CORS Errors
**Problem**: Frontend can't connect
**Solution**:
- Add your frontend URL to `ALLOWED_ORIGINS`
- Check CORS configuration in logs
- Verify frontend is sending requests to correct backend URL

#### 5. Memory Issues (Free Tier)
**Problem**: App crashes due to memory limits
**Solution**:
- Optimize `requirements.txt` (remove unused packages)
- Reduce log file sizes
- Consider upgrading to paid plan

### Debug Commands

**Check Environment Variables:**
```bash
# In Render shell (if available)
env | grep -E "(PORT|DATA_DIR|ENVIRONMENT)"
```

**Check Disk Usage:**
```bash
df -h
du -sh /opt/render/project/src/data
```

**Check Logs:**
```bash
tail -f /opt/render/project/src/data/logs/glyphmind.log
```

## 📈 Optimization for Free Tier

### Memory Usage
- **Minimal Dependencies**: Only essential packages in `requirements.txt`
- **Efficient Logging**: Console-first logging with limited file logging
- **Database Optimization**: SQLite with reduced cache sizes

### Performance
- **Async Operations**: All I/O operations use async/await
- **Connection Pooling**: Reuse database connections
- **Caching**: Smart caching of API responses

### Storage
- **Persistent Data**: Uses `/opt/render/project/src/data` for persistence
- **Log Rotation**: Automatic log file rotation to prevent disk full
- **Cleanup**: Automatic cleanup of old cache files

## 🔄 Updates and Maintenance

### Automatic Deployments
- **Git Push**: Push to `main` branch triggers automatic redeploy
- **Environment Variables**: Update in Render dashboard without redeploy
- **Rollback**: Use Render dashboard to rollback to previous deployment

### Manual Updates
1. Update code in GitHub
2. Push to main branch
3. Render automatically detects changes and redeploys
4. Monitor deployment logs

### Maintenance Tasks
- **Monitor Logs**: Check for errors and warnings
- **Update Dependencies**: Keep packages up to date
- **Clean Data**: Periodically clean old cache/log files
- **Monitor Usage**: Track memory and CPU usage

## 🆙 Scaling Options

### Free Tier Limits
- **Memory**: 512 MB RAM
- **CPU**: Shared CPU
- **Storage**: Ephemeral (data directory persists)
- **Bandwidth**: 100 GB/month

### Upgrade Options
- **Starter ($7/month)**: 512 MB RAM, dedicated CPU
- **Standard ($25/month)**: 2 GB RAM, more CPU
- **Pro ($85/month)**: 4 GB RAM, high performance

## 🔐 Security

### Best Practices
- **Environment Variables**: Never commit API keys to code
- **CORS**: Restrict origins to your frontend domains only
- **HTTPS**: Render provides automatic HTTPS
- **Rate Limiting**: Built-in rate limiting for API endpoints

### API Key Management
- **Render Dashboard**: Store all API keys as environment variables
- **Rotation**: Regularly rotate API keys
- **Monitoring**: Monitor API usage and costs

## 📞 Support

### Render Support
- **Documentation**: [render.com/docs](https://render.com/docs)
- **Community**: [community.render.com](https://community.render.com)
- **Support**: Email support for paid plans

### GlyphMind Support
- **Issues**: Create GitHub issues for bugs
- **Documentation**: Check README.md and DEVELOPMENT.md
- **Logs**: Always include relevant logs when reporting issues

---

## ✅ Deployment Checklist

- [ ] Repository connected to Render
- [ ] Root directory set to `backend`
- [ ] Build command: `pip install -r requirements.txt`
- [ ] Start command: `python render_start.py`
- [ ] Environment variables configured
- [ ] Service deployed successfully
- [ ] Health check endpoint responding
- [ ] Chat endpoint working
- [ ] Frontend can connect to backend
- [ ] Logs are accessible and readable
- [ ] API keys working (if configured)

**🎉 Your GlyphMind AI backend is now running on Render.com!**
