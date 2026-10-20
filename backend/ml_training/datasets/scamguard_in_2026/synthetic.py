"""Synthetic messages for ScamGuard-IN-2026 (training only, never in a test set).

Real data has gaps: the public smishing corpus (IMC'25) has no genuine
messages and few 2025-26 scam types (digital arrest, e-challan / wedding APKs,
task and stock-group scams). These templates fill those gaps. Every row made
here is tagged ``is_synthetic=1`` and ``source=synthetic`` so it can be kept out
of evaluation.

Design rules, so the model learns intent rather than topic:
  * genuine and scam templates share vocabulary (OTP, KYC, bank, bill, parcel,
    challan, refund, link, app);
  * genuine messages inform or point to an official channel; scam messages ask
    for a secret, a payment, an install, a call to a private number or a click
    on a non-official link, usually with pressure;
  * both classes get the same surface noise (case, short forms, Hinglish).
"""

from __future__ import annotations

import random
import re

BANKS = [("SBI", "VM-SBIINB", "yonosbi", "sbi.co.in"), ("HDFC Bank", "VM-HDFCBK", "HDFC Bank MobileBanking", "hdfcbank.com"),
         ("ICICI Bank", "JD-ICICIB", "iMobile Pay", "icicibank.com"), ("Axis Bank", "AX-AXISBK", "Axis Mobile", "axisbank.com"),
         ("Kotak Bank", "VK-KOTAKB", "Kotak811", "kotak.com"), ("PNB", "VM-PNBSMS", "PNB ONE", "pnbindia.in"),
         ("Bank of Baroda", "BV-BOBTXN", "bob World", "bankofbaroda.in"), ("Canara Bank", "VM-CANBNK", "Canara ai1", "canarabank.com"),
         ("Union Bank", "AD-UNIONB", "Vyom", "unionbankofindia.co.in"), ("IDFC FIRST Bank", "VM-IDFCFB", "IDFC FIRST app", "idfcfirstbank.com")]
UPI_APPS = ["PhonePe", "Google Pay", "Paytm", "BHIM", "CRED", "Amazon Pay"]
SHOPS = [("Amazon", "amazon.in"), ("Flipkart", "flipkart.com"), ("Myntra", "myntra.com"), ("Meesho", "meesho.com"),
         ("Ajio", "ajio.com"), ("Nykaa", "nykaa.com"), ("BigBasket", "bigbasket.com"), ("Blinkit", "blinkit.com")]
FOOD = ["Swiggy", "Zomato", "Zepto", "Swiggy Instamart"]
RIDES = ["Uber", "Ola", "Rapido", "Namma Yatri"]
TELCOS = [("Airtel", "Airtel Thanks app", "airtel.in"), ("Jio", "MyJio app", "jio.com"), ("Vi", "Vi app", "myvi.in"),
          ("BSNL", "BSNL Selfcare app", "bsnl.co.in")]
DISCOMS = [("BESCOM", "bescom.karnataka.gov.in"), ("MSEDCL", "mahadiscom.in"), ("TPDDL", "tatapower-ddl.com"),
           ("BSES", "bsesdelhi.com"), ("TNPDCL", "tnpdcl.org"), ("UPPCL", "uppcl.org"), ("Adani Electricity", "adanielectricity.com")]
CITIES = ["Bengaluru", "Mumbai", "Delhi", "Pune", "Hyderabad", "Chennai", "Kolkata", "Jaipur", "Lucknow", "Indore", "Mysuru", "Noida"]
NAMES = ["Rahul", "Priya", "Amit", "Sneha", "Arjun", "Kavya", "Rohan", "Ananya", "Vikram", "Pooja", "Karan", "Neha",
         "Aditya", "Divya", "Siddharth", "Meera", "Harsh", "Isha", "Manoj", "Lakshmi"]
SHORT = ["bit.ly", "tinyurl.com", "cutt.ly", "rb.gy", "is.gd", "t.ly", "shorturl.at"]
BAD_TLD = ["xyz", "top", "click", "online", "site", "live", "info", "co", "in.net", "shop", "vip"]


def _amt(r: random.Random) -> str:
    v = r.choice([r.randint(10, 999), r.randint(1000, 9999), r.randint(10000, 99999), r.randint(100000, 499999)])
    f = r.choice(["Rs.{:,}", "Rs {:,}", "INR {:,}", "₹{:,}", "Rs.{:,}.00", "INR {:,}.00", "₹ {:,}"])
    return f.format(v)


def _acct(r):
    return r.choice(["XX{}", "XXXX{}", "**{}", "x{}", "A/c no. XX{}", "...{}"]).format(r.randint(1000, 9999) if r.random() < .7 else r.randint(100, 999))


def _date(r):
    d, m = r.randint(1, 28), r.randint(1, 12)
    y = r.choice([2025, 2026, 2026, 2026])
    return r.choice([f"{d:02d}-{m:02d}-{y}", f"{d:02d}/{m:02d}/{str(y)[2:]}", f"{d:02d}{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m-1]}{str(y)[2:]}",
                     f"{d} {['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m-1]} {y}"])


def _time(r):
    return f"{r.randint(1, 12)}:{r.randint(0, 59):02d} {r.choice(['AM', 'PM'])}" if r.random() < .6 else f"{r.randint(0, 23):02d}:{r.randint(0, 59):02d}"


def _otp(r, n=None):
    n = n or r.choice([4, 6, 6, 6, 8])
    return "".join(r.choice("0123456789") for _ in range(n))


def _mobile(r):
    return r.choice("6789") + "".join(r.choice("0123456789") for _ in range(9))


def _ref(r):
    return "".join(r.choice("0123456789") for _ in range(12))


def _bad_link(r, brand="kyc"):
    b = re.sub(r"[^a-z]", "", brand.lower())[:8] or "kyc"
    kind = r.random()
    if kind < .35:
        return f"{r.choice(['http://', 'https://', ''])}{r.choice(SHORT)}/{''.join(r.choice('abcdefghjkmnpqrstuvwxyz23456789') for _ in range(6))}"
    if kind < .75:
        return f"{r.choice(['http://', 'https://', ''])}{b}-{r.choice(['kyc', 'update', 'verify', 'secure', 'help', 'login', 'pay', 'reward', 'online'])}.{r.choice(BAD_TLD)}{r.choice(['', '/login', '/update', '/verify', '/pay'])}"
    return f"http://{r.randint(11, 223)}.{r.randint(0, 255)}.{r.randint(0, 255)}.{r.randint(1, 254)}/{b}"


