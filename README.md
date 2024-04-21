# gmail-paylah

This is a Python utility to

1. Export emails from **Gmail**
2. Parse emails from
    - **DBS PayLah!** (Singapore)
    - **Fave** (Singapore)
    - **Grab** (Singapore)
3. Extract the transaction details and save to a CSV/JSON file.

## Assumptions

1. Your DBS PayLah! / Fave / Grab account is linked to your Gmail account. Usually, you will receive an email receipt for each transaction.
2. You are able to enable the Gmail API on your Google account. (Instructions below)

## Usage

### Step 1: Enable Gmail API on your Google account

Follow the instructions [here](https://developers.google.com/gmail/api/quickstart/python#enable_the_api) to enable the Gmail API on your Google account. Follow the steps, including:

-   Enable the API
-   Configure the OAuth consent screen
-   Authorize credentials for a desktop application
-   Download the credentials file and save it as `credentials.json` at the root of this project.

During the steps above, you may need to fill in the scopes for the Gmail API. Due to the nature of the project, the script only requires read-only access to your Gmail account. The only scope required by this project is:

| Scope                                            | Description                                                |
| ------------------------------------------------ | ---------------------------------------------------------- |
| `https://www.googleapis.com/auth/gmail.readonly` | Read all resources and their metadata—no write operations. |

### Step 2: Setup Python environment for this project

```bash
# Create a virtual environment
python3 -m venv venv
# Activate the virtual environment
source venv/bin/activate
# Install dependencies
pip install -r requirements.txt
```

### Step 3: Run the script

```bash
python main.py
```

The default outputs are located in the `output` folder.

### Step 4: Further analysis

You can further analyze the CSV/JSON files using Excel, Google Sheets, or write your own Python scripts.

Example code to analyze the Grab transactions:

```bash
python analyze_grab.py
```

Example code to analyze the PayLah! transactions:

```bash
python analyze_paylah.py
```

## Disclaimer

Understand the script before running it. Use at your own risk.
