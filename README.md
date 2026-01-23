# Beancount PayPal Importer

`beancount-paypal-ng` provides a beangulp-compatible Importer for converting CSV
exports of PayPal into the beancount format.

**Note:** This project was forked from
[nils-werner/beancount-paypal](https://github.com/nils-werner/beancount-paypal)
but is now independent. The reason for the fork was that contributing changes
to the original project was too slow for my personal taste. If at all possible,
I intend to incorporate the original's future changes. At the time of writing
this fork fixes several bugs and adds features that are missing in the
original.

## Installation

### Using uv (recommended)

```sh
uv add git+https://github.com/omarkohl/beancount-paypal-ng.git
```

### Using pip

```sh
pip install git+https://github.com/omarkohl/beancount-paypal-ng.git
```

### For development

```sh
git clone https://github.com/omarkohl/beancount-paypal-ng.git
cd beancount-paypal-ng
uv sync
```

#### Code quality

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```sh
uv run ruff check .     # lint
uv run ruff format .    # format
```

## Usage

### Basic usage

Configure `PaypalImporter` in your beangulp importer script, and download your PayPal statements as CSV.

In PayPal you can customize the report fields. If you enable `Transaction Details > Balance`, the
beancount output will be finalized with a `balance` assertion.


```python
from beancount_paypal import PaypalImporter

CONFIG = [
    PaypalImporter(
        'my-paypal-account@gmail.com',
        'Assets:US:PayPal',
        'Assets:US:Checking',
        'Expenses:Financial:Commission',
        default_expense_account='Expenses:TODO',  # optional
        default_income_account='Income:TODO',  # optional
    )
]
```

Use with beangulp:

```bash
beangulp extract CONFIG paypal_export.csv
```

### Advanced usage

If you enable additional report fields you can map them into transaction metadata using the
`metadata_map` keyword argument:

```python
from beancount_paypal import PaypalImporter, lang

CONFIG = [
    PaypalImporter(
        'my-paypal-account@gmail.com',
        'Assets:US:PayPal',
        'Assets:US:Checking',
        'Expenses:Financial:Commission',
        language=lang.de(),
        metadata_map={
            "uuid": "Transaktionscode",
            "sender": "Absender E-Mail-Adresse",
            "recipient": "Empfänger E-Mail-Adresse"
        }
    )
]
```

Use with beangulp for import workflows:

```bash
beangulp identify CONFIG paypal_export.csv
beangulp extract CONFIG paypal_export.csv > new_entries.beancount
beangulp file CONFIG paypal_export.csv
```