def _noise(r, t: str, scam: bool) -> str:
    """Same kinds of surface noise for both classes; scams get a bit more."""
    if r.random() < (.18 if scam else .08):
        t = t.upper() if r.random() < .3 else t.lower()
    if r.random() < (.25 if scam else .05):
        t = t.replace("your", r.choice(["ur", "your", "yr"])).replace("please", r.choice(["pls", "plz", "please"]))
    if scam and r.random() < .15:
        t = t.replace("account", r.choice(["acount", "a/c", "accnt"])).replace("immediately", r.choice(["immediatly", "imediately", "immediately"]))
    if r.random() < .1:
        t = t.replace(". ", ".  ")
    return t


# ----------------------------------------------------------------------------------------------- genuine

def genuine(r: random.Random) -> tuple[str, str]:
    kind = r.choices(
        ["debit", "credit", "otp", "delivery", "ride", "telecom", "dnd", "bill", "govt", "promo", "card", "emi", "food",
         "travel", "appointment", "edu", "chat", "chat_money", "security", "refund", "fastag", "challan", "job", "subscription", "insurance", "family_new",
         "vas", "hindi", "kyc_official", "alert_fwd"],
        weights=[9, 6, 10, 7, 4, 6, 3, 5, 6, 7, 4, 3, 3, 4, 3, 3, 9, 4, 4, 3, 2, 2, 2, 2, 2, 1, 3, 5, 3, 4])[0]
    bank, sender, app, dom = r.choice(BANKS)
    a = _amt(r)
    if kind == "debit":
        t = r.choice([
            f"Dear Customer, {a} debited from A/c {_acct(r)} on {_date(r)} to VPA {r.choice(NAMES).lower()}{r.randint(1, 99)}@{r.choice(['okaxis', 'ybl', 'oksbi', 'paytm', 'okhdfcbank'])} (UPI Ref No {_ref(r)}). Not you? Call 1800{r.randint(1000000, 9999999)} or SMS BLOCK to {r.choice(['9223008333', '5676791', '9215676766'])} -{bank}",
            f"{bank}: {a} spent on your Credit Card {_acct(r)} at {r.choice(['AMAZON', 'SWIGGY', 'RELIANCE SMART', 'DMART', 'BOOKMYSHOW', 'IRCTC', 'APOLLO PHARMACY'])} on {_date(r)}. Avl limit: {_amt(r)}. If not done by you, report via the {app} app or call the number on the back of your card.",
            f"A/c {_acct(r)} debited by {a} on {_date(r)}. Info: {r.choice(['ATM WDL', 'POS', 'NEFT', 'IMPS', 'UPI', 'ACH-EMI', 'NACH'])}/{_ref(r)[:8]}. Avl Bal {_amt(r)}. -{bank}",
            f"Sent {a} from {bank} {_acct(r)} To {r.choice(NAMES)} {r.choice(['Sharma', 'Kumar', 'Reddy', 'Nair', 'Patel', 'Singh'])} On {_date(r)} Ref {_ref(r)} Not You? Call 18002586161/SMS BLOCK UPI to 7308080808",
            f"Rs {r.randint(10, 9999)}.00 paid to {r.choice(FOOD + [s for s, _ in SHOPS])} via {r.choice(UPI_APPS)} UPI. UPI Ref: {_ref(r)}. Bal: {_amt(r)}",
        ])
    elif kind == "credit":
        t = r.choice([
            f"Dear Customer, your A/c {_acct(r)} is credited with {a} on {_date(r)} by {r.choice(['NEFT', 'IMPS', 'UPI', 'RTGS'])} from {r.choice(NAMES).upper()}. Avl Bal: {_amt(r)} -{bank}",
            f"{a} credited to your account {_acct(r)} towards {r.choice(['SALARY', 'refund from AMAZON', 'interest', 'dividend', 'cashback', 'PM-KISAN instalment', 'EPF withdrawal', 'scholarship'])} on {_date(r)}. -{bank}",
            f"Received {a} in your {bank} a/c {_acct(r)} from {r.choice(NAMES)} via UPI. Ref {_ref(r)}. No action needed.",
            f"Your salary of {a} has been credited to A/c {_acct(r)}. Check details in the {app} app. -{bank}",
        ])
    elif kind == "otp":
        o = _otp(r)
        svc = r.choice([bank, "Amazon", "Flipkart", "Paytm", "PhonePe", "DigiLocker", "UIDAI", "IRCTC", "Swiggy", "Zomato", "Instagram", "WhatsApp", "Google",
                        "LinkedIn", "Naukri", "Groww", "Zerodha", "CRED", "MakeMyTrip", "Income Tax e-filing", "EPFO", "Parivahan", "CoWIN", "UMANG", "BMSCE ERP"])
        t = r.choice([
            f"{o} is your OTP for {r.choice(['login', 'transaction', 'verification', 'registration', 'password reset'])} on {svc}. Valid for {r.choice([3, 5, 10, 15])} minutes. Do not share it with anyone. -{svc}",
            f"Your {svc} verification code is {o}. Never share this code with anyone, not even {svc} staff.",
            f"OTP for your {bank} transaction of {a} at {r.choice(['AMAZON', 'FLIPKART', 'MAKEMYTRIP', 'IRCTC'])} is {o}. Valid for 5 mins. {bank} never asks for OTP. If not initiated by you, call 1800{r.randint(1000000, 9999999)}.",
            f"<#> {o} is your {svc} code. Don't share it. {''.join(r.choice('abcdefghijkLMNOP123') for _ in range(11))}",
            f"Dear Customer, {o} is the OTP to link your Aadhaar with {svc}. OTP is confidential, please do not share it. -UIDAI",
            f"Use {o} to verify your mobile number on {svc}. This code expires in 10 minutes. If you did not request this, ignore this message.",
            f"{o} is OTP to log in to {svc}. Do not share with anyone. {svc} will never call you to ask for it.",
        ])
    elif kind == "delivery":
        s, sd = r.choice(SHOPS)
        o = _otp(r, 4)
        t = r.choice([
            f"Your {s} order #{_ref(r)[:10]} is out for delivery today. Share OTP {o} with the delivery agent only at the time of delivery. Track on the {s} app.",
            f"Delivered: your {s} package was delivered on {_date(r)} at {_time(r)}. Not received? Visit {sd}/help or the {s} app.",
            f"{r.choice(['Delhivery', 'Ekart', 'Blue Dart', 'Shadowfax', 'XpressBees', 'India Post'])}: Shipment {_ref(r)[:11]} from {s} will be delivered by {r.choice(['today', 'tomorrow', _date(r)])}. Track at {r.choice(['delhivery.com', 'ekartlogistics.com', 'bluedart.com', 'indiapost.gov.in'])}.",
            f"Hi, your {s} order of {r.choice(['Boat Airdopes', 'Redmi Note 14', 'Nike shoes', 'kurta set', 'books', 'mixer grinder', 'phone cover'])} has been shipped and will arrive by {_date(r)}.",
            f"Your {s} return pickup is scheduled for tomorrow. Refund of {a} will be processed to your original payment method after pickup.",
            f"India Post: Article {r.choice(['EE', 'RR', 'CP'])}{_ref(r)[:9]}IN booked on {_date(r)} has been delivered. Track at indiapost.gov.in",
        ])
    elif kind == "ride":
        rd = r.choice(RIDES)
        t = r.choice([
            f"{rd}: Your ride OTP is {_otp(r, 4)}. Share it with your driver {r.choice(NAMES)} only when you start the trip. {r.choice(['KA', 'MH', 'DL', 'TS'])}{r.randint(1, 50):02d}AB{r.randint(1000, 9999)} is arriving in {r.randint(2, 9)} min.",
            f"Your {rd} trip to {r.choice(CITIES)} {r.choice(['Airport', 'Central', 'Railway Station', 'Mall'])} has ended. Fare {a[:3]} {r.randint(80, 900)}. Rate your driver in the app.",
            f"{rd}: Captain {r.choice(NAMES)} is on the way. Vehicle {r.choice(['KA', 'MH', 'DL'])}{r.randint(1, 50):02d}{r.choice(['EX', 'HK', 'MP'])}{r.randint(1000, 9999)}.",
        ])
    elif kind == "telecom":
        tc, tapp, td = r.choice(TELCOS)
        t = r.choice([
            f"Recharge of Rs {r.choice([199, 239, 299, 349, 399, 479, 666, 719, 859, 2999])} successful for {tc} number {_mobile(r)[:2]}XXXXXX{_mobile(r)[-2:]}. Validity till {_date(r)}. Thank you for choosing {tc}.",
            f"Your {tc} plan expires on {_date(r)}. Recharge via the {tapp} or {td} to continue enjoying unlimited calls and data.",
            f"{tc}: You have used 80% of your daily data quota. Speed will reduce after 100%. Check usage on the {tapp}.",
            f"Dear customer, your {tc} postpaid bill of {a} is generated. Due date {_date(r)}. Pay on the {tapp}.",
            f"{tc} 5G is now available in your area. Use 5G at no extra cost on your current plan. Details on the {tapp}.",
            f"Your {tc} SIM upgrade request is complete. Please restart your phone to enjoy uninterrupted services.",
        ])
    elif kind == "dnd":
        tc, tapp, td = r.choice(TELCOS)
        t = r.choice([
            f"Alert: On receiving any unwanted SMS, please complain by calling 1909 or send SMS to 1909 in format 'SMS Content, Sender No, dd/mm/yy' or report through the {tapp}.",
            "Report suspected fraud calls and SMS on the Sanchar Saathi portal (sancharsaathi.gov.in) using Chakshu. Never share OTP, PIN or CVV with anyone.",
            "To stop promotional calls and SMS, SMS START 0 to 1909 or use the DND option in your operator app. -TRAI",
            "Lost money to online fraud? Call the cyber crime helpline 1930 immediately or report at cybercrime.gov.in. -I4C, MHA",
            f"{tc}: Calls from numbers starting +92, +84 or +62 claiming to be TRAI or police are fraud. Do not respond. Report on sancharsaathi.gov.in.",
        ])
    elif kind == "bill":
        dc, dd = r.choice(DISCOMS)
        t = r.choice([
            f"Dear Consumer, your {dc} electricity bill for {r.choice(['Sep', 'Oct', 'Aug', 'Jul'])} 2026 of {a} is generated. Due date {_date(r)}. Pay at {dd} or via {r.choice(UPI_APPS)}. Ignore if already paid.",
            f"{dc}: Payment of {a} received for account {_ref(r)[:10]} on {_date(r)}. Thank you.",
            f"{dc}: Planned power shutdown in your area on {_date(r)} from 10 AM to 2 PM for maintenance work. We regret the inconvenience.",
            f"Your {r.choice(['Indane', 'HP Gas', 'Bharatgas'])} LPG refill booking no. {_ref(r)[:8]} is confirmed. Cash memo {a}. Delivery within 2 days.",
            f"Your water bill of {a} for connection {_ref(r)[:9]} is due on {_date(r)}. Pay at the BWSSB portal or any authorised counter.",
            f"Gas bill generated: {a}, due {_date(r)}. Pay on the official app or website. Ignore if paid. -{r.choice(['MGL', 'IGL', 'Adani Total Gas'])}",
        ])
    elif kind == "govt":
        t = r.choice([
            f"Your Aadhaar {r.choice(['address', 'mobile', 'demographic'])} update request URN {_ref(r)[:14]} has been completed successfully. Download e-Aadhaar from myaadhaar.uidai.gov.in -UIDAI",
            f"Your PAN is linked with Aadhaar successfully. -Income Tax Department",
            f"Your ITR for AY 2026-27 has been successfully verified. Acknowledgement no. {_ref(r)}. Refund, if any, will be credited to your pre-validated bank account. -ITD",
            f"Dear member, your EPF contribution of {a} for {r.choice(['Aug', 'Sep'])}-2026 has been credited. Check passbook on the UMANG app or epfindia.gov.in -EPFO",
            f"PM-KISAN: {r.choice(['Rs 2000', '₹2,000'])} instalment has been credited to your Aadhaar-linked bank account. Check status at pmkisan.gov.in",
            f"Your Voter ID (EPIC) application reference {r.choice(['S', 'F'])}{_ref(r)[:10]} has been approved. Download e-EPIC at voters.eci.gov.in",
            f"Your passport application {r.choice(['BN', 'MU', 'DL'])}{_ref(r)[:10]} is dispatched by Speed Post. Track at passportindia.gov.in",
            f"Your documents are now available in DigiLocker: {r.choice(['Class XII Marksheet', 'Driving Licence', 'Vehicle RC', 'PAN Verification Record'])}. Open the DigiLocker app to view.",
            f"Your appointment for Aadhaar update is confirmed at {r.choice(CITIES)} Aadhaar Seva Kendra on {_date(r)} at {_time(r)}. Carry original documents.",
            "Government of India never asks for money over phone or video call for any case. 'Digital arrest' is a fraud. Report at cybercrime.gov.in or 1930.",
        ])
    elif kind == "promo":
        s, sd = r.choice(SHOPS)
        tc, tapp, td = r.choice(TELCOS)
        t = r.choice([
            f"{s} {r.choice(['Great Indian Festival', 'Big Billion Days', 'End of Reason Sale', 'Diwali Sale'])} is live! Up to {r.randint(5, 8)}0% off on top brands. Shop now on the {s} app. T&C apply. To opt out, reply STOP",
            f"Get {r.choice([10, 15, 20, 25])}% instant discount with {bank} cards on {s}. Offer valid till {_date(r)}. Shop at {sd}",
            f"{tc}: Enjoy extra {r.choice([2, 5, 10])}GB data with your next recharge. Recharge on the {tapp}. T&C apply.",
            f"Hungry? Flat {r.choice([50, 60, 100, 125])} off on your next {r.choice(FOOD)} order. Use code {r.choice(['TRYNEW', 'WELCOME50', 'FEAST'])}. T&C",
            f"{bank}: Pre-approved personal loan offer available in your {app} app. No paperwork. Check eligibility in the app. T&C apply.",
            f"New arrivals at {r.choice(['Westside', 'Lifestyle', 'Max Fashion', 'Pantaloons', 'Zudio'])}! Visit your nearest store this weekend. Flat 20% off on Rs 2999+.",
            f"Your {r.choice(['CRED', 'Paytm', 'PhonePe'])} cashback of Rs {r.randint(5, 150)} is added to your rewards. View in app.",
        ])
    elif kind == "card":
        t = r.choice([
            f"Your {bank} Credit Card {_acct(r)} statement for {r.choice(['Sep', 'Oct'])} 2026 is generated. Total due {a}, min due {_amt(r)}, due date {_date(r)}. Pay via the {app} app.",
            f"Payment of {a} received towards your {bank} Credit Card {_acct(r)}. Thank you.",
            f"Your new {bank} Debit Card has been dispatched and will reach you in 7 working days. Activate it in the {app} app. Never share your card PIN or CVV.",
            f"Your {bank} card {_acct(r)} has been blocked as requested. For a replacement, use the {app} app or visit the nearest branch.",
        ])
    elif kind == "emi":
        t = r.choice([
            f"Reminder: EMI of {a} for loan a/c {_acct(r)} is due on {_date(r)}. Please maintain sufficient balance. -{bank}",
            f"Your {r.choice(['Bajaj Finserv', 'HDFC Bank', 'Tata Capital', 'SBI'])} EMI of {a} has been successfully debited on {_date(r)}.",
            f"Your home loan interest certificate for FY 2025-26 is available in the {app} app. -{bank}",
        ])
    elif kind == "food":
        f = r.choice(FOOD)
        t = r.choice([
            f"Your {f} order from {r.choice(['Meghana Foods', 'Empire', 'Truffles', 'MTR', 'Domino’s', 'Burger King', 'Haldiram'])} is on the way. Arriving in {r.randint(10, 35)} mins.",
            f"{f}: Your order was delivered. Enjoy your meal! Rate your order in the app.",
            f"{f}: Refund of Rs {r.randint(40, 600)} for your cancelled order has been initiated to your original payment method. It may take 3-5 working days.",
        ])
    elif kind == "travel":
        t = r.choice([
            f"PNR:{_ref(r)[:10]},TRN:{r.randint(10000, 22999)},DOJ:{_date(r)},{r.choice(['SL', '3A', '2A', 'CC'])},{r.choice(['SBC-MAS', 'NDLS-BCT', 'YPR-HWH', 'MYS-SBC'])},Dep:{_time(r)}, {r.choice(['CNF', 'RAC 12', 'WL 4'])}. -IRCTC",
            f"Your flight {r.choice(['6E', 'AI', 'QP', 'SG', 'IX'])}{r.randint(100, 999)} {r.choice(['BLR-DEL', 'BOM-BLR', 'HYD-MAA'])} on {_date(r)} is on time. Web check-in is open on the airline app.",
            f"Your bus ticket with {r.choice(['KSRTC', 'redBus', 'VRL', 'AbhiBus'])} is confirmed. Seat {r.randint(1, 40)}, boarding at {r.choice(CITIES)} at {_time(r)}.",
            f"Booking confirmed at {r.choice(['OYO', 'Treebo', 'FabHotel', 'Taj'])}, {r.choice(CITIES)} for {_date(r)}. Booking ID {_ref(r)[:8]}. Pay at hotel.",
        ])
    elif kind == "appointment":
        t = r.choice([
            f"Hi, your {r.choice(['Urban Company', 'Housejoy', 'NoBroker'])} {r.choice(['professional', 'cleaner', 'electrician', 'plumber', 'AC technician'])} will arrive between {r.randint(9, 17)} and {r.randint(10, 18)} {r.choice(['am', 'pm'])} {r.choice(['today', 'tomorrow'])}. Share the start code with them only after they arrive.",
            f"Your {r.choice(['Samsung', 'LG', 'Whirlpool', 'Voltas'])} service request {_ref(r)[:8]} is scheduled for {_date(r)}. Our technician {r.choice(NAMES)} will visit between 10 AM and 1 PM.",
            f"Your {r.choice(['gas stove', 'water purifier', 'washing machine'])} installation is complete. Rate the technician in the app. -{r.choice(['Kent', 'Aquaguard', 'Bosch'])} Care",
            f"Your appointment with Dr. {r.choice(NAMES)} at {r.choice(['Apollo', 'Manipal', 'Fortis', 'Narayana', 'Aster'])} Hospital is confirmed for {_date(r)} at {_time(r)}.",
            f"Reminder: your vehicle service at {r.choice(['Maruti Suzuki', 'Hyundai', 'Honda', 'Tata Motors'])} {r.choice(CITIES)} is booked for tomorrow {_time(r)}.",
            f"Your lab report for booking {_ref(r)[:8]} is ready. View it in the {r.choice(['Tata 1mg', 'Practo', 'Apollo 24|7', 'Thyrocare'])} app.",
        ])
    elif kind == "edu":
        t = r.choice([
            f"Dear student, CIE-{r.randint(1, 3)} for {r.choice(['Machine Learning', 'Compiler Design', 'Computer Networks', 'Cloud Computing'])} is scheduled on {_date(r)}. Check the timetable on the college ERP.",
            f"Your semester fee payment of {a} has been received. Receipt no. {_ref(r)[:8]}. -Accounts Office",
            f"Placement drive: {r.choice(['Infosys', 'TCS', 'Accenture', 'Deloitte', 'Wipro', 'Bosch'])} pre-placement talk at 10 AM in the seminar hall tomorrow. Register on the placement portal.",
            f"{r.choice(['CBSE', 'VTU', 'NTA'])}: Results for {r.choice(['June 2026 exams', 'JEE Main 2026 Session 2', 'semester 6'])} are declared. Check on the official website.",
            "Library notice: books issued on your card are due for return this Friday. Late fine Rs 2 per day.",
        ])
    elif kind == "chat":
        t = r.choice([
            "Bhai kal ka plan kya hai? Movie chalein?", "Reached home safely, call you later", "Mom said dinner at 8, don't be late",
            f"Hey {r.choice(NAMES)}, can you send me the notes for tomorrow's class?", "Meeting shifted to 4 pm, conference room B",
            "Happy birthday!! Have a great year ahead 🎉", "Kal college aa raha hai kya?", "Running 10 mins late, traffic on Outer Ring Road",
            "Ok done, thanks yaar", "Can you pick up milk and bread on the way?", "The cab is downstairs, come fast",
            "Did you submit the assignment?", "Good morning! Have a nice day", "Call me when you're free", "Papa ka phone nahi lag raha, tu try kar",
            f"Let's meet at {r.choice(['Third Wave', 'Starbucks', 'CCD', 'the canteen'])} at {_time(r)}", "Sorry missed your call, in a meeting",
            "Bro the match is at 7:30 tonight, coming?", "Send me the location pin", "Your parcel came, I kept it with the watchman",
            "Haan main pahunch gaya, tension mat le", "Interview went well! Fingers crossed 🤞", "Sure, see you tomorrow",
            "What time is the train?", "Doctor said take rest for two days", "Need to recharge my phone, will call later",
        ])
    elif kind == "chat_money":
        n = r.choice(NAMES)
        t = r.choice([
            f"Sent you {r.choice(['500', '1200', '250', '2000'])} on GPay for the dinner, check", f"Bhai {r.choice(['300', '500', '800'])} bhej de UPI pe, kal wapas kar dunga",
            f"{n}, I paid the electricity bill from my account, transfer your share when free", "Got your payment, thanks!",
            "Rent transferred to the landlord, receipt bhej diya group pe", f"Can you split the cab fare? It was {r.randint(200, 900)}",
            "Mom I paid the fees online, screenshot sent", "Let me know if the money reached", "Dad sent the hostel fees, all good",
        ])
    elif kind == "security":
        t = r.choice([
            f"{bank} never asks for your OTP, PIN, CVV or password over call, SMS or email. Do not share them with anyone. Stay alert, stay safe.",
            f"Beware of fake KYC update messages. {bank} does not send links for KYC. Update KYC only at the branch or in the {app} app.",
            f"RBI Kehta Hai: never share your OTP or PIN. Report fraud at 1930 or cybercrime.gov.in.",
            f"New login to your {r.choice(['Google', 'Instagram', 'Netflix', 'Amazon'])} account from {r.choice(['Chrome on Windows', 'iPhone', 'Android'])} in {r.choice(CITIES)}. If this was you, no action is needed. If not, change your password in the app.",
            f"Your {bank} net banking password was changed on {_date(r)} at {_time(r)}. If not done by you, call the number on the back of your card.",
        ])
    elif kind == "refund":
        s, sd = r.choice(SHOPS)
        t = r.choice([
            f"Refund of {a} for your {s} order has been processed to your {r.choice(['original payment method', 'bank account', 'UPI ID'])}. It will reflect in 5-7 days.",
            f"Income Tax refund of {a} for AY 2025-26 has been credited to your bank account {_acct(r)}. -ITD",
            f"Your IRCTC ticket cancellation refund of {a} is processed to the original payment mode.",
        ])
    elif kind == "fastag":
        t = r.choice([
            f"FASTag: {a[:3]} {r.randint(30, 400)} debited at {r.choice(['Electronic City', 'Hoskote', 'Kherki Daula', 'Nelamangala'])} toll plaza for vehicle {r.choice(['KA', 'MH', 'DL'])}{r.randint(1, 50):02d}MX{r.randint(1000, 9999)}. Bal {_amt(r)}.",
            "Your FASTag balance is low. Recharge via your bank app, NETC FASTag or any UPI app.",
        ])
    elif kind == "challan":
        t = r.choice([
            f"A challan no. {r.choice(['KA', 'DL', 'MH'])}{_ref(r)} has been issued for vehicle {r.choice(['KA', 'DL', 'MH'])}{r.randint(1, 50):02d}XX{r.randint(1000, 9999)} for {r.choice(['over-speeding', 'no helmet', 'signal jump'])}. Check and pay only at echallan.parivahan.gov.in. -Parivahan",
            "Your e-challan payment has been received. Transaction ID " + _ref(r) + ". -Parivahan",
        ])
    elif kind == "job":
        t = r.choice([
            f"Hi {r.choice(NAMES)}, your interview with {r.choice(['Infosys', 'Flipkart', 'Razorpay', 'Deloitte', 'Swiggy'])} is scheduled on {_date(r)} at {_time(r)}. The meeting link is in your registered email.",
            f"Your application for {r.choice(['Software Engineer', 'Data Analyst', 'SDE Intern'])} on {r.choice(['Naukri', 'LinkedIn', 'Superset'])} was viewed by the recruiter.",
        ])
    elif kind == "subscription":
        t = r.choice([
            f"Your {r.choice(['Netflix', 'Spotify', 'JioHotstar', 'YouTube Premium', 'Prime'])} membership has been renewed for {a}. Manage it in the app or account settings.",
            f"Your {r.choice(['Netflix', 'Spotify', 'JioHotstar'])} payment failed. Update your payment method in the app to keep watching.",
        ])
    elif kind == "insurance":
        t = r.choice([
            f"Your {r.choice(['LIC', 'HDFC Life', 'Star Health', 'ICICI Lombard'])} policy {_ref(r)[:9]} premium of {a} is due on {_date(r)}. Pay on the official app or website.",
            f"Premium of {a} received for policy {_ref(r)[:9]}. Thank you. -{r.choice(['LIC', 'HDFC Life', 'Max Life'])}",
        ])
    elif kind == "vas":
        tc = r.choice(TELCOS)[0]
        t = r.choice([
            f"{r.choice(['Hungama Music', 'Gaana', 'Cricket Alerts', 'Devotional Songs', 'Daily Horoscope'])} service has been activated on your {tc} number at Rs {r.choice([2, 5, 10, 30])}/{r.choice(['day', 'week', 'month'])}. To deactivate, SMS STOP to 155223 (toll free).",
            f"Your {r.choice(['Caller Tune', 'Hello Tune', 'Jio Tune'])} '{r.choice(['Kesariya', 'Tum Hi Ho', 'Naatu Naatu', 'Apna Bana Le'])}' is active. Rs {r.choice([0, 9, 39])} charged. To stop, SMS STOP to 155223.",
            f"Thanks for using {r.choice(['SHORTFILMS', 'GAMES', 'COMEDY'])} service. You have been charged Rs {r.choice([10, 30, 90])} from your {tc} mobile. To deactivate, call or SMS STOP to 155223.",
        ])
    elif kind == "hindi":
        t = r.choice([
            f"प्रिय ग्राहक, आपके खाते {_acct(r)} से {a} की राशि {_date(r)} को डेबिट की गई है। यदि यह आपने नहीं किया है तो 1800{r.randint(1000000, 9999999)} पर कॉल करें। -{bank}",
            f"{_otp(r)} आपका OTP है। इसे किसी के साथ साझा न करें। {bank} कभी भी OTP नहीं मांगता।",
            f"प्रिय उपभोक्ता, आपका बिजली बिल {a} जारी हो गया है। अंतिम तिथि {_date(r)}। भुगतान आधिकारिक ऐप या वेबसाइट से करें।",
            f"आपके खाते में {a} जमा किए गए हैं। उपलब्ध शेष: {_amt(r)} -{bank}",
            "भाई कल शाम को घर आ जाना, खाना साथ में खाएंगे",
            f"आपका {r.choice(['Amazon', 'Flipkart', 'Meesho'])} ऑर्डर आज डिलीवर होगा। डिलीवरी के समय ही OTP {_otp(r, 4)} बताएं।",
            "PM-KISAN योजना की किस्त आपके आधार से जुड़े बैंक खाते में भेज दी गई है। स्थिति pmkisan.gov.in पर देखें।",
            "साइबर धोखाधड़ी की शिकायत 1930 पर करें या cybercrime.gov.in पर दर्ज करें। अपना OTP किसी को न बताएं।",
        ])
    elif kind == "kyc_official":
        t = r.choice([
            f"Dear Customer, periodic KYC update for your {bank} account is due. Please visit your home branch with original ID proof or update in the {app} app. {bank} never asks for OTP or PIN.",
            f"{bank}: Your re-KYC has been completed successfully. No further action is needed.",
            f"As per RBI guidelines, please update your KYC at the nearest {bank} branch. Do not respond to SMS or calls asking for KYC details or links.",
            f"Your {r.choice(['Paytm', 'PhonePe', 'Amazon Pay'])} wallet KYC is pending. Complete it inside the official app under Profile > KYC. We never ask for your OTP.",
        ])
    elif kind == "alert_fwd":
        t = r.choice([
            f"Rs {r.randint(500, 20000)} withdrawn at {bank} ATM {r.choice(['S1NC', 'S5NA', 'IIB'])}{r.randint(100000, 999999)} from A/c {_acct(r)} on {_date(r)}. Avl Bal {_amt(r)}. If not done by you, forward this SMS to 9223008333 or call 1800{r.randint(1000000, 9999999)} to block your card.",
            f"Thx for INB txn of {a} frm A/c {_acct(r)} on {_date(r)}. If not done, fwd this SMS to 9223008333 / call 18001234 to block INB. -{bank}",
            f"Thank you for using your {bank} Debit Card {_acct(r)} for a purchase worth {a} on POS at {r.choice(['DMART', 'PAYTM', 'GOOGLE', 'RELIANCE'])}. If not done by you, call 1800{r.randint(1000000, 9999999)}.",
            f"Dear {bank} Cardholder, on your request we have blocked your card ending {r.randint(1000, 9999)}. To reissue, use the {app} app or call the number on our official website.",
        ])
    else:  # family_new: genuine new-number message that asks nothing
        t = r.choice(["Hi, this is my new number, save it. Old one stopped working.", "New number hai ye mera, save kar lena - " + r.choice(NAMES)])
    return _noise(r, t, False), kind


