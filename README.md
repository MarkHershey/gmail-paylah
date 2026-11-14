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

To download only transaction-related emails from Grab, use:

```bash
python main.py --receipts-only
```

This optional Gmail subject filter includes e-receipts, merchant purchases, and
cancellation fees. The default still exports every message from the sender.
Existing cached emails are retained and remain available to the parser.

The default outputs are located in the `output` folder.

Grab transaction exports include `txn_currency` (`SGD`, `MYR`, or `THB`).
`txn_amount` is the original receipt amount in that currency; no exchange-rate
conversion is applied. Tips and cancellation fees are separate transactions.
GrabPay and PayLater merchant purchases are included; PayLater bill settlements
are excluded to avoid counting the same purchases twice.
The Grab analysis script reports SGD ride and food spending, includes related
tips and cancellation fees without counting extra trips or orders, and reports
how many foreign-currency transactions it excludes. Merchant payments and GrabMart
purchases remain in the exports and are outside these ride/food charts.

Gmail listings use 500 messages per page. Temporary quota and server errors have
up to seven retries with exponential backoff. Individual malformed or deleted
messages are reported by ID after the remaining messages have been exported;
authentication, exhausted quota/server errors, and storage failures stop the run.
Any export failure prevents transaction report generation.

Rerunning the script reuses valid cached messages and repairs incomplete exports.
Cache and report files are replaced only after a successful write. A receipt
that cannot be parsed stops report generation with an error rather than adding
a zero amount or replacing reports with incomplete results.

### Step 4: Further analysis

You can further analyze the CSV/JSON files using Excel, Google Sheets, or write your own Python scripts.

Example code to analyze the Grab transactions:

```bash
python analyze_grab.py
```

Spending averages use the last N completed calendar months for both costs and
transaction counts, excluding the current month. Months with no transactions
count as zero; insufficient history produces a warning rather than an average.

Example code to analyze the PayLah! transactions:

```bash
python analyze_paylah.py
```

## Tests

Run the offline regression tests with the project environment activated:

```bash
python -m unittest discover -v
```

The tests simulate Gmail responses and retry delays, so they do not contact Gmail
or consume API quota.

## Disclaimer

Understand the script before running it. Use at your own risk.
