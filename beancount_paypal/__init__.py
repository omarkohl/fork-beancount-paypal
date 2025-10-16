from beancount.core.number import D
from beancount.ingest import importer
from beancount.core import amount
from beancount.core import flags
from beancount.core import data

from datetime import timedelta
from contextlib import contextmanager

import csv

from . import lang


@contextmanager
def csv_open(filename):
    with open(filename, newline="", encoding="utf-8-sig") as f:
        yield csv.DictReader(f, quotechar='"')


class PaypalImporter(importer.ImporterProtocol):
    def __init__(
        self,
        email_address,
        account,
        checking_account,
        commission_account,
        language=None,
        metadata_map=None,
    ):
        if language is None:
            language = lang.en()

        if metadata_map is None:
            metadata_map = language.metadata_map

        self.email_address = email_address
        self.account = account
        self.checking_account = checking_account
        self.commission_account = commission_account
        self.language = language
        self.metadata_map = metadata_map

    def file_account(self, _):
        return self.account

    def identify(self, filename):
        with csv_open(filename.name) as rows:
            try:
                row = next(rows)
                if not self.language.identify(list(next(rows).keys())):
                    return False

                row = self.language.normalize_keys(row)
                if not (
                    row["from"] == self.email_address or row["to"] == self.email_address
                ):
                    return False

                return True
            except StopIteration:
                return False

    def extract(self, filename):
        entries = []
        last_txn_id = None
        last_net = None
        last_currency = None
        last_was_currency = False

        with csv_open(filename.name) as rows:
            for index, row in enumerate(rows):
                metadata = {k: row[v] for k, v in self.metadata_map.items()}
                row = self.language.normalize_keys(row)

                row["date"] = self.language.parse_date(row["date"]).date()
                row["gross"] = self.language.decimal(row["gross"])
                row["fee"] = self.language.decimal(row["fee"])
                row["net"] = self.language.decimal(row["net"])

                if row["reference_txn_id"] != last_txn_id:
                    meta = data.new_metadata(filename.name, index, metadata)

                    txn = data.Transaction(
                        meta=meta,
                        date=row["date"],
                        flag=flags.FLAG_OKAY,
                        payee=row["name"],
                        narration=row.get("item_title")
                        or row.get("subject")
                        or row.get("note"),
                        tags=set(),
                        links=set(),
                        postings=[],
                    )

                if self.language.txn_from_checking(row["txn_type"]):
                    txn.postings.append(
                        data.Posting(
                            self.checking_account,
                            amount.Amount(-1 * D(row["gross"]), row["currency"]),
                            None,
                            None,
                            None,
                            None,
                        )
                    )

                    txn.postings.append(
                        data.Posting(
                            self.account,
                            amount.Amount(D(row["net"]), row["currency"]),
                            None,
                            None,
                            None,
                            None,
                        )
                    )

                elif self.language.txn_currency_conversion(row["txn_type"]):
                    if last_was_currency:
                        txn.postings.append(
                            data.Posting(
                                self.account,
                                amount.Amount(D(last_net), last_currency),
                                None,
                                None,
                                None,
                                None,
                            )
                        )
                        txn.postings.append(
                            data.Posting(
                                self.account,
                                amount.Amount(D(row["net"]), row["currency"]),
                                None,
                                amount.Amount(
                                    -1 * (D(last_net) / D(row["net"])), last_currency
                                ),
                                None,
                                None,
                            )
                        )
                        last_net = None
                        last_currency = None
                        last_was_currency = False
                    else:
                        last_net = row["net"]
                        last_currency = row["currency"]
                        last_was_currency = True

                else:
                    txn.postings.append(
                        data.Posting(
                            self.account,
                            amount.Amount(D(row["gross"]), row["currency"]),
                            None,
                            None,
                            None,
                            None,
                        )
                    )

                if D(row["fee"]) > 0:
                    txn.postings.append(
                        data.Posting(
                            self.commission_account,
                            amount.Amount(D(row["fee"]), row["currency"]),
                            None,
                            None,
                            None,
                            None,
                        )
                    )

                if row["reference_txn_id"] != last_txn_id:
                    entries.append(txn)
                    last_txn_id = row["txn_id"]

                last_currency = row["currency"]

        if "balance" in row:
            meta = data.new_metadata(filename.name, index + 1)
            entries.append(
                data.Balance(
                    meta,
                    row["date"] + timedelta(days=1),
                    self.account,
                    amount.Amount(
                        D(self.language.decimal(row["balance"])), row["currency"]
                    ),
                    None,
                    None,
                )
            )

        return entries
