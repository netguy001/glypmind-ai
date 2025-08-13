# 🛠️ GlyphMind AI Development Guide

## 📁 Project Structure

The project is structured for split deployment:

### Backend (`/backend`)
- **Purpose**: Railway-hosted FastAPI API server
- **Entry Point**: `server/app.py`
- **Dependencies**: `requirements.txt`
- **Deployment**: `Procfile` and `railway.json`

### Frontend (`/frontend`)
- **Purpose**: Hugging Face Spaces-hosted Gradio UI
- **Entry Point**: `app.py`
- **Dependencies**: `requirements.txt`
- **Environment**: `BACKEND_URL` environment variable

## 🏃 Local Development

### Prerequisites
- Python 3.10+
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/glyphmind.git
   cd glyphmind
   ```

2. **Backend Development**
   ```bash
   cd backend
   pip install -r requirements.txt
   python run_local.py
   ```
   - Backend runs on: http://127.0.0.1:8000
   - API docs: http://127.0.0.1:8000/docs

3. **Frontend Development**
   ```bash
   cd frontend
   pip install -r requirements.txt
   python run_local.py
   ```
   - Frontend runs on: http://127.0.0.1:7860
   - Connects to local backend automatically

## 🚀 Deployment Process

### Automatic Deployment (Recommended)

1. **Setup Repository Secrets** (GitHub Settings → Secrets):
   ```
   RAILWAY_TOKEN=your_railway_token
   HF_TOKEN=your_huggingface_token
   HF_USERNAME=your_hf_username
   HF_SPACE_NAME=your_space_name
   BACKEND_URL=https://your-backend.railway.app
   ```

2. **Push to Main Branch**
   ```bash
   git push origin main
   ```
   - GitHub Actions automatically deploys both backend and frontend

### Manual Deployment

#### Backend to Railway
```bash
cd backend
railway login
railway up
```

#### Frontend to Hugging Face Spaces
1. Create a new Space on Hugging Face
2. Set Space SDK to "Gradio"
3. Upload all files from `/frontend` folder
4. Set environment variable: `BACKEND_URL=https://your-backend.railway.app`

## 🔧 Configuration

### Environment Variables

#### Backend
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: info)

#### Frontend
- `BACKEND_URL`: Backend API URL (required)

### API Keys

Backend API keys are configured in `backend/config/api_keys.json`:
```json
{
  "google_search_api_key": "your_key",
  "google_search_engine_id": "your_engine_id",
  "youtube_api_key": "your_key",
  "openai_api_key": "your_key",
  "anthropic_api_key": "your_key"
}
```

## 🧪 Testing

### Backend Testing
```bash
cd backend
python -c "from server.app import app; print('✅ Backend imports successfully')"

# Test API endpoints
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d '{"text": "Hello"}'
```

### Frontend Testing
```bash
cd frontend
python -c "from app import demo; print('✅ Frontend imports successfully')"
```

### Integration Testing
1. Start backend: `cd backend && python run_local.py`
2. Start frontend: `cd frontend && python run_local.py`
3. Open http://127.0.0.1:7860
4. Test chat functionality

## 📦 Adding New Features

### Backend Features
1. Add new endpoints in `backend/server/app.py`
2. Add new modules in appropriate `backend/` subdirectories
3. Update `backend/requirements.txt` if needed
4. Test locally before pushing

### Frontend Features
1. Modify `frontend/app.py`
2. Add new Gradio components
3. Update API calls to backend
4. Test locally before pushing

## 🐛 Troubleshooting

### Common Issues

#### Backend Won't Start
```bash
# Check Python version
python --version  # Should be 3.10+

# Check dependencies
cd backend
pip install -r requirements.txt

# Check port availability
netstat -an | grep :8000
```

#### Frontend Can't Connect to Backend
- Verify `BACKEND_URL` environment variable
- Check backend is running and accessible
- Check CORS settings in backend

#### Deployment Failures
- Check GitHub Actions logs
- Verify all repository secrets are set
- Check Railway and HuggingFace service status

### Debug Mode

Enable debug logging:
```bash
# Backend
LOG_LEVEL=debug python run_local.py

# Check logs
tail -f backend/logs/glyphmind.log
```

## 🔄 CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/deploy.yml`) handles:

1. **Backend Deployment**: Deploys to Railway on push to main
2. **Frontend Deployment**: Deploys to HuggingFace Spaces
3. **Notifications**: Success/failure status

### Pipeline Triggers
- Push to `main` branch
- Manual trigger via GitHub Actions UI

### Pipeline Secrets Required
- `RAILWAY_TOKEN`: Railway deployment token
- `HF_TOKEN`: HuggingFace access token
- `HF_USERNAME`: HuggingFace username
- `HF_SPACE_NAME`: HuggingFace Space name
- `BACKEND_URL`: Railway backend URL

## 📊 Monitoring

### Backend Monitoring
- Health endpoint: `/health`
- Status endpoint: `/status`
- API documentation: `/docs`
- Railway dashboard for metrics

### Frontend Monitoring
- HuggingFace Spaces logs
- User interaction analytics via Gradio

## 🎯 Performance Optimization

### Backend
- Use async/await for all I/O operations
- Implement proper caching strategies
- Monitor memory usage with Railway metrics
- Use connection pooling for databases

### Frontend
- Minimize API calls
- Implement client-side caching
- Use Gradio's built-in optimization features
- Optimize for mobile devices

## 🔐 Security

### Backend Security
- CORS properly configured for HF Spaces
- API rate limiting implemented
- Input validation on all endpoints
- Secure API key storage

### Frontend Security
- No sensitive data in client code
- Secure communication with backend
- User input sanitization

## 📈 Scaling

### Horizontal Scaling
- Railway: Increase replicas
- Backend: Stateless design supports scaling
- Database: Consider managed database services

### Vertical Scaling
- Railway: Upgrade plan for more resources
- Optimize code for lower memory usage
- Use efficient data structures

## 🤝 Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make changes and test locally
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Create Pull Request

### Code Standards
- Follow PEP 8 for Python code
- Add type hints to all functions
- Include docstrings for modules and functions
- Write tests for new features
- Update documentation as needed
