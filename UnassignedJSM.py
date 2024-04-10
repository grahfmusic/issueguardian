#!/usr/bin/python3

import datetime
import requests
from requests.auth import HTTPBasicAuth
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import configparser
import argparse
import logging
import sys
import os

class ApplicationInfo:
    @staticmethod
    def display_app_info():
        print("\n" + "\u2550" * 51)
        print("AUJA (Automatic Unassigned Jira Announcer)")
        print("Version 1.0.0")
        print("Developed by Dean Thomson")
        print("FOR INTERNAL USE ONLY")
        print("Copyright 2024 © CCA Software Pty Ltd. All Rights Reserved")
        print("\u2550" * 51 + "\n")

class ConfigValidator:
    @staticmethod
    def validate(config):
        logger = logging.getLogger('UnassignedJiraReportLogger')
        logger.info("Configuration Validating")
        required_settings = {
            'jira': ['server', 'jira_ticket_base_url', 'username', 'password'],
            'email': ['sender', 'smtp_server', 'smtp_port', 'smtp_username', 'smtp_password', 'recipient']
        }
        missing_settings = []
        for section, keys in required_settings.items():
            if section not in config:
                missing_settings.append(f"Missing section: {section}")
                continue
            for key in keys:
                if key not in config[section]:
                    missing_settings.append(f"Missing setting: {section}/{key}")
        if missing_settings:
            raise ValueError("Configuration validation failed:\n" + "\n".join(missing_settings))
        logger.info("Configuration Validated")

class JiraApi:
    def __init__(self, config):
        self.config = config

    def fetch_unassigned_issues(self):
        logger = logging.getLogger('UnassignedJiraReportLogger')
        logger.info("JIRA API Unassigned Ticket Request")
        api_url = f"{self.config['jira']['server']}/rest/api/2/search"
        # Include 'customfield_10002' in the fields parameter
        jql_query = 'assignee = EMPTY AND status != "Closed" AND status != "Resolved" AND status != "Done" ORDER BY created DESC'
        try:
            response = requests.get(api_url, auth=HTTPBasicAuth(self.config['jira']['username'], self.config['jira']['password']),
                                    params={'jql': jql_query, 'fields': 'key,summary,assignee,reporter,created,updated,priority,customfield_10002,description,status'})
            response.raise_for_status()
            issues = response.json()['issues']
            logger.info(f"Fetched {len(issues)} unassigned issues")
            return issues
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            raise
        except Exception as err:
            logger.error(f"An error occurred: {err}")
            raise

        
