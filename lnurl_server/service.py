from dataclasses import dataclass
import asyncio
from typing import Any, Optional, TypedDict
import lnurl
import json
import hashlib
import math
import logging
import requests
import secrets
import os


def to_f(value, places="%.1f"):
    v = value
    if isinstance(v, str):
        v = float(value)
    return float(places % v)


MAX_CORN = 0.01 * 100_000_000


async def loop_helper(callback):
    loop = asyncio.get_event_loop()
    future = loop.run_in_executor(None, callback)
    return await future


logger = logging.getLogger(__name__)
logger.setLevel(level=logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(handler)


class Invoice(TypedDict):
    currency: str
    amount_msat: int
    payment_hash: str
    payment_secret: str
    description: str
    payee: str
    signature: dict
    features: dict
    date: int


class FundSource:
    def get_owner(self, owner: str):
        raise NotImplementedError

    def deposit_funds(self, owner: str, amount: int) -> str:
        """amount in sats"""
        raise NotImplementedError

    def withdraw_funds(self, owner: str, amount: int, invoice: str, symbol="BTCUSDC"):
        raise NotImplementedError

    def decode_invoice(self, invoice: str) -> Invoice:
        raise NotImplementedError


@dataclass
class LnurlHandler:
    domain: str
    service: FundSource
    min_sats_receivable: Optional[int] = 1
    max_sats_receivable: Optional[int] = MAX_CORN
    username: Optional[str] = ""
    lnurl_address: Optional[str] = ""
    metadata_info: Optional[str] = ""

    @property
    def metadata(self):
        return self.metadata_info or f"Zap {self.username} some sats"

    def get_address(self, owner: str):
        exists = self.service.get_owner(owner=owner)
        if exists:
            self.username = owner
            self.lnurl_address = f"{owner}@{self.domain}"

    @property
    def base_url(self):
        return f"https://{self.domain}"

    def lnurl_address_encoded(self) -> lnurl.Lnurl:
        if self.username:
            return lnurl.encode(f"{self.base_url}/lnurlp/{self.username}")

    def metadata_for_payrequest(self) -> str:
        return json.dumps(
            [
                ["text/plain", self.metadata],
                ["text/identifier", self.lnurl_address],
                # ["image/jpeg;base64", "TODO optional"],
            ]
        )

    def metadata_hash(self) -> str:
        return hashlib.sha256(
            self.metadata_for_payrequest().encode("UTF-8")
        ).hexdigest()

    def lnurl_pay_request_lud16(
        self, ln_address: str, min_sats=0
    ) -> lnurl.LnurlPayResponse:
        """
        Implements [LUD-16](https://github.com/lnurl/luds/blob/luds/16.md) `payRequest`
        initial step, using human-readable `username@host` addresses.
        path="/lnurlp/{username}", method="GET">
        path="/.well-known/lnurlp/{username}",
        """
        username = parse_username(ln_address)
        self.get_address(username)
        if not self.lnurl_address:
            return None

        logger.info(
            "LUD-16 payRequest for username='{username}'".format(username=username)
        )
        return lnurl.LnurlPayResponse.parse_obj(
            dict(
                callback=f"{self.base_url}/lnurlp/{username}/callback",
                minSendable=(min_sats or self.min_sats_receivable) * 1000,
                maxSendable=self.max_sats_receivable * 1000,
                metadata=self.metadata_for_payrequest(),
            )
        )

    def lnurl_pay_request_callback_lud06(
        self,
        username: str,
        amount: int,
        tag="message",
        message=lambda x: f"Thanks for zapping {x}",
    ) -> lnurl.LnurlPayActionResponse:
        """path="/lnurlp/{username}/callback","""
        self.get_address(parse_username(username))
        if not self.lnurl_address:
            return None
        username = self.username

        # TODO check compatibility of conversion to sats, some wallets
        # may not like the invoice amount not matching?
        amount_sat = math.ceil(amount / 1000)
        logger.info(
            "LUD-06 payRequestCallback for username='{username}' sat={amount_sat} (mSat={amount})".format(
                username=username,
                amount_sat=amount_sat,
                amount=amount,
            )
        )

        if amount_sat < self.min_sats_receivable:
            logger.warning(
                "LUD-06 payRequestCallback with too-low amount {amount_sat} sats".format(
                    amount_sat=amount_sat,
                )
            )
            return None

        if amount_sat > self.max_sats_receivable:
            logger.warning(
                "LUD-06 payRequestCallback with too-high amount {amount_sat} sats".format(
                    amount_sat=amount_sat,
                )
            )
            return None

        invoice = self.service.deposit_funds(username, amount_sat)
        if not invoice:
            logger.warning("Failed to generate lightning invoice")
            return None

        return lnurl.LnurlPayActionResponse.parse_obj(
            dict(
                pr=invoice,
                success_action={
                    "tag": tag,
                    "message": message(username),
                },
                routes=[],
            )
        )

    def lnurl_withdraw_lud03(
        self,
        description="Initiating withdrawal",
        callback_url=None,
        username=None,
    ):
        maximum_amount = self.service.get_account_balance()
        minimum_amount = 0
        callback = callback_url or f"{self.base_url}/lnurlw/{username}/callback"
        k1 = secrets.token_hex(32)
        payload = lnurl.LnurlWithdrawResponse.parse_obj(
            {
                "callback": callback,
                "k1": k1,
                "defaultDescription": description,
                "minWithdrawable": minimum_amount,
                "maxWithdrawable": maximum_amount,
            }
        )
        return payload

    def initiate_withdrawal(self, owner: str, invoice: str, fee=100):
        fee_msats = fee * 1000
        details = self.service.decode_invoice(invoice)
        invoice_amount = details["amount_msat"]
        total_amount = invoice_amount + fee_msats
        amount_in_sats = math.ceil(total_amount / 1000)
        return self.service.withdraw_funds(owner, amount_in_sats, invoice)


def get_wrapped_invoice(original_invoice: str):
    response = requests.post(
        "https://lnproxy.org/spec", json={"invoice": original_invoice}
    )
    if response.status_code < 400:
        result = response.json()
        if result.get("status") == "ERROR":
            raise Exception(result["reason"])
        breakpoint()
        return result["proxy_invoice"]


def parse_username(email_or_name):
    username = email_or_name.split("@")[0]
    print("function")
    return username


NODE_URL = os.getenv("NODE_BASE_URL")
LN_ADDRESS_DOMAIN = os.getenv("LN_ADDRESS_DOMAIN")
LN_USERNAME = os.getenv("LN_USERNAME", "nwc")


@dataclass
class NWCProxy:
    base_url: str

    def create_invoice(self, amount: int, description: str):
        response = requests.post(
            f"{self.base_url}/api/run-command",
            json={
                "action": "makeInvoice",
                "data": {"amount": amount, "memo": description},
            },
        )
        if response.status_code < 400:
            result = response.json()["result"]
            return result
        response.raise_for_status()


def new_phoenix_client():
    return NWCProxy(base_url=NODE_URL)


def run_async(coroutine):
    try:
        return asyncio.run(coroutine)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coroutine)


