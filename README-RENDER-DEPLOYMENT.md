# Render.com Deployment Guide

This guide explains how to deploy the Meeting Spot Backend to Render.com instead of Google Cloud Platform.

## Why Render.com?

- **Simpler deployment process** - No complex GCP setup required
- **Free tier available** - Perfect for development and testing
- **Automatic HTTPS** - SSL certificates handled automatically
- **GitHub integration** - Direct deployment from GitHub repositories
- **No Docker required** - Native Node.js support
- **Environment variables** - Easy to manage through dashboard

## Prerequisites

1. GitHub account with your code repository
2. Render.com account (free)
3. Node.js application with proper `package.json`

## Deployment Methods

### Method 1: Manual Deployment via Render Dashboard (Recommended)

1. **Sign up for Render.com**
   - Go to [render.com](https://render.com)
   - Sign up using your GitHub account

2. **Create a New Web Service**
   - Click "New +" in the dashboard
   - Select "Web Service"
   - Connect your GitHub repository

3. **Configure the Service**
   ```
   Name: meeting-spot-backend
   Language: Node
   Branch: main
   Build Command: npm ci && npm run build
   Start Command: npm start
   ```

4. **Set Environment Variables**
   - Add your environment variables in the Render dashboard
   - Required variables:
     - `NODE_ENV=production`
     - `DATABASE_URL=your_database_url`
     - `JWT_SECRET=your_jwt_secret`
     - Any other environment variables your app needs

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically build and deploy your app
   - You'll get a URL like `https://meeting-spot-backend.onrender.com`

### Method 2: Infrastructure as Code (render.yaml)

We've included a `render.yaml` file in your repository. This allows you to:

1. **Deploy using Render Blueprint**
   - Go to Render Dashboard
   - Click "New +" → "Blueprint"
   - Connect your repository
   - Render will read the `render.yaml` configuration

2. **Benefits of this approach**
   - Version controlled configuration
   - Reproducible deployments
   - Easy to manage multiple environments

### Method 3: GitHub Actions (Automated)

We've created a GitHub Actions workflow that will:

1. **Automatic deployment on push to main**
2. **Run tests before deployment**
3. **Build the application**
4. **Deploy to Render**

**Setup Required:**
1. Get your Render API key:
   - Go to Render Dashboard → Account Settings → API Keys
   - Create a new API key

2. Get your service ID:
   - After creating your service, find the service ID in the URL or settings

3. Add GitHub Secrets:
   - Go to your GitHub repository → Settings → Secrets and variables → Actions
   - Add these secrets:
     - `RENDER_API_KEY`: Your Render API key
     - `RENDER_SERVICE_ID`: Your service ID

## Database Setup

### Option 1: Render PostgreSQL (Recommended)

1. **Create a PostgreSQL database**
   - In Render dashboard, click "New +" → "PostgreSQL"
   - Choose a name (e.g., `meeting-spot-db`)
   - Select the free tier for development

2. **Get connection details**
   - Once created, go to the database details
   - Copy the "Internal Database URL" 
   - Add this as `DATABASE_URL` environment variable in your web service

### Option 2: External Database

You can continue using any external database service:
- ElephantSQL
- Heroku Postgres
- AWS RDS
- Google Cloud SQL

Just update the `DATABASE_URL` environment variable.

## Environment Variables

Set these in your Render service settings:

```bash
NODE_ENV=production
PORT=10000  # Render will set this automatically
DATABASE_URL=postgresql://username:password@host:port/database
JWT_SECRET=your-super-secret-jwt-key
FRONTEND_URL=https://your-frontend-domain.com
```

## Custom Domain (Optional)

1. **Add custom domain in Render**
   - Go to your service settings
   - Click "Custom Domains"
   - Add your domain

2. **Update DNS**
   - Point your domain to Render's servers
   - Render provides the exact DNS records needed

## Monitoring and Logs

- **Live logs**: Available in Render dashboard
- **Metrics**: CPU, memory usage, response times
- **Health checks**: Render monitors `/api/v1/health` endpoint
- **Alerts**: Email notifications for downtime

## Scaling

- **Free tier**: Limited resources, may sleep after inactivity
- **Paid tiers**: Always-on, more CPU/RAM, faster builds
- **Auto-scaling**: Available on higher tiers

## Troubleshooting

### Common Issues:

1. **Build fails**
   - Check `package.json` has all required dependencies
   - Ensure `build` script exists and works locally
   - Check Node.js version compatibility

2. **App won't start**
   - Verify `start` script points to correct file
   - Check environment variables are set
   - Review application logs in dashboard

3. **Database connection fails**
   - Verify `DATABASE_URL` is correct
   - Check database is running and accessible
   - Ensure database allows connections from Render IPs

4. **CORS issues**
   - Update CORS configuration to include your frontend domain
   - Check `FRONTEND_URL` environment variable

### Getting Help:

- **Render Documentation**: [render.com/docs](https://render.com/docs)
- **Render Community**: [community.render.com](https://community.render.com)
- **Support**: Available for paid plans

## Migration from GCP

If you're migrating from Google Cloud Platform:

1. **Export your data** from Cloud SQL or other GCP services
2. **Import to Render PostgreSQL** or your new database
3. **Update environment variables** to point to new services
4. **Test thoroughly** before switching DNS
5. **Update your frontend** to point to the new backend URL

## Cost Comparison

- **Render Free Tier**: $0/month (with limitations)
- **Render Starter**: $7/month (always-on, 512MB RAM)
- **GCP Cloud Run**: Pay-per-use (can be cost-effective for low traffic)

For most small to medium applications, Render is more predictable and often cheaper.

## Next Steps

1. ✅ Create Render account
2. ✅ Deploy your application
3. ✅ Set up database
4. ✅ Configure environment variables
5. ✅ Set up custom domain (optional)
6. ✅ Monitor application performance
7. ✅ Set up GitHub Actions for CI/CD (optional)

Your application should now be running on Render.com! 🚀 