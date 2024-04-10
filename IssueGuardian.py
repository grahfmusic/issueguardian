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

# Displays application information at startup
class ApplicationInfo:
    """
    A static class to display application information at startup.
    """

    @staticmethod
    def display_app_info():
        """
        Prints the application information.
        """
        # Print a horizontal line
        print("\n" + "\u2550" * 60)

        # Print application version and name
        print("IssueGuardian :: Version 1.0.0")
        print("Monitor and Safeguard Against Untracked or Unassigned Issues")

        # Print developer name
        print("Developed by Dean Thomson")

        # Print notice for internal use only
        print("\nFOR INTERNAL USE ONLY")

        # Print copyright information
        print("Copyright 2024 © CCA Software Pty Ltd. All Rights Reserved")

        # Print a horizontal line
        print("\u2550" * 60 + "\n")

class ConfigValidator:
    """
    A static class to validate the configuration.
    """

    @staticmethod
    def validate(config):
        """
        Validates the configuration by checking if the required settings are present.

        Args:
            config (dict): The configuration to be validated.

        Raises:
            ValueError: If the configuration is missing any required settings.

        """
        logger = logging.getLogger('UnassignedJiraReportLogger')
        logger.info("Configuration Validating")

        # Define the required settings
        required_settings = {
            'jira': ['server', 'jira_ticket_base_url', 'username', 'password'],
            'email': ['sender', 'smtp_server', 'smtp_port', 'smtp_username', 'smtp_password', 'recipient']
        }

        # Check if the required settings are present in the configuration
        missing_settings = []
        for section, keys in required_settings.items():
            if section not in config:
                missing_settings.append(f"Missing section: {section}")
                continue
            for key in keys:
                if key not in config[section]:
                    missing_settings.append(f"Missing setting: {section}/{key}")

        # Raise an exception if any required settings are missing
        if missing_settings:
            error_message = "Configuration validation failed:\n" + "\n".join(missing_settings)
            raise ValueError(error_message)

        # Log that the configuration has been validated
        logger.info("Configuration Validated")

class JiraApi:
    """
    Represents the Jira API class.

    Attributes:
        config (dict): The configuration settings.
    """

    def __init__(self, config):
        """
        Initializes a new instance of the JiraApi class.

        Args:
            config (dict): The configuration settings.
        """
        # The configuration settings
        self.config = config

    def fetch_unassigned_issues(self):
        """
        Fetches unassigned issues from the JIRA API.

        Returns:
            List: List of issues.

        Raises:
            requests.exceptions.HTTPError: If there is an HTTP error.
            Exception: If any other error occurs.
        """
        # Create a logger
        logger = logging.getLogger('UnassignedJiraReportLogger')
        
        # Log the API request
        logger.info("JIRA API Unassigned Ticket Request")
        
        # Construct the API URL
        api_url = f"{self.config['jira']['server']}/rest/api/2/search"
        
        # Construct the JQL query
        jql_query = ('assignee = EMPTY AND status != "Closed" AND '
                     'status != "Resolved" AND status != "Done" '
                     'ORDER BY created DESC')
        
        try:
            # Make the API request
            response = requests.get(api_url, 
                                    auth=HTTPBasicAuth(self.config['jira']['username'], 
                                                       self.config['jira']['password']),
                                    params={'jql': jql_query, 
                                            'fields': 'key,summary,assignee,reporter,created,updated,priority,customfield_10002,description,status'})
            
            # Raise an error if the response status is not OK
            response.raise_for_status()
            
            # Extract the issues from the response
            issues = response.json()['issues']
            
            # Log the number of issues fetched
            logger.info(f"Fetched {len(issues)} unassigned issues")
            
            # Return the issues
            return issues
        
        # Handle HTTP errors
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            raise
        
        # Handle other errors
        except Exception as err:
            logger.error(f"An error occurred: {err}")
            raise

        
