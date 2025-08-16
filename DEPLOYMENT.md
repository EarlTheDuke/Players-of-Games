# Deployment Guide 🚀

## Streamlit Cloud Deployment

### Prerequisites
- GitHub account with access to this repository
- xAI API key (from [x.ai](https://x.ai))
- Anthropic API key (from [console.anthropic.com](https://console.anthropic.com))

### Step-by-Step Deployment

#### 1. Prepare Repository
Ensure your repository has:
- ✅ `streamlit_app.py` (entry point for Streamlit Cloud)
- ✅ `requirements.txt` (dependencies)
- ✅ `.streamlit/config.toml` (Streamlit configuration)
- ✅ All game files and modules

#### 2. Deploy to Streamlit Cloud

1. **Visit Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account

2. **Create New App**
   - Click "New app"
   - Select repository: `EarlTheDuke/Players-of-Games`
   - Branch: `master`
   - Main file path: `streamlit_app.py`

3. **Configure Secrets**
   - In app settings, go to "Secrets"
   - Add your API keys:
   ```toml
   GROK_API_KEY = "your_actual_grok_api_key_here"
   CLAUDE_API_KEY = "your_actual_claude_api_key_here"
   ```

4. **Deploy**
   - Click "Deploy!"
   - Wait for deployment to complete
   - Your app will be available at `https://players-of-games.streamlit.app`

#### 3. Test Deployment
- ✅ App loads without errors
- ✅ Game selection works
- ✅ AI vs AI games complete successfully
- ✅ Move reasoning displays correctly
- ✅ Error handling works gracefully

### Alternative Deployment Options

#### Heroku Deployment
```bash
# Install Heroku CLI
heroku create players-of-games-ai

# Set environment variables
heroku config:set GROK_API_KEY=your_key
heroku config:set CLAUDE_API_KEY=your_key

# Deploy
git push heroku master
```

#### Railway Deployment
```bash
# Install Railway CLI
railway login
railway init
railway add

# Set environment variables in Railway dashboard
# Deploy automatically on git push
```

### Environment Variables
Required for production deployment:
```
GROK_API_KEY=your_grok_api_key_from_x_ai
CLAUDE_API_KEY=your_claude_api_key_from_anthropic
```

### Monitoring & Maintenance
- **Performance**: Monitor response times and API usage
- **Costs**: Track API call costs for both services
- **Updates**: Deploy automatically on git push
- **Logs**: Monitor Streamlit Cloud logs for errors

### Troubleshooting

**Common Issues:**
1. **Import Errors**: Ensure all dependencies in `requirements.txt`
2. **API Failures**: Check API key validity and rate limits
3. **Memory Issues**: Streamlit Cloud has memory limits
4. **Timeout Issues**: Long-running games may timeout

**Solutions:**
- Use shorter commit messages for git
- Add retry logic for API calls
- Implement proper error handling
- Monitor resource usage

### Security Best Practices
- ✅ Never commit API keys to repository
- ✅ Use Streamlit Cloud secrets for production
- ✅ Implement rate limiting
- ✅ Add input validation
- ✅ Monitor for abuse

### Performance Optimization
- Cache game states when possible
- Implement connection pooling for API calls
- Use async operations where appropriate
- Minimize memory usage for long games

## Success Metrics
**Deployment is successful when:**
- App loads in under 10 seconds
- Games complete without errors
- API integrations work reliably
- Error handling is graceful
- Mobile experience is usable
