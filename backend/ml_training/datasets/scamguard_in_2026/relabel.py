"""Label audit for the IMC'25 India subset.

IMC'25 rows are messages that users *reported* as smishing. An audit of a random
sample of 70 campaigns found that about a third were genuine (bank alerts, OTPs
with a "do not share" warning, order updates, brand ads, fraud-awareness notices).
Reporting is not the same as being a scam, so every campaign is put into one of:

  scam        strong fraud cue (block/suspend + update/KYC/PAN/call, prize + fee,
              pay-to-receive, earn-per-day, remote app, ask for OTP/PIN, ...)
  genuine     genuine-notice shape and no fraud cue (transaction alert, OTP with a
              warning, order/shipping update, receipt, premium-due, awareness notice)
  review      neither or both; decided by hand in imc_review.csv

The rules here are deliberately independent of the app's ThreatScorer so that the
evaluation of that scorer is not circular.
"""

from __future__ import annotations

import re

SCAM = [
    r"\b(block|blocked|suspend\w*|deactivat\w*|disconnect\w*|closed|expire\w*|frozen|hold)\b.{0,90}\b(update|kyc|pan|aadha?ar|call|contact|click|link|visit|verify|documents?)\b",
    r"\b(update|kyc|pan|verify)\b.{0,90}\b(block|blocked|suspend\w*|deactivat\w*|disconnect\w*|closed)\b",
    r"\belectric\w*\b.{0,80}\b(disconnect\w*|cut)\b",
    r"\b(won|winner|win|prize|lucky ?draw|selected)\b.{0,120}\b(registration|charge|fee|deposit|pay|claim|contact|call|send)\b",
    r"\b(registration|processing|file) (charge|fee)s?\b",
    r"\b(earn|salary|income)\b.{0,40}\b(per day|/day|daily|a day|rs ?\d+ ?/ ?day)\b",
    r"\bpart[- ]?time\b|\bwork from home\b|\btasks?\b.{0,40}\b(deposit|earn|commission)\b",
    r"\b(anydesk|teamviewer|quick ?support)\b",
    r"\b(share|send|tell|forward|provide)\b.{0,30}\b(otp|pin|cvv|password)\b",
    r"\b(arrest|warrant|cbi|narcotics|money laundering|digital arrest|customs)\b",
    r"\bsend (your )?(name|address|details)\b",
    r"\b(invest\w*)\b.{0,60}\b(return|profit|double|guarantee\w*)\b",
    r"\bloan\b.{0,60}\b(approved|sanctioned)\b.{0,80}\b(fee|charge|pay|deposit|download|app|link|call)\b",
    r"\b(reward|points)\b.{0,60}\b(expire\w*|redeem)\b.{0,60}\b(link|click|http)\b",
    r"\.apk\b",
    r"\bhttp://\d+\.\d+\.\d+\.\d+",
    r"\b(dear|hi|hello)\b.{0,20}\b(sir|madam|friend)\b.{0,80}\b(invest|business|partner|supply|help)\b",
    r"\bgift card\b|\bbitcoin|\busdt\b|\bcrypto\b",
    r"\bcan be credited\b|\b(click|download|tap|scan)\b.{0,25}\bto receive\b|\bpayment request\b",
]

GENUINE = [
    r"\b(debited|credited|spent|w/d|withdrawn|txn|transaction)\b.{0,80}\b(a/c|account|card)\b.{0,10}\b(ending|xx|\*\*|x{2,})",
    r"\b(a/c|account|card)\b.{0,10}(ending|xx+|\*\*)\s?\d{2,4}.{0,80}\b(debited|credited|spent|reversed|w/d)\b",
    r"\b(otp|code)\b.{0,140}\b(do not|don't|never|dont)\b.{0,30}\b(share|disclose)\b",
    r"\b(do not|don't|never)\b.{0,20}\b(share|disclose)\b.{0,40}\b(otp|code)\b",
    r"\b(shipped|delivered|out for delivery|dispatched)\b",
    r"\b(order|booking)\b.{0,30}\b(id|no|number|#)\b",
    r"\b(receipt|received|we confirm receipt|payment of rs.{0,20} received)\b",
    r"\bmaintain sufficient balance\b",
    r"\b(fraudsters?|beware|be alert|cyber swachhata|awareness|never asks?)\b",
    r"\bhas requested\b.{0,40}\bfrom you\b",
    r"\byou have successfully\b",
    r"\b(t&c|t&cs|tnc|t & c)\b",
    r"\bopt out\b|\bto unsubscribe\b|\breply stop\b",
]

_S = [re.compile(p, re.I | re.S) for p in SCAM]
_G = [re.compile(p, re.I | re.S) for p in GENUINE]


def scam_cues(t: str) -> int:
    return sum(1 for rx in _S if rx.search(t))


def genuine_cues(t: str) -> int:
    return sum(1 for rx in _G if rx.search(t))


def classify(t: str) -> str:
    s, g = scam_cues(t), genuine_cues(t)
    if s and not g:
        return "scam"
    if g and not s:
        return "genuine"
    return "review"
