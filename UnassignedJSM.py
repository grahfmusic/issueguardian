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
        print("Version 1.1.0")
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
        jql_query = 'assignee = EMPTY AND status != "Closed" AND status != "Resolved" AND status != "Done" ORDER BY created DESC'
        try:
            response = requests.get(api_url, auth=HTTPBasicAuth(self.config['jira']['username'], self.config['jira']['password']),
                                    params={'jql': jql_query, 'fields': 'key,summary,assignee,reporter,created,updated,priority,status'})
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
        html_body = "<html><head></head><body>"
        html_body += "<h1>Unassigned JIRA Issues Report</h1>"
        if issues:
            html_body += "<ul>"
            for issue in issues:
                html_body += f"<li><b>{issue['key']}</b>: {issue['fields']['summary']}</li>"
            html_body += "</ul>"
        else:
            html_body += "<p>No unassigned issues found.</p>"
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
