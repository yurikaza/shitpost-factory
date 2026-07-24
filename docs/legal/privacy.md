# Privacy Policy

**Last updated: July2026**

## Information We Collect

### Information You Provide

- **Account Information:** Brand names, content preferences, publishing schedules
- **API Credentials:** OAuth tokens for social media platforms (stored locally in `tokens/` directory)
- **Content Configuration:** YAML files defining content concepts and publishing settings

### Information Collected Automatically

- **Usage Data:** Pipeline execution logs, render times, publish status
- **Technical Data:** Error logs, API response codes

### Information from Third Parties

- **Social Media APIs:** Username, profile picture (via user.info.basic scope)
- **Content APIs:** Royalty-free footage metadata from Pexels

## How We Use Information

We use collected information to:

- Generate and publish content to your authorized social media accounts
- Maintain and improve the Service
- Debug errors and monitor pipeline performance
- Authenticate and authorize access to social media platforms

## Data Storage

- **Local Storage:** API tokens, configuration files, and logs are stored locally on your machine or GitHub Actions runner
- **No Cloud Database:** The Service does not use a cloud database. All data remains on your infrastructure
- **GitHub:** Source code and configuration are stored in your GitHub repository

## Data Sharing

We do not sell, trade, or share your personal information with third parties, except:

- **Social Media Platforms:** Content is published to your authorized accounts via official APIs
- **GitHub:** Source code and configuration are stored in your GitHub repository
- **Legal Requirements:** If required by law or to protect our rights

## Third-Party Services

The Service integrates with:

- **TikTok:** Content Posting API (video.publish, user.info.basic scopes)
- **Instagram:** Instagram Graph API (requires Facebook Business account)
- **YouTube:** YouTube Data API v3 (requires Google Cloud project)
- **Pexels:** Royalty-free footage API
- **Xiaomi MiMo:** AI language model for text generation

Each third-party service has its own privacy policy. We encourage you to review their policies.

## Data Security

We implement reasonable security measures to protect your data:

- API tokens are stored locally and never committed to version control
- OAuth tokens are refreshed automatically and expire after24 hours
- Refresh tokens expire after365 days
- All API communication uses HTTPS

## Your Rights

You have the right to:

- Access your data stored in the Service
- Delete your data by removing configuration files and tokens
- Revoke API access through social media platform settings
- Disable or delete your account at any time

## Data Retention

- API tokens: Retained until you delete them or they expire
- Configuration files: Retained until you delete them
- Logs: Retained for30 days, then automatically deleted
- Rendered videos: Deleted immediately after publishing (when using --cleanup flag)

## Children's Privacy

The Service is not intended for use by children under13. We do not knowingly collect personal information from children.

## Changes to Privacy Policy

We may update this Privacy Policy from time. We will notify you of any changes by posting the new Privacy Policy on this page.

## Contact

For questions about this Privacy Policy, contact: [your-email@example.com]