# ----------------------------------------------------------------------------------------------- scam

def scam(r: random.Random) -> tuple[str, str]:
    kind = r.choices(
        ["kyc", "digital_arrest", "echallan_apk", "wedding_apk", "electricity", "sim_kyc", "courier_customs", "indiapost", "task_job",
         "stock_group", "loan_fee", "lottery", "family_emergency", "mistaken_upi", "collect_refund", "otp_ask", "card_points", "it_refund",
         "pm_scheme", "fake_care", "sextortion", "ott", "event_phish", "rent_army", "crypto", "lpg_kyc", "aadhaar_bio", "decoy",
         "fake_credit", "loan_harass", "hindi_scam"],
        weights=[9, 6, 6, 4, 6, 4, 5, 4, 7, 5, 5, 4, 4, 3, 3, 5, 4, 3, 3, 3, 2, 2, 2, 2, 2, 2, 2, 3, 5, 3, 5])[0]
    bank, sender, app, dom = r.choice(BANKS)
    lk = _bad_link(r, bank)
    mob = _mobile(r)
    dl = r.choice(["today", "within 24 hours", "tonight", "in 2 hours", f"today at {_time(r)}", "within 12 hrs", "immediately"])
    if kind == "kyc":
        t = r.choice([
            f"Dear {bank} user, your {r.choice(['YONO', 'net banking', 'account', 'debit card'])} will be {r.choice(['blocked', 'suspended', 'deactivated', 'frozen'])} {dl}. Update your {r.choice(['PAN', 'KYC', 'Aadhaar'])} now: {lk}",
            f"Dear Customer, your {bank} account KYC has expired. To avoid suspension click {lk} and update details {dl}.",
            f"{bank} ALERT: Your reward points / account will expire {dl}. Complete re-KYC here {lk} -Team {bank}",
            f"Aapka {bank} account aaj band ho jayega. KYC update karne ke liye is link pe click karein {lk}",
            f"Your {bank} account has been temporarily locked due to incomplete KYC. Download the {bank} KYC update app {lk}.apk to unlock.",
        ])
    elif kind == "digital_arrest":
        ag = r.choice(["CBI", "ED", "Mumbai Police Cyber Cell", "NCB", "Customs", "TRAI", "RBI", "Delhi Police Crime Branch", "Income Tax Department"])
        t = r.choice([
            f"This is {ag}. A parcel in your name containing {r.choice(['MDMA', 'fake passports', 'drugs', '5 passports and 3 credit cards'])} was seized. You are under digital arrest. Stay on video call and do not tell anyone. Join: {lk}",
            f"{ag} NOTICE: Your Aadhaar is linked to a money laundering case. An arrest warrant is issued. Call {mob} {dl} to avoid arrest.",
            f"Your mobile number is involved in illegal activity. It will be disconnected in 2 hours by TRAI. Press 9 or call {mob} to speak to the {ag} officer.",
            f"Sir aapke naam pe FIR darj hui hai. Case settle karne ke liye verification amount {_amt(r)} RBI safe account me transfer karein, warna arrest hoga. Kisi ko mat batana.",
            f"Final notice from {ag}: to clear your name, transfer {_amt(r)} for fund verification to the account given by the officer. Amount will be refunded after investigation. Keep this confidential.",
        ])
    elif kind == "echallan_apk":
        t = r.choice([
            f"Dear vehicle owner, a traffic challan of Rs {r.choice([500, 1000, 2000])} is pending for your vehicle. Download RTO e-Challan app to pay {dl} or licence will be suspended: {lk}.apk",
            f"VAHAN PARIVAHAN: your vehicle challan is unpaid. Pay now to avoid court case: {lk}",
            f"RTO TRAFFIC CHALLAN: Check your challan details here {r.choice(['RTO_Challan.apk', 'eChallan.apk', 'mParivahan_update.apk'])} {lk}",
            f"Your e-challan {r.choice(['DL', 'KA', 'MH'])}{_ref(r)} is overdue. Pay Rs {r.choice([500, 1000])} at {lk} within 24 hours or a penalty of 10x will apply.",
        ])
    elif kind == "wedding_apk":
        t = r.choice([
            f"Hi, you are invited to my wedding 🙏 Please see the invitation card: {r.choice(['Wedding_Invitation.apk', 'Shadi_card.apk', 'Invitation.apk'])}",
            f"Shaadi ka card bheja hai, install karke dekho: {lk}.apk", f"Join us for the marriage ceremony. Open the e-invite: {lk}/invite.apk",
        ])
    elif kind == "electricity":
        t = r.choice([
            f"Dear Consumer, your electricity power will be disconnected {dl} because your previous month bill was not updated. Please immediately contact electricity officer {mob}.",
            f"{r.choice([d for d, _ in DISCOMS])}: Your power supply will be cut tonight at 9:30 PM. Your last bill is not updated. Call {mob} immediately.",
            f"Bijli vibhag: aapka connection aaj raat kaat diya jayega. Bill update ke liye turant {mob} pe call karein.",
            f"Dear customer your electricity bill is pending. Pay Rs {r.randint(10, 13)} token amount via {lk} to avoid disconnection.",
        ])
    elif kind == "sim_kyc":
        tc = r.choice(TELCOS)[0]
        t = r.choice([
            f"Dear {tc} customer, your SIM KYC documents are pending. Your SIM will be blocked {dl}. Call customer care {mob}.",
            f"Your {tc} SIM card will be deactivated in 24 hrs due to e-KYC expiry. Update now: {lk}",
            f"{tc}: Your number will be suspended. To keep it active, share the OTP sent to your phone with our executive.",
        ])
    elif kind == "courier_customs":
        t = r.choice([
            f"FedEx: your parcel from {r.choice(['Taiwan', 'Dubai', 'Cambodia', 'Thailand'])} is held at customs with illegal items. Press 1 to talk to the officer or call {mob}.",
            f"Your {r.choice(['DHL', 'FedEx', 'Blue Dart', 'DTDC'])} shipment is on hold. Pay customs duty of Rs {r.randint(25, 499)} at {lk} to release it {dl}.",
            f"Your package could not be delivered due to incomplete address. Update here within 12 hours: {lk}",
        ])
    elif kind == "indiapost":
        t = r.choice([
            f"India Post: Your package has arrived at the warehouse but cannot be delivered due to incomplete address. Please update your address within 48 hours: {lk}",
            f"IndiaPost: Delivery failed twice. Pay Rs 25 redelivery fee to reschedule {lk}",
        ])
    elif kind == "task_job":
        t = r.choice([
            f"Part-time job offer: earn Rs {r.choice([3000, 5000, 8000])}/day by liking YouTube videos. Work from home. WhatsApp {r.choice(['wa.me/', 'wa.me/91'])}{mob}",
            f"Hello, I am {r.choice(NAMES)} from {r.choice(['Amazon', 'Meesho', 'Deloitte', 'Unacademy'])} HR. We have a part time job: daily salary {_amt(r)}. Join Telegram: t.me/{r.choice(['taskjob', 'earnhome', 'hrdesk'])}{r.randint(10, 999)}",
            f"Congratulations! You are selected for a hotel rating task. Pay Rs {r.choice([1000, 2000, 5000])} registration deposit to unlock your earnings of {_amt(r)}.",
            "Your task commission is frozen. Complete 3 more prepaid tasks to withdraw your money.",
            f"Ghar baithe kamao Rs {r.choice([2000, 4000, 7000])} roz! Sirf review dena hai. Abhi join karo {lk}",
        ])
    elif kind == "stock_group":
        t = r.choice([
            f"Welcome to the {r.choice(['SEBI registered', 'premium', 'VIP'])} stock group. Our institutional account gives 300% returns on IPO. Download the trading app {lk} and deposit to start.",
            f"Dear investor, guaranteed {r.choice([5, 10, 20])}% daily profit with our expert tips. Join WhatsApp group {lk}",
            "Your account profit is ₹4,80,000. To withdraw, pay 20% tax first to the given account.",
        ])
    elif kind == "loan_fee":
        t = r.choice([
            f"Congratulations! Your personal loan of {_amt(r)} is approved. Pay processing fee Rs {r.choice([999, 1499, 2999, 5500])} to get disbursal {dl}. Call {mob}",
            f"Instant loan {_amt(r)} without CIBIL. Download app {lk} and pay the file charge to receive money.",
            f"Your loan EMI is overdue. Pay now or we will send your photos to all your contacts. {lk}",
        ])
    elif kind == "lottery":
        t = r.choice([
            f"Congratulations! Your number has won {_amt(r)} in the KBC lucky draw. To claim, pay registration fee Rs {r.choice([4500, 12500, 25000])} and call {mob}.",
            f"You have won an iPhone 17 in the {r.choice(['Flipkart', 'Amazon', 'Jio'])} anniversary lucky draw! Claim your prize here {lk}",
            f"Dear customer you are the 2nd prize winner of a Tata Safari in the Snapdeal draw. Pay {_amt(r)} GST to receive the car.",
        ])
    elif kind == "family_emergency":
        t = r.choice([
            f"Hi Mom/Dad, this is my new number. My phone broke. I need {_amt(r)} urgently for a hospital bill, please send to this UPI {r.choice(NAMES).lower()}{r.randint(1, 99)}@ybl. Don't call, I'll explain later.",
            f"Uncle main {r.choice(NAMES)} hoon, naya number hai. Emergency hai, abhi {r.choice(['10000', '15000', '25000'])} bhej do please, kisi ko mat batana.",
            "Your son has been arrested by police. Send Rs 50000 for bail immediately or he will be jailed. Don't tell anyone.",
        ])
    elif kind == "mistaken_upi":
        t = r.choice([
            f"Sorry sir, I sent {_amt(r)} to your number by mistake. Please return it, I am a poor student. I am sending a request, approve it.",
            f"Sir galti se aapke account me {_amt(r)} transfer ho gaye. Please wapas bhej dijiye, request bhej raha hoon.",
        ])
    elif kind == "collect_refund":
        t = r.choice([
            f"You have received a cashback of {_amt(r)} from {r.choice(UPI_APPS)}. Enter your UPI PIN to receive the amount in your account.",
            f"Refund of {_amt(r)} from {r.choice(['Amazon', 'Flipkart', 'Swiggy'])} is pending. Approve the collect request on {r.choice(UPI_APPS)} to receive it.",
            "Scan this QR code to receive your payment of Rs 15000 for the OLX item.",
        ])
    elif kind == "otp_ask":
        t = r.choice([
            f"Dear customer, an OTP has been sent to your number. Share it with our {bank} executive to stop the unauthorised transaction.",
            f"Sir I am calling from {r.choice(['Amazon', bank, 'Flipkart'])}. Please tell me the 6 digit code you just received to cancel the order.",
            f"Hi, I accidentally entered your number for my OTP. Can you please send me the code you just got?",
            f"Your {bank} reward points of {_amt(r)} will lapse {dl}. Reply with the OTP received to redeem in cash.",
            f"Bhai mera WhatsApp verify karna hai, tere number pe 6 digit code aaya hoga, bhej de jaldi",
        ])
    elif kind == "card_points":
        t = r.choice([
            f"Dear customer your {bank} credit card reward points worth {_amt(r)} expire {dl}. Redeem in cash now: {lk}",
            f"{bank}: your credit card limit increase is approved. Confirm by entering card number, expiry and CVV at {lk}",
        ])
    elif kind == "it_refund":
        t = r.choice([
            f"Income Tax Department: you are eligible for a refund of {_amt(r)}. Verify your account number at {lk} to receive it.",
            f"Your ITR refund is on hold due to a PAN mismatch. Update details {dl} at {lk}",
        ])
    elif kind == "pm_scheme":
        t = r.choice([
            f"PM Kisan Yojana: your next instalment is on hold. Download the PM Kisan app {lk}.apk and update KYC.",
            f"PM Mudra loan of {_amt(r)} approved in your name. Pay Rs 2,500 stamp duty to receive the sanction letter.",
            f"Free laptop scheme 2026: register your name {lk} to get a free laptop from the government.",
            f"Pradhan Mantri free recharge yojana: get 3 months free recharge. Click {lk}",
        ])
    elif kind == "fake_care":
        t = r.choice([
            f"For your complaint regarding {r.choice(['Paytm', 'PhonePe', 'Amazon', 'Swiggy'])} refund, contact our customer care {mob} and install AnyDesk to resolve.",
            f"Your refund is being processed. Our support executive will help, download {r.choice(['AnyDesk', 'TeamViewer QuickSupport', 'RustDesk'])} and share the 9 digit code.",
        ])
    elif kind == "sextortion":
        t = r.choice(["I have recorded your video call. Pay Rs 20000 now or I will send it to your family and friends.",
                      "Your private video is with us. Transfer money to this UPI within 1 hour or it will be uploaded on YouTube."])
    elif kind == "ott":
        t = r.choice([f"Netflix: your account is on hold because we could not validate your billing information. Update now at {lk}",
                      f"Your JioHotstar subscription has expired. Renew for Rs 1 at {lk} to continue watching."])
    elif kind == "event_phish":
        t = r.choice([f"Register for the India AI Impact Summit 2026 delegate pass. Pay Rs 1,999 confirmation fee at {lk}",
                      f"Your IPL 2026 ticket booking is confirmed. Pay the remaining balance at {lk} to receive your ticket."])
    elif kind == "rent_army":
        t = r.choice(["I am an army officer posted at the base. I want to rent your flat. Send Rs 1 on this QR to verify your account, I will send advance.",
                      "Sir I am from CRPF, buying your item on OLX. I will send payment via QR, please scan and enter your PIN."])
    elif kind == "crypto":
        t = r.choice([f"Your USDT wallet has 1500 USDT pending. Pay withdrawal gas fee to unlock: {lk}", f"Invest Rs 10,000 in bitcoin and get Rs 1,00,000 in 7 days. Guaranteed. {lk}"])
    elif kind == "lpg_kyc":
        t = r.choice([f"Your LPG gas connection will be blocked {dl}. Complete e-KYC by calling {mob}.", f"Indane: your gas subsidy is stopped. Update KYC at {lk}"])
    elif kind == "aadhaar_bio":
        t = r.choice([f"UIDAI: your Aadhaar will be deactivated {dl}. Update your biometric details at {lk}", f"Your Aadhaar card is misused. Share your Aadhaar OTP to block it immediately."])
    elif kind == "fake_credit":
        t = r.choice([
            f"Congrats, your {_mobile(r)[:4]}XXXX{_mobile(r)[-2:]} is selected for {_amt(r)} directly in your account. Register now to use it {lk}",
            f"Dear user, {_amt(r)} can be credited to your A/c {_acct(r)} on successful verification. Check now {lk}",
            f"{_amt(r)} has been credited to your account under a government yojana. Click to view balance {lk}",
            f"Received payment of {_amt(r)} by PAYTM. Download the app and register to receive your amount {lk}",
            f"Your A/c is credited with {_amt(r)}. Enter your details to withdraw now {lk}",
        ])
    elif kind == "loan_harass":
        t = r.choice([
            "Your loan is overdue. Pay today or we will call all your contacts and share your photos.",
            f"[{r.choice(['FutureWallet', 'CashNow', 'RupeeKing'])}] Your loan is due today. Repay immediately to avoid legal action and calls to your family {lk}",
            "Legal notice: a case is filed against you for non-payment. Pay the settlement amount today to this UPI to avoid arrest.",
        ])
    elif kind == "hindi_scam":
        t = r.choice([
            f"प्रिय उपभोक्ता, आपकी बिजली आज रात 9:30 बजे काट दी जाएगी क्योंकि पिछले महीने का बिल अपडेट नहीं है। तुरंत बिजली अधिकारी {mob} पर कॉल करें।",
            f"बधाई हो! आपके नंबर ने KBC लॉटरी में 25 लाख रुपये जीते हैं। इनाम पाने के लिए {mob} पर कॉल करें और रजिस्ट्रेशन फीस जमा करें। किसी को न बताएं।",
            f"आपका {bank} खाता आज बंद हो जाएगा। KYC अपडेट करने के लिए इस लिंक पर क्लिक करें {lk}",
            f"आपका सिम कार्ड 24 घंटे में बंद हो जाएगा। KYC के लिए तुरंत {mob} पर कॉल करें।",
            f"घर बैठे रोज़ {r.choice([3000, 5000, 8000])} रुपये कमाएं, सिर्फ वीडियो लाइक करें। जुड़ें: {lk}",
            f"आपके खाते में गलती से {_amt(r)} आ गए हैं, कृपया वापस भेज दें। मैं रिक्वेस्ट भेज रहा हूं, अप्रूव करें।",
        ])
    else:  # decoy: a warning first, then the ask
        t = r.choice([
            f"{bank} never asks for your OTP. However, to complete the security check of your account, please share the OTP sent to your number with our officer {dl}.",
            f"Do not share your OTP with anyone. For your KYC verification, kindly tell the OTP to our executive who will call you shortly. -{bank}",
            f"For your safety never share PIN. To stop the fraud transaction of {_amt(r)} reply with the OTP received now.",
        ])
    return _noise(r, t, True), kind


def generate(n_genuine: int, n_scam: int, seed: int = 2026) -> list[dict]:
    r = random.Random(seed)
    rows, seen = [], set()
    for label, n, fn in (("legitimate", n_genuine, genuine), ("scam", n_scam, scam)):
        made, tries = 0, 0
        while made < n and tries < n * 30:
            tries += 1
            text, sub = fn(r)
            key = re.sub(r"\d", "0", text.lower())
            if key in seen:
                continue
            seen.add(key)
            rows.append({"text": text, "label": label, "subtype": sub})
            made += 1
    return rows