class AppFundingSource(FundSource):
    def get_owner(self, owner: str):
        return {"owner": owner}

    def deposit_funds(self, owner: str, amount: int, description="Deposit") -> str:
        if owner == LN_USERNAME:
            client = new_phoenix_client()
            result = client.create_invoice(
                amount,description
            )
            return result["paymentRequest"]
        return super().deposit_funds(owner, amount)


class AppLnurlHandler(LnurlHandler):
    def lnurl_pay_request_callback_lud06(
        self,
        username: str,
        amount: int,
        tag="message",
        message=lambda x: f"Thanks for zapping {x}",
    ) -> lnurl.LnurlPayActionResponse:
        """path="/lnurlp/{username}/callback","""
        self.get_address(parse_username(username))
        if not self.lnurl_address:
            return None
        username = self.username

        # TODO check compatibility of conversion to sats, some wallets
        # may not like the invoice amount not matching?
        amount_sat = math.ceil(amount / 1000)
        logger.info(
            "LUD-06 payRequestCallback for username='{username}' sat={amount_sat} (mSat={amount})".format(
                username=username,
                amount_sat=amount_sat,
                amount=amount,
            )
        )

        if amount_sat < self.min_sats_receivable:
            logger.warning(
                "LUD-06 payRequestCallback with too-low amount {amount_sat} sats".format(
                    amount_sat=amount_sat,
                )
            )
            return None

        if amount_sat > self.max_sats_receivable:
            logger.warning(
                "LUD-06 payRequestCallback with too-high amount {amount_sat} sats".format(
                    amount_sat=amount_sat,
                )
            )
            return None

        invoice = self.service.deposit_funds(username, amount_sat)
        if not invoice:
            logger.warning("Failed to generate lightning invoice")
            return None
        payload = dict(
            pr=invoice,
            routes=[],
        )
        return lnurl.LnurlPayActionResponse.parse_obj(payload)

    def generate_invoice(self, username: str, amount: int):
        result = self.lnurl_pay_request_callback_lud06(
            username,
            amount,
            tag="payRequest",
            message=lambda x: f"Payment to ln address for {x}",
        )
        return result

    def get_ln_details(self, username: str, amount=None):
        result = self.lnurl_pay_request_lud16(username,amount)
        return result

    def get_user(self, username: str):
        return username == LN_USERNAME

    def to_url(self, identifier, is_dev=False):
        parts = identifier.split("@")
        if len(parts) != 2:
            raise ValueError(f"Invalid lightning address {identifier}")

        domain = parts[1]
        username = parts[0]
        protocol = "http" if is_dev else "https"
        keysend_url = f"{protocol}://{domain}/.well-known/keysend/{username}"
        lnurlp_url = f"{protocol}://{domain}/.well-known/lnurlp/{username}"
        nostr_url = f"{protocol}://{domain}/.well-known/nostr.json?name={username}"
        return lnurlp_url, keysend_url, nostr_url

    def get_json(self, url):
        response = requests.get(url)
        if response.status_code >= 300:
            raise Exception(f"Request failed with status {response.status_code}")
        return response.json()

    def lnurl_address_encoded(self, url: str) -> lnurl.Lnurl:
        return lnurl.encode(url)


handler = AppLnurlHandler(
    domain=LN_ADDRESS_DOMAIN,
    service=AppFundingSource(),
    min_sats_receivable=0.00000001 * 100_000_000,
    max_sats_receivable=0.02 * 100_000_000,
)
