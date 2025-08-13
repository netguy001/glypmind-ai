# 🚀 GlyphMind AI Deployment Checklist

## Pre-Deployment Setup

### 1. Repository Setup
- [ ] Fork/clone the GlyphMind AI repository
- [ ] Ensure you have admin access to the repository
- [ ] Verify all files are in correct structure:
  - [ ] `/backend` folder with all backend code
  - [ ] `/frontend` folder with Gradio UI
  - [ ] `.github/workflows/deploy.yml` exists

### 2. Railway Setup (Backend)
- [ ] Create account at [Railway.app](https://railway.app)
- [ ] Generate Railway API token:
  - Go to Account Settings → Tokens
  - Create new token
  - Copy token value
- [ ] Create new Railway project
- [ ] Connect GitHub repository
- [ ] Set deployment source to `/backend` folder

### 3. Hugging Face Setup (Frontend)
- [ ] Create account at [Hugging Face](https://huggingface.co)
- [ ] Generate HF access token:
  - Go to Settings → Access Tokens
  - Create new token with write permissions
  - Copy token value
- [ ] Create new Space:
  - Choose "Gradio" as SDK
  - Set visibility (public/private)
  - Note the space name

### 4. GitHub Secrets Configuration
Go to your repository → Settings → Secrets and variables → Actions

Add these repository secrets:
- [ ] `RAILWAY_TOKEN`: Your Railway API token
- [ ] `HF_TOKEN`: Your Hugging Face access token
- [ ] `HF_USERNAME`: Your Hugging Face username
- [ ] `HF_SPACE_NAME`: Your Hugging Face space name
- [ ] `BACKEND_URL`: Will be set after Railway deployment

## Deployment Steps

### Step 1: Deploy Backend to Railway
- [ ] Push code to main branch (triggers GitHub Actions)
- [ ] Monitor GitHub Actions workflow
- [ ] Check Railway dashboard for successful deployment
- [ ] Test backend health endpoint: `https://your-backend.railway.app/health`
- [ ] Copy the Railway backend URL
- [ ] Update GitHub secret `BACKEND_URL` with Railway URL

### Step 2: Deploy Frontend to Hugging Face Spaces
- [ ] GitHub Actions should automatically deploy frontend
- [ ] Check HuggingFace Space for successful deployment
- [ ] Verify environment variable `BACKEND_URL` is set in HF Space
- [ ] Test frontend UI loads correctly
- [ ] Test chat functionality works

### Step 3: Verify Full Integration
- [ ] Frontend loads without errors
- [ ] Chat requests successfully reach backend
- [ ] Web search functionality works (if API keys configured)
- [ ] System status page shows all components

## Post-Deployment Configuration

### API Keys (Optional but Recommended)
Configure in Railway environment variables:
- [ ] `GOOGLE_SEARCH_API_KEY`: For web search functionality
- [ ] `GOOGLE_SEARCH_ENGINE_ID`: Custom search engine ID
- [ ] `YOUTUBE_API_KEY`: For YouTube search
- [ ] `OPENAI_API_KEY`: For OpenAI integration
- [ ] `ANTHROPIC_API_KEY`: For Claude integration

### Performance Optimization
- [ ] Monitor Railway resource usage
- [ ] Check HuggingFace Space performance
- [ ] Verify CORS settings allow frontend domain
- [ ] Test under load (multiple concurrent users)

## Testing Checklist

### Backend Testing
- [ ] Health endpoint: `GET /health`
- [ ] Status endpoint: `GET /status`
- [ ] Chat endpoint: `POST /chat`
- [ ] API documentation: `/docs`
- [ ] CORS headers present for frontend domain

### Frontend Testing
- [ ] UI loads without JavaScript errors
- [ ] Chat interface responds to messages
- [ ] Web search tab functions (if configured)
- [ ] System status tab shows backend info
- [ ] Mobile responsiveness

### Integration Testing
- [ ] End-to-end chat flow works
- [ ] Error handling displays user-friendly messages
- [ ] Backend connection errors handled gracefully
- [ ] All UI components function correctly

## Troubleshooting

### Common Issues

#### Backend Deployment Fails
- [ ] Check Railway build logs
- [ ] Verify `requirements.txt` has all dependencies
- [ ] Check `Procfile` syntax
- [ ] Verify Python version compatibility

#### Frontend Deployment Fails
- [ ] Check HuggingFace Space logs
- [ ] Verify `BACKEND_URL` environment variable set
- [ ] Check `requirements.txt` for frontend dependencies
- [ ] Verify `app.py` is the main entry point

#### Connection Issues
- [ ] Verify CORS settings in backend
- [ ] Check `BACKEND_URL` matches actual Railway URL
- [ ] Test backend health endpoint directly
- [ ] Check network connectivity

#### GitHub Actions Fails
- [ ] Verify all repository secrets are set correctly
- [ ] Check workflow permissions
- [ ] Review action logs for specific errors
- [ ] Ensure tokens have necessary permissions

## Maintenance

### Regular Tasks
- [ ] Monitor Railway usage and costs
- [ ] Check HuggingFace Space status
- [ ] Update dependencies regularly
- [ ] Monitor error logs
- [ ] Backup configuration and data

### Updates
- [ ] Test changes locally before pushing
- [ ] Use feature branches for development
- [ ] Monitor deployment after updates
- [ ] Have rollback plan ready

## Success Criteria

Deployment is successful when:
- [ ] ✅ Backend responds to health checks
- [ ] ✅ Frontend loads without errors  
- [ ] ✅ Chat functionality works end-to-end
- [ ] ✅ System status shows all components healthy
- [ ] ✅ No console errors in browser
- [ ] ✅ Mobile interface works correctly
- [ ] ✅ CI/CD pipeline runs successfully

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Review deployment logs in Railway and HuggingFace
3. Test components individually
4. Consult the [Development Guide](DEVELOPMENT.md)
5. Create an issue in the repository

---

**🎉 Congratulations!** Once all items are checked, your GlyphMind AI should be fully deployed and operational!
