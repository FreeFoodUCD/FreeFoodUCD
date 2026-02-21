# FreeFood UCD - External Services Setup Guide

This guide walks you through setting up all the external services required for FreeFood UCD.

---

## 📋 Required Services

1. **Instagram Account** - For monitoring society posts
2. **Twilio** - For WhatsApp notifications
3. **SendGrid** - For email notifications
4. **AWS S3 or MinIO** - For screenshot storage

---

## 1. 📸 Instagram Account Setup

### Create Monitoring Account

1. **Create a new Instagram account** (don't use your personal account)
   - Go to https://www.instagram.com/accounts/emailsignup/
   - Use a dedicated email (e.g., `freefood.monitor@gmail.com`)
   - Choose username like `freefood_ucd_monitor`
   - Use a strong password

2. **Age the account naturally** (2-3 weeks recommended)
   - Add profile picture
   - Write a bio: "Automated monitoring for FreeFood UCD"
   - Post 2-3 generic stories
   - Follow 10-15 UCD societies organically
   - Like a few posts daily

3. **Enable Two-Factor Authentication**
   - Go to Settings → Security → Two-Factor Authentication
   - Use authenticator app (not SMS)
   - Save backup codes securely

4. **Follow UCD Societies**
   ```
   Required societies to follow:
   - @ucdlawsoc
   - @ucdcommsoc
   - @ucddramasoc
   - @ucdcompsoc
   - @ucdsu
   - (Add more as needed)
   ```

### ⚠️ Important Instagram Guidelines

- **Don't scrape aggressively** - Use delays between requests
- **Respect rate limits** - Max 200 requests per hour
- **Monitor account health** - Check for warnings
- **Have a backup account** - In case of temporary blocks
- **Use residential IP** - Avoid datacenter IPs if possible

---

## 2. 📱 Twilio Setup (WhatsApp)

### Create Twilio Account

1. **Sign up for Twilio**
   - Go to https://www.twilio.com/try-twilio
   - Sign up with your email
   - Verify your phone number

2. **Get WhatsApp Sandbox** (for testing)
   - Go to Console → Messaging → Try it out → Send a WhatsApp message
   - Follow instructions to join sandbox
   - Note the sandbox number (e.g., `+14155238886`)

3. **Get API Credentials**
   - Go to Console → Account → API keys & tokens
   - Copy your **Account SID**
   - Copy your **Auth Token**
   - Keep these secure!

### For Production (WhatsApp Business API)

1. **Apply for WhatsApp Business API**
   - Go to Console → Messaging → WhatsApp → Get started
   - Fill out business information
   - Wait for approval (can take 1-2 weeks)

2. **Configure Message Templates**
   - Create pre-approved message templates
   - Example template:
     ```
     🍕 FREE FOOD ALERT
     Society: {{1}}
     📍 Location: {{2}}
     🕒 {{3}}
     📅 {{4}}
     ```

3. **Set up Webhook** (optional)
   - For delivery status updates
   - URL: `https://your-domain.com/api/v1/webhooks/twilio`

### Pricing

- **Sandbox**: Free (for testing)
- **WhatsApp Business API**: 
  - $0.005 per message (Ireland)
  - First 1,000 conversations/month free

### Add to .env

```bash
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_NUMBER=+14155238886  # Sandbox number
```

---

## 3. 📧 SendGrid Setup (Email)

### Create SendGrid Account

1. **Sign up for SendGrid**
   - Go to https://signup.sendgrid.com/
   - Sign up with your email
   - Verify your email address

2. **Create API Key**
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Name: `FreeFood UCD Production`
   - Permissions: **Full Access** (or Mail Send only)
   - Copy the API key (you won't see it again!)

3. **Verify Sender Identity**
   
   **Option A: Single Sender Verification** (easier, for testing)
   - Go to Settings → Sender Authentication → Single Sender Verification
   - Add email: `alerts@freefooducd.ie` (or your domain)
   - Verify via email link
   
   **Option B: Domain Authentication** (recommended for production)
   - Go to Settings → Sender Authentication → Domain Authentication
   - Add your domain (e.g., `freefooducd.ie`)
   - Add DNS records provided by SendGrid
   - Wait for verification (can take 24-48 hours)

4. **Set up Email Templates** (optional)
   - Go to Email API → Dynamic Templates
   - Create templates for:
     - Event notifications
     - Verification emails
     - Welcome emails

### Pricing

- **Free Tier**: 100 emails/day forever
- **Essentials**: $19.95/month for 50,000 emails
- **Pro**: $89.95/month for 100,000 emails

### Add to .env

```bash
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=alerts@freefooducd.ie
```

---

## 4. 🗄️ Storage Setup (Screenshots)

### Option A: MinIO (Local Development)

MinIO is already configured in `docker-compose.yml`!

1. **Start MinIO**
   ```bash
   cd backend
   docker-compose up -d minio
   ```

2. **Access MinIO Console**
   - URL: http://localhost:9001
   - Username: `minioadmin`
   - Password: `minioadmin`

3. **Create Bucket**
   - Click "Buckets" → "Create Bucket"
   - Name: `freefood-screenshots`
   - Region: `us-east-1`
   - Click "Create"

4. **Get Access Keys**
   - Already set in docker-compose:
     - Access Key: `minioadmin`
     - Secret Key: `minioadmin`

### Option B: AWS S3 (Production)

1. **Create AWS Account**
   - Go to https://aws.amazon.com/
   - Sign up (requires credit card)

2. **Create S3 Bucket**
   - Go to S3 Console
   - Click "Create bucket"
   - Name: `freefood-ucd-screenshots`
   - Region: `eu-west-1` (Ireland)
   - Block all public access: **Yes**
   - Enable versioning: Optional
   - Click "Create bucket"

3. **Create IAM User**
   - Go to IAM Console → Users → Add user
   - Username: `freefood-s3-uploader`
   - Access type: **Programmatic access**
   - Attach policy: `AmazonS3FullAccess` (or create custom policy)
   - Copy **Access Key ID** and **Secret Access Key**

4. **Set Lifecycle Policy** (optional, to auto-delete old screenshots)
   - Go to bucket → Management → Lifecycle rules
   - Create rule to delete objects after 30 days

### Pricing (AWS S3)

- **Storage**: $0.023 per GB/month (first 50 TB)
- **Requests**: $0.005 per 1,000 PUT requests
- **Free Tier**: 5 GB storage, 20,000 GET requests/month (first year)

### Add to .env

**For MinIO (local):**
```bash
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_S3_BUCKET=freefood-screenshots
AWS_REGION=us-east-1
AWS_ENDPOINT_URL=http://localhost:9000  # Add this for MinIO
```

**For AWS S3 (production):**
```bash
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_S3_BUCKET=freefood-ucd-screenshots
AWS_REGION=eu-west-1
```

---

## 5. 🔐 Environment Variables Summary

Create `backend/.env` with all credentials:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://freefood:password@localhost:5432/freefood
DATABASE_URL_SYNC=postgresql://freefood:password@localhost:5432/freefood

# Redis
REDIS_URL=redis://localhost:6379/0

# Instagram
INSTAGRAM_USERNAME=freefood_ucd_monitor
INSTAGRAM_PASSWORD=your_secure_password_here

# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_NUMBER=+14155238886

# SendGrid (Email)
SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SENDGRID_FROM_EMAIL=alerts@freefooducd.ie

# AWS S3 / MinIO
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_S3_BUCKET=freefood-screenshots
AWS_REGION=us-east-1
AWS_ENDPOINT_URL=http://localhost:9000  # Only for MinIO

# Application
SECRET_KEY=generate_with_openssl_rand_hex_32
ENVIRONMENT=development
LOG_LEVEL=INFO
API_V1_PREFIX=/api/v1

# CORS
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

---

## 6. 🧪 Testing Services

### Test Twilio WhatsApp

```python
# test_twilio.py
from twilio.rest import Client

account_sid = "ACxxxxx"
auth_token = "your_token"
client = Client(account_sid, auth_token)

message = client.messages.create(
    from_='whatsapp:+14155238886',
    to='whatsapp:+353871234567',  # Your number
    body='🍕 Test message from FreeFood UCD!'
)

print(f"Message sent: {message.sid}")
```

### Test SendGrid Email

```python
# test_sendgrid.py
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

message = Mail(
    from_email='alerts@freefooducd.ie',
    to_emails='your.email@example.com',
    subject='Test Email from FreeFood UCD',
    html_content='<strong>🍕 This is a test email!</strong>'
)

sg = SendGridAPIClient('SG.xxxxx')
response = sg.send(message)
print(f"Status: {response.status_code}")
```

### Test S3/MinIO Upload

```python
# test_s3.py
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9000',  # Remove for AWS
    aws_access_key_id='minioadmin',
    aws_secret_access_key='minioadmin'
)

# Upload test file
s3.put_object(
    Bucket='freefood-screenshots',
    Key='test.txt',
    Body=b'Test content'
)

print("Upload successful!")
```

---

## 7. 💰 Cost Estimation

### Monthly Costs (for ~1000 active users)

| Service | Usage | Cost |
|---------|-------|------|
| **Instagram** | Free account | $0 |
| **Twilio WhatsApp** | ~5,000 messages/month | $25 |
| **SendGrid** | ~10,000 emails/month | $0 (free tier) |
| **AWS S3** | ~5 GB storage, 10k requests | $1 |
| **Database (Heroku/Railway)** | Hobby tier | $5-7 |
| **Server (DigitalOcean)** | Basic droplet | $6 |
| **Total** | | **~$37/month** |

### Free Tier Options

- **Twilio**: First 1,000 conversations free
- **SendGrid**: 100 emails/day free forever
- **AWS S3**: 5 GB free for first year
- **Railway**: $5 free credit/month
- **Vercel**: Free for frontend hosting

---

## 8. 🔒 Security Best Practices

### API Keys

- ✅ Never commit `.env` to git
- ✅ Use different keys for dev/staging/production
- ✅ Rotate keys every 90 days
- ✅ Use environment variables, not hardcoded values
- ✅ Limit API key permissions to minimum required

### Instagram Account

- ✅ Use dedicated account, not personal
- ✅ Enable 2FA
- ✅ Monitor for unusual activity
- ✅ Have backup account ready
- ✅ Don't share credentials

### Rate Limiting

- ✅ Implement exponential backoff
- ✅ Cache responses when possible
- ✅ Monitor API usage
- ✅ Set up alerts for quota limits

---

## 9. 📊 Monitoring & Alerts

### Set Up Monitoring

1. **Twilio Console**
   - Monitor message delivery rates
   - Set up usage alerts

2. **SendGrid Dashboard**
   - Track email delivery rates
   - Monitor bounce/spam rates

3. **AWS CloudWatch** (if using S3)
   - Monitor storage usage
   - Set up billing alerts

4. **Application Logs**
   - Log all API calls
   - Track error rates
   - Monitor scraping success rates

---

## 10. ✅ Verification Checklist

Before going live, verify:

- [ ] Instagram account aged and following societies
- [ ] Twilio WhatsApp sandbox working
- [ ] SendGrid sender verified
- [ ] S3/MinIO bucket created and accessible
- [ ] All environment variables set
- [ ] Test messages sent successfully
- [ ] Rate limiting configured
- [ ] Error handling in place
- [ ] Monitoring set up
- [ ] Backup plan for service failures

---

## 🆘 Troubleshooting

### Twilio Issues

**Error: "Sandbox number not verified"**
- Join WhatsApp sandbox by sending code to Twilio number
- Check Console → Messaging → WhatsApp → Sandbox

**Error: "Authentication failed"**
- Verify Account SID and Auth Token
- Check for typos in .env file

### SendGrid Issues

**Error: "Sender not verified"**
- Complete sender verification in SendGrid console
- Check spam folder for verification email

**Error: "Daily sending limit exceeded"**
- Upgrade from free tier
- Or wait 24 hours for reset

### S3/MinIO Issues

**Error: "Access Denied"**
- Check bucket permissions
- Verify IAM user has S3 access
- For MinIO, check endpoint URL is correct

---

## 📚 Additional Resources

- [Twilio WhatsApp API Docs](https://www.twilio.com/docs/whatsapp)
- [SendGrid API Docs](https://docs.sendgrid.com/)
- [AWS S3 Documentation](https://docs.aws.amazon.com/s3/)
- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [Instagram Graph API](https://developers.facebook.com/docs/instagram-api/) (alternative to scraping)

---

**Need help?** Open an issue on GitHub or contact the maintainers.