class EmailReport:
    def __init__(self, config, recipient_email, cc_emails=[]):
        """
        Initializes an EmailReport object.

        Args:
            config (dict): The configuration for the email report.
            recipient_email (str): The email address of the recipient.
            cc_emails (List[str], optional): The email addresses for CC. Defaults to an empty list.
        """
        # Store the configuration, recipient email, and CC email addresses
        self.config = config
        self.recipient_email = recipient_email
        self.cc_emails = cc_emails
        
        # Get the current date in the format 'YYYY-MM-DD'
        self.current_date = datetime.datetime.now().strftime('%Y-%m-%d')
        
        """
        The current_date attribute stores the date when the email report is generated.
        It is formatted as 'YYYY-MM-DD'.
        """

    def generate_email_body(self, issues):
        """
        Generate the HTML body for an email containing information about the provided JIRA issues.
        Args:
            self: The instance of the class.
            issues (list): A list of dictionaries containing information about JIRA issues.
        Returns:
            str: The complete HTML body for the email.
        """
        # HTML structure for the email body
        html_body = f"""
        <html>
        <!-- Begin of email body -->
        <head>
            <style>
                /* CSS styles for the email body */
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
            <!-- Logo and report header -->
            <div class="header-logo">
                <img src="https://www.ccasoftware.com/wp-content/uploads/CCA-software-logo.svg" alt="CCA Software Logo" style="max-width: 90px;">
                <div class="header-text">Software</div>
            </div>
            <div class="hrdotted3"></div>
            <h2 style align="center">Unassigned JIRA Issues Report - {self.current_date}</h2>
            <div class="hrdotted3"></div>
            <br><br><br>
        <!-- End of email body -->
        """

        # Loop over each issue and generate the HTML for the email body
        for issue in issues:
            # Construct the issue URL
            issue_url = (f"{self.config['jira']['jira_ticket_base_url']}/"
                         f"{issue['key']}")
            
            # Determine the priority class for the issue
            priority_class = issue['fields']['priority']['name'].capitalize()
            
            # Extract the organization(s) from the custom field
            organization_field = issue['fields'].get('customfield_10002', 'N/A')
            
            # Convert the organization field into a comma-separated string
            organization_names = (', '.join(org.get('name', 'Unknown') 
                                            for org in organization_field) 
                                  if isinstance(organization_field, list) 
                                  else organization_field)
            
            # Process the description, replacing newlines with HTML line breaks
            description = (issue['fields'].get('description', 'No description provided')
                           .replace('\n', '<br>'))
            
            # The following lines of code generate the HTML for each issue in the email body
            # Generate the HTML for each issue in the email body
            html_body += f"""
                <!-- Start of issue -->
                <div class="issue">
                    <!-- Horizontal line -->
                    <div class="hrdotteds"></div>
                    <!-- Issue header -->
                    <div class="issue-header">
                        <!-- Issue link -->
                        <a href="{issue_url}" target="_blank">{issue['key']}</a> - {issue['fields']['summary']}
                    </div>
                    <!-- Horizontal line -->
                    <div class="hrdotted"></div>
                    <br>
                    <!-- Issue details table -->
                    <table class="issue-detail">
                        <!-- Organization(s) -->
                        <tr>
                            <td class="label">Organization(s):</td>
                            <td style="padding-right: 10px;">{organization_names}</td>
                        </tr>
                        <!-- Priority -->
                        <tr>
                            <td class="label">Priority:</td>
                            <td style="padding-right: 10px;">
                                <!-- Priority class and name -->
                                <span class="priority {priority_class}">
                                    {issue['fields']['priority']['name']}
                                </span>
                            </td>
                        </tr>
                        <!-- Reporter -->
                        <tr>
                            <td class="label">Reporter:</td>
                            <td style="padding-right: 10px;">
                                {issue['fields']['reporter']['displayName']}
                            </td>
                        </tr>
                    </table>
                    <!-- Horizontal line -->
                    <div class="hrdotted"></div>
                    <br>
                    <!-- Issue description -->
                    <div class="description">
                        <!-- Description label -->
                        <span class="label">Description:</span>
                        <!-- Description text -->
                        <div class="description-text">{description}</div>
                    </div>
                    <!-- Horizontal line -->
                    <div class="hrdottede"></div>
                </div>
                <!-- End of issue -->
            """ 
                    
        html_body += "</body></html>"
        return html_body
    

    def send(self, issues):
        """
        Sends an email with the provided issues as HTML body.

        Args:
            issues (List[Dict]): List of JIRA issues.
        """
        # Generate the HTML body for the email
        html_body = self.generate_email_body(issues)

        # Create a new email message
        msg = MIMEMultipart('related')

        # Set the email subject
        msg['Subject'] = f"Outstanding Unassigned CCA Software JIRA Tickets Report - Date: {self.current_date}"

        # Set the sender and recipient email addresses
        msg['From'] = self.config['email']['sender']
        msg['To'] = self.recipient_email

        # Add CC email addresses if provided
        if self.cc_emails:
            msg['Cc'] = ', '.join(self.cc_emails)

        # Add the HTML body to the email message
        msg.attach(MIMEText(html_body, 'html'))

        # Connect to the SMTP server and send the email
        with smtplib.SMTP_SSL(self.config['email']['smtp_server'], 
                              int(self.config['email']['smtp_port'])) as server:
            # Login to the SMTP server
            server.login(self.config['email']['smtp_username'], 
                         self.config['email']['smtp_password'])

            # Send the email message
            server.send_message(msg)



def main():
    """
    Main function that generates and sends a JIRA report for unassigned issues.
    """

    # Configure logging
    logging.basicConfig(level=logging.INFO, filename='issueguardian.log', filemode='a', format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('UnassignedJiraReportLogger')

    # Change to the directory where the script is located
    abs_script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(abs_script_path)
    os.chdir(script_dir)

    # Display application information
    ApplicationInfo.display_app_info()

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Generate and send a JIRA report for unassigned issues.")
    parser.add_argument("--recipient", required=True, help="The email address of the recipient.")
    parser.add_argument("--cc", help="Email addresses for CC, separated by commas.", default="")
    args = parser.parse_args()

    # Read configuration from config.ini
    config = configparser.ConfigParser()
    config.read('config.ini')

    # Validate configuration
    ConfigValidator.validate(config)

    # Fetch unassigned issues from JIRA
    jira_api = JiraApi(config)
    issues = jira_api.fetch_unassigned_issues()

    # Fetch the recipient and CC email addresses from the configuration
    recipient_email = config['email']['recipient']
    cc_emails = args.cc.split(',') if args.cc else []

    # Create an email report
    email_report = EmailReport(config, recipient_email, cc_emails)

    # Send the email report
    email_report.send(issues)


if __name__ == "__main__":
    main()
