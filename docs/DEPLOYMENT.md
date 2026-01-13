# Deploying to Streamlit Cloud

This guide will walk you through deploying the AI Real Estate Assistant to Streamlit Cloud.

## Prerequisites

1. A GitHub account
2. API keys for at least one LLM provider (OpenAI, Anthropic, or Google)
3. A Streamlit Cloud account (free tier available at [share.streamlit.io](https://share.streamlit.io))

## Step 1: Prepare Your Repository

The repository is already configured with all necessary files:
- ✅ `requirements.txt` - Python dependencies
- ✅ `packages.txt` - System dependencies
- ✅ `.streamlit/config.toml` - App configuration
- ✅ `.streamlit/secrets.toml.example` - Secrets template
- ✅ `app_modern.py` - Main application file

## Step 2: Push to GitHub

Make sure your branch is pushed to GitHub:

```bash
git push -u origin <your-branch>
```

## Step 3: Deploy to Streamlit Cloud

1. **Go to Streamlit Cloud**
   - Visit [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account

2. **Create New App**
   - Click "New app" button
   - Select your repository: `AleksNeStu/ai-real-estate-assistant`
   - Select branch: the branch you want to deploy (for example: `main`)
   - Main file path: `app_modern.py`
   - App URL: Choose a custom URL (optional)

3. **Configure Secrets**
   - Click "Advanced settings" before deploying
   - Or go to App settings → Secrets after deployment
   - Add your API keys in TOML format:

```toml
# Required: At least one LLM provider API key
OPENAI_API_KEY = "sk-..."

# Optional: Other LLM providers
ANTHROPIC_API_KEY = "sk-ant-..."
GOOGLE_API_KEY = "..."

# Optional: For local Ollama (if using a public Ollama endpoint)
# OLLAMA_BASE_URL = "http://your-ollama-server:11434"

# Optional: Email notifications
# SMTP_USERNAME = "your.email@gmail.com"
# SMTP_PASSWORD = "your-app-specific-password"
# SMTP_PROVIDER = "gmail"
```

4. **Deploy**
   - Click "Deploy!"
   - Wait for the deployment to complete (usually 2-5 minutes)

## Step 4: Initial Setup

Once deployed:

1. **Load Data**
   - The app will use sample data from `data/sample_properties.csv`
   - You can upload your own CSV file via the sidebar

2. **Select Model Provider**
   - In the sidebar, select your LLM provider (OpenAI, Anthropic, Google, or Ollama)
   - The app will use the API key from secrets

3. **Initialize Vector Store**
   - Click "Load Data" in the sidebar
   - The vector store will be created automatically
   - This may take 30-60 seconds on first load

## Step 5: Configure Notifications (Optional)

If you want to use the notification system:

1. Navigate to the **Notifications** tab
2. Enter your email address
3. Configure email service:
   - Select provider (Gmail/Outlook/Custom)
   - Enter credentials
   - For Gmail: Use an [app-specific password](https://support.google.com/accounts/answer/185833)
4. Set notification preferences
5. Send a test email to verify

## Troubleshooting

### Deployment Fails

**Issue:** Dependencies fail to install
- **Solution:** Check the deployment logs for specific errors
- Some packages may need additional system dependencies
- Try reducing the number of LangChain providers if memory is limited

**Issue:** ChromaDB errors
- **Solution:** ChromaDB requires build-essential (already in packages.txt)
- If issues persist, check Streamlit Cloud's system requirements

### App Doesn't Load

**Issue:** "API key not found" error
- **Solution:** Ensure you've added API keys in the Secrets section
- Keys should be in TOML format without quotes around the key names

**Issue:** "Module not found" errors
- **Solution:** Check that all imports in `app_modern.py` match installed packages
- Verify `requirements.txt` includes all necessary dependencies

### Performance Issues

**Issue:** App is slow or times out
- **Solution:** Free tier has resource limitations
- Consider upgrading to Streamlit Cloud Pro for better performance
- Reduce vector store size by using fewer sample properties

### Email Notifications Don't Work

**Issue:** Test email fails to send
- **Solution:**
  - For Gmail: Use an app-specific password
  - For Outlook: Ensure SMTP is enabled
  - Check firewall/network restrictions
  - Verify credentials are correct

## App Features Available

Your deployed app includes:
- Multi-provider LLM support (OpenAI, Anthropic, Google, Ollama)
- ChromaDB vector store with persistent storage
- Hybrid agent (retrieval + tools) with reranking
- Market insights and analytics
- Visual dashboards and charts
- Export (CSV/JSON/Markdown/PDF)
- Notification preferences and email alerts

## Resource Limits (Free Tier)

Streamlit Cloud free tier has these limits:
- 1 GB memory
- 1 CPU core
- Public apps only
- Sleep after 7 days of inactivity

For production use or private apps, consider upgrading to Pro.

## Updating Your Deployment

To update the deployed app:

1. Make changes in your local repository
2. Commit and push to the deployment branch:
   ```bash
   git add .
   git commit -m "Your update message"
   git push
   ```
3. Streamlit Cloud will automatically detect changes and redeploy
4. Reboot app from Streamlit Cloud dashboard if needed

## Security Best Practices

1. ✅ Never commit API keys to the repository
2. ✅ Use Streamlit Cloud's secrets management
3. ✅ `.gitignore` is configured to exclude sensitive files
4. ✅ Email credentials are stored in session state only
5. ⚠️ Consider making the app private if handling sensitive data

## Support & Documentation

- Streamlit Cloud Docs: https://docs.streamlit.io/streamlit-community-cloud
- Streamlit Forum: https://discuss.streamlit.io/
- GitHub Issues: Report issues in your repository

## Post-Deployment Checklist

- [ ] App deploys successfully
- [ ] Data loads correctly
- [ ] Can search for properties
- [ ] Chat functionality works
- [ ] Market insights display properly
- [ ] Export functionality works
- [ ] Notifications can be configured (if using)
- [ ] All tabs are accessible
- [ ] No errors in browser console

Enjoy your deployed AI Real Estate Assistant!
