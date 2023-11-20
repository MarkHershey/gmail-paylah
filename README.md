# gmail-paylah

This is a Python utility to export emails from Gmail, parse emails from DBS PayLah! (Singapore) / Fave (Singapore), and extract the transaction details. Extracted details are then written to a CSV/JSON file.

## Usage

### Step 1: Enable Gmail API on your Google account

Follow the instructions [here](https://developers.google.com/gmail/api/quickstart/python#enable_the_api) to enable the Gmail API on your Google account. Follow the steps, including:

-   Enable the API
-   Configure the OAuth consent screen
-   Authorize credentials for a desktop application
-   Download the credentials file and save it as `credentials.json` at the root of this project.

During the steps above, you may need to fill in the scopes for the Gmail API. The only scope required by this project is:

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