class EmailReport:
    def __init__(self, config, recipient_email, cc_emails=[]):
        self.config = config
        self.recipient_email = recipient_email
        self.cc_emails = cc_emails
        self.current_date = datetime.datetime.now().strftime('%Y-%m-%d')

    def generate_email_body(self, issues):
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Consolas, 'Ubuntu', Geneva, Verdana, sans-serif; }}
                .hrdotted {{ border-top: 2px dotted darkblue; margin-left: auto; margin-right: auto; margin-top: 20px; margin-bottom: 20px; }}
                .hrdotted2 {{ border-top: 4px dashed blue; margin-left: auto; margin-right: auto; margin-top: 20px; margin-bottom: 20px; }}
                .hrdotted3 {{ border-top: 2px dotted #1e3f5a; margin-left: auto; margin-right: auto; margin-top: 20px; margin-bottom: 20px; width: 40%; }}
                .hrdotteds {{ border-top: 2px dotted darkblue; margin-left: auto; margin-right: auto; margin-bottom: 20px; }}
                .hrdottede {{ border-top: 2px dotted darkblue; margin-left: auto; margin-right: auto; margin-top: 20px; }}
                .issue {{ margin-bottom: 30px; padding: 15px; border-left: 5px solid #007BFF; background-color: #f9f9f9; }}
                .issue-header {{ font-weight: bold; color: #1e3f5a;font-size: 20px; margin-bottom: 10px; }}
                .issue-header a {{ color: #007BFF; text-decoration: none; font-weight: bold; }}
                .issue-detail, .description {{ margin-left: 20px; }}
                .priority {{ padding: 3px; border-radius: 4px; color: #fff; font-weight: normal; }}
                .High, .Highest {{ background-color: #DC3545; }}
                .Medium {{ background-color: #FFC107; }}
                .Low, .Lowest {{ background-color: #28A745; }}
                .description-text {{ margin-top: 10px; padding-left: 20px; color: #1e3f5a; /* Additional indentation for the description content */ }}
                .label {{ font-weight: bold; padding-right: 30px }}
                .header-logo {{ text-align: center; margin-bottom: 20px; }}
                .header-text {{ text-align: center; font-size: 16px; margin-top: 0px; color: #001F3F; font-weight: bold; text-transform: uppercase; }}
            </style>
        </head>
        <body>
            <div class="header-logo">
                <img src="https://www.ccasoftware.com/wp-content/uploads/CCA-software-logo.svg" alt="CCA Software Logo" style="max-width: 90px;">
                <div class="header-text">Software</div>
            </div>
            <div class="hrdotted3"></div>
            <h2 style align="center">Unassigned JIRA Issues Report - {self.current_date}</h2>
            <div class="hrdotted3"></div>
            <br><br><br>
        """

        for issue in issues:
            issue_url = f"{self.config['jira']['jira_ticket_base_url']}/{issue['key']}"
            priority_class = issue['fields']['priority']['name'].capitalize()
            
            organization_field = issue['fields'].get('customfield_10002', 'N/A')
            organization_names = ', '.join(org.get('name', 'Unknown') for org in organization_field) if isinstance(organization_field, list) else organization_field

            description = issue['fields'].get('description', 'No description provided').replace('\n', '<br>')

            html_body += f"""
                <div class="issue">
                    <div class="hrdotteds"></div>
                    <div class="issue-header">
                        <a href="{issue_url}" target="_blank">{issue['key']}</a> - {issue['fields']['summary']}
                    </div><div class="hrdotted"></div>
                    <br>
                    <table class="issue-detail">
                        <tr>
                            <td class="label">Organization(s):</td>
                            <td style="padding-right: 10px;">{organization_names}</td>
                        </tr>
                        <tr>
                            <td class="label">Priority:</td>
                            <td style="padding-right: 10px;"><span class="priority {priority_class}">{issue['fields']['priority']['name']}</span></td>
                        </tr>
                        <tr>
                            <td class="label">Reporter:</td>
                            <td style="padding-right: 10px;">{issue['fields']['reporter']['displayName']}</td>
                        </tr>
                    </table><br>
                    <div class="hrdotted"></div>
                    <div class="description">

                        <span class="label">Description:</span>
                        <div class="description-text">{description}</div>
                    </div>
                    <div class="hrdottede"></div>
                </div>
            """
                
            
        html_body += "</body></html>"
        return html_body



    def send(self, issues):
        html_body = self.generate_email_body(issues)
        msg = MIMEMultipart('related')
        msg['Subject'] = f"Outstanding Unassigned CCA Software JIRA Tickets Report - Date: {self.current_date}"
        msg['From'] = self.config['email']['sender']
        msg['To'] = self.recipient_email
        if self.cc_emails:
            msg['Cc'] = ', '.join(self.cc_emails)
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP_SSL(self.config['email']['smtp_server'], int(self.config['email']['smtp_port'])) as server:
            server.login(self.config['email']['smtp_username'], self.config['email']['smtp_password'])
            server.send_message(msg)



def main():
    logging.basicConfig(level=logging.INFO, filename='unassigned-jira-report.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('UnassignedJiraReportLogger')

    abs_script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(abs_script_path)
    os.chdir(script_dir)

    ApplicationInfo.display_app_info()

    parser = argparse.ArgumentParser(description="Generate and send a JIRA report for unassigned issues.")
    parser.add_argument("--recipient", required=True, help="The email address of the recipient.")
    parser.add_argument("--cc", help="Email addresses for CC, separated by commas.", default="")
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read('config.ini')
    ConfigValidator.validate(config)

    jira_api = JiraApi(config)
    issues = jira_api.fetch_unassigned_issues()

    # Fetch the recipient from the configuration
    recipient_email = config['email']['recipient']
    cc_emails = args.cc.split(',') if args.cc else []
    email_report = EmailReport(config, recipient_email, cc_emails)
    email_report.send(issues)

if __name__ == "__main__":
    main()
