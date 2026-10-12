"""Builds indian_scam_supplement.csv: Indian-context scam and genuine
messages that the UCI/Kaggle SMS Spam Collection (UK, 2011) does not cover.

Why: the base dataset is mostly prize/ringtone spam, so the model had never
seen KYC/OTP fraud, fake job and task scams, digital-arrest calls, UPI
refund tricks, electricity-disconnection SMS or call-style transcripts. It
scored those at 5-20% even when the threat scorer flagged them.

How: the team wrote the fragments below by hand, modelled on fraud
patterns described in public advisories (RBI, CERT-In, I4C / cybercrime.gov.in,
TRAI, DoT Sanchar Saathi). Messages are composed from these fragments with a
fixed random seed, so the file is reproducible. Genuine messages deliberately
reuse the same vocabulary (OTP, bank, account, KYC, delivery, bill) so the
model learns the *intent* (asking you to share/pay/click) rather than the
topic words.

This is a curated supplement, not field-collected data. Accuracy is
therefore reported separately on indian_challenge_set.csv, which is written
independently (no fragments shared) and never used for training.

    python -m ml_training.datasets.build_indian_supplement
"""

from __future__ import annotations

import csv
import random
from pathlib import Path

SEED = 20261012
OUT = Path(__file__).with_name("indian_scam_supplement.csv")

