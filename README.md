# IssueGuardian
**IssueGuardian** is a Python-based tool designed to monitor, identify, and alert on unassigned JIRA issues. It aims to ensure that all issues in a JIRA project receive prompt attention and are assigned appropriately, aiding teams in maintaining efficient workflows and project management practices.

<img style="display: block; margin-left: auto; margin-right: auto;" src="https://github.com/grahfmusic/issueguardian/blob/master/imgs/readme_header.png?raw=true" alt="readme header"></img>

## Features

- **Automatic Detection**: Scans the JIRA project for unassigned issues based on predefined criteria.
- **Email Alerts**: Sends detailed reports via email to specified recipients, including issue summaries, priorities, and direct links for quick navigation.
- **Customisable Configuration**: Allows configuration of JIRA credentials, project settings, and email details through an easy-to-use configuration file.
- **Logging**: Provides comprehensive logging of operations, facilitating easy troubleshooting and monitoring of the tool's activities.
## Getting Started
### Prerequisites
- Python 3.6 or higher
- `requests` library for making API requests
- Access to a JIRA project with API access enabled
- SMTP server credentials for sending email alerts
### Configuration
Edit the `config.ini` file to set up your JIRA access and email settings:
- `[jira]`: JIRA server URL, credentials, and project settings.
- `[email]`: SMTP server details and sender email address.
## Documentation
### Modules
- `ApplicationInfo`: Displays startup information and application details.
- `ConfigValidator`: Validates the provided configuration against required settings.
- `JiraApi`: Interfaces with the JIRA REST API to fetch unassigned issues.
- `EmailReport`: Generates and sends an email report based on the fetched issues.
### Functions
- `display_app_info()`: Prints application information.
- `validate(config)`: Validates the application's configuration.
- `fetch_unassigned_issues()`: Fetches unassigned issues from JIRA.
- `generate_email_body(issues)`: Generates the HTML body for the email report.
- `send(issues)`: Sends the email report to specified recipients.
