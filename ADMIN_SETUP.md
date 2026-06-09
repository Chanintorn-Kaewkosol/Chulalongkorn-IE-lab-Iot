# Admin Panel Setup Guide

## 🔐 Setting Up Secure Password

The admin password is stored in **Streamlit Secrets** (not in the code). This keeps it secure and hidden from GitHub.

### For Streamlit Cloud (Production):

1. Go to your app on Streamlit Cloud: https://share.streamlit.io/
2. Click on your app → **Settings** (⚙️)
3. Click on **Secrets**
4. Add this:
   ```toml
   admin_password = "your_secure_password_here"
   ```
5. Click **Save**
6. Your app will restart with the new password

### For Local Development:

1. Create a file: `.streamlit/secrets.toml`
2. Add this content:
   ```toml
   admin_password = "your_secure_password_here"
   ```
3. Save the file (it's already in .gitignore, so it won't be committed)

## 🔑 Accessing Admin Panel

1. **Public Dashboard**: https://chulalongkorn-lab-iot.streamlit.app/
2. **Admin Panel**: https://chulalongkorn-lab-iot.streamlit.app/?admin

## 🛡️ Security Notes

- ✅ Password is stored in Streamlit Secrets (NOT in code)
- ✅ `.gitignore` prevents secrets from being committed to GitHub
- ✅ Session-based authentication (stays logged in during session)
- ⚠️ Change the default password immediately after deployment!

## 📝 Admin Panel Features

- **View All Data**: See all records with CSV export
- **Add Record**: Manually add new data
- **Edit Record**: Modify existing records
- **Delete**: Remove single records or clear entire database