BANKS = ["SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "PNB", "Bank of Baroda", "Kotak", "Canara Bank", "Union Bank", "Paytm Payments Bank"]
NAMES = ["Rahul", "Priya", "Amit", "Sneha", "Vikram", "Anjali", "Rohan", "Kavya", "Arjun", "Neha", "Sanjay", "Pooja"]
CITIES = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Pune", "Chennai", "Kolkata", "Jaipur", "Lucknow"]
SHADY = ["bit.ly/{x}", "tinyurl.com/{x}", "{x}-verify.xyz", "{x}-update.top", "secure-{x}.online", "{x}-kyc.in.net", "{x}.help-desk.site", "rb.gy/{x}", "{x}-refund.click"]
SLUGS = ["sbi-kyc", "hdfc-netbank", "icici-alert", "bescom-pay", "india-post", "fedex-in", "itr-refund", "upi-claim", "rewards-pts", "aadhaar-link", "pan-update", "jobs-hr", "trai-sim", "kbc-lucky"]


def link(r: random.Random) -> str:
    slug = r.choice(SLUGS) + str(r.randint(1, 99))
    return ("http://" if r.random() < 0.6 else "") + r.choice(SHADY).format(x=slug)


def phone(r: random.Random) -> str:
    return r.choice(["+91 ", "", "0"]) + str(r.choice([6, 7, 8, 9])) + "".join(str(r.randint(0, 9)) for _ in range(9))


def amount(r: random.Random, lo: int, hi: int) -> str:
    return f"Rs.{r.randrange(lo, hi, 50):,}"


# ---------------------------------------------------------------- scams
def scam_kyc(r):
    b = r.choice(BANKS)
    return r.choice([
        f"Dear Customer, your {b} account will be blocked today due to incomplete KYC. Update PAN immediately: {link(r)}",
        f"{b}: Your YONO/net banking is suspended. Click {link(r)} and verify KYC within 24 hrs to avoid permanent block.",
        f"ALERT! {b} KYC expired. Account will be freezed tonight. Update now {link(r)} or call {phone(r)}",
        f"Dear {b} user your account has been temporarily locked. To unlock share the OTP received and complete re-KYC at {link(r)}",
        f"Your {b} debit card is blocked due to suspicious activity. Call our KYC officer on {phone(r)} immediately to reactivate.",
        f"Aapka {b} account aaj band ho jayega. KYC update karne ke liye is link par click karein {link(r)}",
        f"Pan card not linked with {b} account. Your account will be deactivated. Link now: {link(r)}",
    ])


def scam_otp(r):
    b = r.choice(BANKS)
    return r.choice([
        f"Sir I am calling from {b} head office, your card is getting blocked. Please tell me the OTP that you just received to stop it.",
        f"Hello madam, this is {b} customer care. For your reward points redemption kindly share the 6 digit OTP sent on your mobile.",
        f"Your refund of {amount(r, 900, 9000)} is pending. Share the OTP with our executive to receive money in your account.",
        f"Bhai galti se tumhare number pe OTP chala gaya, please woh code mujhe bhej do jaldi",
        f"To cancel the unauthorised transaction of {amount(r, 5000, 50000)} reply with the OTP sent to you now.",
        f"Dear user your UPI will be deactivated. Send the verification code you received to {phone(r)} on WhatsApp.",
    ])


def scam_bill(r):
    board = r.choice(["BESCOM", "MSEDCL", "TPDDL", "electricity department", "BSES", "TNEB"])
    return r.choice([
        f"Dear Consumer, your electricity power will be disconnected tonight at 9.30 PM from {board} office because your previous month bill was not updated. Please contact our officer {phone(r)}",
        f"{board}: Your light connection will be cut today. Pay pending bill immediately at {link(r)}",
        f"Electricity bill not paid. Supply will be disconnected in 2 hours. Download app from {link(r)} to pay now.",
        f"Bijli bill pending hai, aaj raat connection kat jayega. Turant {phone(r)} par call karein.",
    ])


def scam_job(r):
    amt = amount(r, 15000, 90000)
    return r.choice([
        f"Congratulations! You are selected for work from home job. Earn {amt} per month. Pay registration fee {amount(r, 500, 3000)} to confirm: {link(r)}",
        f"Part time job: like YouTube videos and earn Rs.150 per like. Daily income {amount(r, 2000, 8000)}. Contact HR on Telegram {link(r)}",
        f"Hi, I am {r.choice(NAMES)} from HR team. We found your resume on Naukri. Simple online task job, earn {amt}. Interested? WhatsApp {phone(r)}",
        f"Amazon hiring data entry operators. No interview. Salary {amt}. Pay refundable security deposit {amount(r, 1000, 5000)} today.",
        f"Prepaid task completed! To withdraw your commission of {amount(r, 3000, 20000)} you must recharge {amount(r, 2000, 10000)} into your task account first.",
        f"Ghar baithe kamaye {amt} mahina. Sirf mobile chahiye. Joining fee {amount(r, 300, 2000)}. Abhi message karein {phone(r)}",
    ])


def scam_invest(r):
    return r.choice([
        f"Double your money in 7 days! Join our stock trading group with guaranteed {r.randint(20, 300)}% returns. {link(r)}",
        f"SEBI registered expert tips. Invest {amount(r, 5000, 50000)} today and get assured daily profit. Join VIP group {link(r)}",
        f"Crypto investment: deposit USDT to our wallet and earn {r.randint(5, 30)}% daily. Limited slots. WhatsApp {phone(r)}",
        f"Dear investor, IPO allotment guaranteed through our institutional account. Transfer {amount(r, 10000, 90000)} to secure shares.",
        f"Earn passive income with our forex app. Minimum deposit {amount(r, 1000, 9000)}, withdraw anytime. Register {link(r)}",
    ])


def scam_prize(r):
    return r.choice([
        f"Congratulations! Your mobile number won {amount(r, 250000, 2500000)} in KBC lucky draw. To claim call {phone(r)} and pay processing fee.",
        f"You have won an iPhone 15 in Flipkart anniversary lucky draw. Pay delivery charge Rs.99 at {link(r)}",
        f"Dear customer you have won a cashback of {amount(r, 1000, 9000)} from PhonePe. Accept the collect request to receive.",
        f"Your SIM number is selected for Jio lucky prize {amount(r, 50000, 500000)}. Contact manager {r.choice(NAMES)} {phone(r)}",
    ])


def scam_delivery(r):
    return r.choice([
        f"India Post: Your parcel is held at our warehouse due to incomplete address. Update within 24 hours: {link(r)}",
        f"FedEx: A parcel in your name contains illegal items and is seized by customs. Press 1 to talk to officer.",
        f"Your package could not be delivered. Pay Rs.{r.randint(19, 99)} redelivery fee at {link(r)} or it will be returned.",
        f"DHL: Customs duty of {amount(r, 1500, 9000)} pending on your international parcel. Pay now {link(r)}",
    ])


def scam_authority(r):
    agency = r.choice(["CBI", "Mumbai Police cyber cell", "TRAI", "Narcotics department", "ED", "customs department", "RBI"])
    return r.choice([
        f"This is {agency}. An FIR is registered against your Aadhaar for money laundering. You are under digital arrest, stay on video call and do not tell anyone.",
        f"TRAI notice: your mobile number will be disconnected in 2 hours due to illegal activity. Press 9 to speak to officer.",
        f"Sir I am calling from {agency}, your Aadhaar is used to open bank accounts for illegal transactions. Transfer {amount(r, 50000, 500000)} to RBI safe account for verification.",
        f"Your PAN is linked to a drug parcel case. To avoid arrest pay the security amount to the {agency} officer immediately.",
        f"Income Tax Department: You are eligible for a refund of {amount(r, 5000, 30000)}. Submit bank details at {link(r)}",
        f"Traffic challan of {amount(r, 500, 5000)} pending on your vehicle. Pay immediately to avoid court case: {link(r)}",
    ])


def scam_upi_loan(r):
    return r.choice([
        f"Instant loan of {amount(r, 20000, 500000)} approved without CIBIL. Pay processing fee {amount(r, 500, 3000)} to get money in 5 minutes. {link(r)}",
        f"Your loan app EMI is overdue. Pay now or we will send your photos to all your contacts. {phone(r)}",
        f"Hi, I sent {amount(r, 2000, 20000)} to your UPI by mistake. Please return it, I am sending a request, just enter your PIN.",
        f"Your credit card reward points worth {amount(r, 2000, 15000)} expire today. Redeem now at {link(r)}",
        f"Get pre-approved credit card with lifetime free. Share your card number, expiry and CVV for instant activation.",
    ])


def scam_personal(r):
    n = r.choice(NAMES)
    return r.choice([
        f"Hi mom, this is my new number, my phone broke. I need {amount(r, 5000, 40000)} urgently for hospital, please send on this UPI.",
        f"Hello {n} uncle, I am your son's friend, he met with an accident in {r.choice(CITIES)}. Send money immediately for surgery.",
        f"Beta main papa ka dost hoon, unhone kaha tha tumhe paise bhejne ko, maine galti se zyada bhej diye, wapas kar do",
        f"Dear, I am an army officer posted in {r.choice(CITIES)}, I am selling my car cheap due to transfer. Pay advance {amount(r, 5000, 20000)} for gate pass.",
        f"Your WhatsApp account will be banned. Verify immediately by sending the 6 digit code we sent to you.",
    ])


def scam_call(r):
    b = r.choice(BANKS)
    return r.choice([
        f"Hello sir good morning, I am calling from {b} credit card department. Your card limit is increased, for activation please confirm the card number and the OTP.",
        f"Madam this is from electricity office, your meter is not updated, please install the app I am sending and enter your card details to pay ten rupees.",
        f"Hello, I am calling from customer care, you asked for refund na, please download AnyDesk and tell me the code on screen.",
        f"Sir, I am an officer from the cyber crime branch. Your number is linked with a fraud case. Do not disconnect the call and do not tell your family.",
        f"Hi this is Amazon support, an order of iPhone is placed from your account. If not you press 1 and share the OTP to cancel.",
        f"Hello ji, main bank se bol raha hoon, aapka ATM card band ho gaya hai, card ke peeche ka number aur OTP batayiye.",
    ])


# ---------------------------------------------------------------- genuine
def legit_bank(r):
    b = r.choice(BANKS)
    return r.choice([
        f"{r.randint(100000, 999999)} is the OTP for your {b} transaction of {amount(r, 100, 9000)}. Valid for 5 mins. Do not share it with anyone. {b} never asks for OTP.",
        f"Your a/c XX{r.randint(1000, 9999)} is debited by {amount(r, 100, 20000)} on {r.randint(1, 28)}-10-26 for UPI txn. Avl bal {amount(r, 2000, 90000)}. Not you? Call the number on the back of your card.",
        f"{b}: {amount(r, 1000, 80000)} credited to your account XX{r.randint(1000, 9999)} towards salary. Thank you for banking with us.",
        f"Reminder from {b}: your credit card bill of {amount(r, 1000, 40000)} is due on {r.randint(1, 28)} Oct. Pay through the official app or net banking.",
        f"{b} will never call you asking for OTP, PIN or card details. Do not share them with anyone, even if the caller claims to be from the bank.",
        f"Your KYC with {b} is complete. No further action is needed. Visit the branch if you have questions.",
        f"Dear customer, your FD of {amount(r, 10000, 500000)} has matured and the amount is credited to your savings account.",
    ])


def legit_services(r):
    return r.choice([
        f"Your electricity bill for September is {amount(r, 300, 4000)}. Due date {r.randint(1, 28)}/10. Pay via the official BESCOM app or any UPI app.",
        f"Payment of {amount(r, 300, 4000)} received for your electricity account. Thank you.",
        f"Your Amazon order of {r.choice(['headphones', 'a phone cover', 'books', 'a water bottle', 'shoes'])} has been shipped and will arrive by Thursday.",
        f"Your Swiggy order is out for delivery. Our delivery partner {r.choice(NAMES)} will reach in 15 minutes.",
        f"Recharge of Rs.{r.choice([199, 239, 299, 719])} successful on your Jio number. Validity 28 days. Thank you.",
        f"Your appointment with Dr. {r.choice(NAMES)} is confirmed for tomorrow at {r.randint(9, 12)}:30 AM. Please arrive 10 minutes early.",
        f"Your train ticket PNR {r.randint(1000000000, 9999999999)} is confirmed. Coach B{r.randint(1, 6)}, seat {r.randint(1, 72)}. Happy journey.",
        f"Your Ola ride is arriving. Driver {r.choice(NAMES)}, white Dzire. Share the ride PIN only after you sit in the car.",
        f"Your Aadhaar update request has been processed. Download the updated Aadhaar from the official UIDAI website.",
        f"Your income tax return for AY 2026-27 has been processed. Refund, if any, will be credited to your validated bank account.",
    ])


def legit_transactions(r):
    b = r.choice(BANKS)
    svc = r.choice(["Airtel", "Jio", "Vi", "BESCOM", "Tata Power", "ACT Fibernet", "Indane", "Zomato", "Amazon", "Flipkart", "IRCTC", "LIC"])
    return r.choice([
        f"Thank you for your payment of {amount(r, 200, 20000)} to {svc}. Your receipt number is {r.randint(10000, 99999)}.",
        f"Your {svc} complaint {r.randint(10000, 99999)} has been closed. Reply 1 if your issue is resolved or 2 to reopen.",
        f"Your service request with {svc} is registered. Our technician will visit between 10 am and 1 pm tomorrow.",
        f"{b}: Your credit card payment of {amount(r, 500, 50000)} has been received. Thank you.",
        f"Your {svc} bill of {amount(r, 199, 3000)} is generated for this month. Due date {r.randint(1, 28)} Nov. Ignore if already paid.",
        f"{b}: Interest of {amount(r, 100, 5000)} credited to your savings account for the quarter.",
        f"Your refund of {amount(r, 100, 5000)} for the cancelled {svc} order has been initiated and will reach your account in 5-7 working days.",
        f"Your EMI of {amount(r, 1000, 30000)} for loan account XX{r.randint(1000, 9999)} will be auto-debited on {r.randint(1, 28)}th. Keep sufficient balance.",
        f"{svc}: Your plan has been renewed. Next renewal date {r.randint(1, 28)} Dec. Manage it in the official app.",
        f"We value your feedback. Rate your recent {svc} experience from 1 to 5 by replying to this message.",
        f"Your policy premium of {amount(r, 1000, 40000)} has been received by {svc}. Policy is in force.",
        f"Cheque no. {r.randint(100000, 999999)} for {amount(r, 1000, 90000)} has been cleared in your {b} account.",
    ])


def legit_personal(r):
    n = r.choice(NAMES)
    return r.choice([
        f"Hi {n}, are you coming for dinner tonight? Mom is making biryani.",
        f"Bhai kal ka match dekhne chalega? Tickets main book kar dunga.",
        f"Meeting moved to 3 pm tomorrow, please update the slides before that.",
        f"Reached {r.choice(CITIES)} safely, will call you after I check in.",
        f"Can you send me the notes for tomorrow's DBMS class? I missed the lecture.",
        f"Happy birthday {n}! Have a great year ahead, party soon.",
        f"Papa, the fees for next semester is due on 20th, I'll pay it through the college portal.",
        f"Kal subah 8 baje gym chalna hai, late mat karna.",
        f"Thanks for the help with the project yesterday, the demo went well.",
        f"Don't forget to bring the charger, mine is not working.",
        f"Hey, I paid you back {amount(r, 100, 2000)} for lunch on GPay, check once.",
        f"Ma'am, I have submitted the assignment on the portal. Please let me know if anything is missing.",
    ])


def legit_call(r):
    return r.choice([
        f"Hello, I am calling from the dental clinic to confirm your appointment tomorrow at 11 am. Please call back if you need to reschedule.",
        f"Hi, this is {r.choice(NAMES)} from the courier, I am outside your building with your parcel, can you come down to the gate?",
        f"Hello sir, this is a reminder call from your child's school about the parent teacher meeting on Saturday.",
        f"Hi, I am calling from the HR team regarding your interview scheduled on Monday at 10 am at our {r.choice(CITIES)} office. No fee is required.",
        f"Hello beta, I reached home, the train was late. Talk to you in the evening.",
        f"Hi, this is the bank branch. Your new cheque book is ready, you can collect it from the branch with your ID.",
    ])


SCAMS = [scam_kyc, scam_otp, scam_bill, scam_job, scam_invest, scam_prize, scam_delivery, scam_authority, scam_upi_loan, scam_personal, scam_call]
GENUINE = [legit_bank, legit_services, legit_transactions, legit_personal, legit_call]


def build(n_scam: int = 520, n_legit: int = 620) -> list[tuple[str, str]]:
    r = random.Random(SEED)
    rows: set[tuple[str, str]] = set()
    while sum(1 for _, l in rows if l == "scam") < n_scam:
        rows.add((r.choice(SCAMS)(r), "scam"))
    while sum(1 for _, l in rows if l == "legitimate") < n_legit:
        rows.add((r.choice(GENUINE)(r), "legitimate"))
    out = sorted(rows)
    r.shuffle(out)
    return out


def main() -> None:
    rows = build()
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["text", "label"])
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
