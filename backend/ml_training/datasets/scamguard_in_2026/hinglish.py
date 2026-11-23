"""Hinglish and Hindi (Devanagari) messages for ScamGuard-IN-2026 v2.

Indian scam SMS and WhatsApp messages are often code-mixed: Hindi written in
Latin script ("aapka account band ho jayega"), Devanagari Hindi, or both mixed
with English. v1 had almost none of this. This module makes two separate sets:

* ``train_rows()``  - training only (4 of every 5 TRAIN templates), tagged ``is_synthetic=1``.
* ``dev_rows()``    - the other TRAIN templates; used to tune the v2 settings.
* ``test_rows()``   - challenge set A, written from a separate TEST bank. It was
  looked at once during development (error analysis), so it is reported as a
  development check, not as a clean final test.
* ``test_b_rows()`` - challenge set B, a third bank written afterwards and scored
  only in the final run. This is the clean held-out Hinglish/Hindi result.

The banks use different wording, sentence order and slot values, so the test
sets measure generalisation to new phrasing, not memorised templates. All sets
are synthetic and are reported as such; they are not real-world data. Because
each template is rendered several times, results are also reported per
template.

Labelling rule (same as the main dataset): a message is a scam when it asks for
a secret, a payment or fee, an app install, a call or reply to a private number,
or a click on a non-official link, usually with pressure. Genuine messages
inform, or point the reader to an official app, branch or helpline.
"""

from __future__ import annotations

import random

BANKS = [("SBI", "sbi.co.in", "YONO SBI"), ("HDFC", "hdfcbank.com", "HDFC MobileBanking"), ("ICICI", "icicibank.com", "iMobile"),
         ("Axis", "axisbank.com", "Axis Mobile"), ("PNB", "pnbindia.in", "PNB ONE"), ("Kotak", "kotak.com", "Kotak811"),
         ("Bank of Baroda", "bankofbaroda.in", "bob World"), ("Canara", "canarabank.com", "Canara ai1")]
UPI = ["PhonePe", "GPay", "Paytm", "BHIM"]
NAMES = ["Rahul", "Priya", "Amit", "Sneha", "Arjun", "Kavya", "Rohan", "Neha", "Vikram", "Pooja", "Karan", "Divya"]
REL = ["mummy", "papa", "bhaiya", "didi", "beta", "chachu", "mausi"]
SHORT = ["bit.ly", "tinyurl.com", "cutt.ly", "rb.gy", "is.gd"]
BAD = ["xyz", "top", "click", "online", "site", "vip", "live"]
CITIES = ["Delhi", "Mumbai", "Lucknow", "Jaipur", "Patna", "Indore", "Bengaluru", "Pune"]


def _amt(r):
    return r.choice(["Rs {}", "Rs.{}", "₹{}", "INR {}"]).format(r.choice([r.randint(99, 999), r.randint(1000, 9999), r.randint(10000, 99999)]))


def _link(r, bank=None):
    if r.random() < 0.5:
        return f"https://{r.choice(SHORT)}/{''.join(r.choice('abcdefghjkmnpqrstuvwxyz23456789') for _ in range(6))}"
    stem = (bank or r.choice(["kyc", "reward", "refund", "update", "verify"])).lower().replace(" ", "")
    return f"http://{stem}-{r.choice(['kyc', 'secure', 'help', 'verify', 'support'])}.{r.choice(BAD)}"


def _phone(r):
    return f"{r.choice('6789')}{r.randint(100000000, 999999999)}"


def _slots(r):
    b = r.choice(BANKS)
    return {"bank": b[0], "site": b[1], "app": b[2], "amt": _amt(r), "amt2": _amt(r), "link": _link(r, b[0]), "ph": _phone(r),
            "upi": r.choice(UPI), "name": r.choice(NAMES), "rel": r.choice(REL), "otp": str(r.randint(100000, 999999)),
            "city": r.choice(CITIES), "hrs": r.choice(["2", "6", "12", "24"]), "a4": str(r.randint(1000, 9999)),
            "date": f"{r.randint(1, 28):02d}-{r.randint(1, 12):02d}", "time": f"{r.randint(1, 12)}:{r.randint(0, 59):02d}"}


# ------------------------------------------------------------------ TRAIN bank (training only)
TRAIN_SCAM = [
    "Priy grahak, aapka {bank} account aaj band ho jayega. KYC turant update karein: {link}",
    "{bank} alert: aapka PAN link nahi hai, account block hoga. Abhi click karo {link}",
    "Congratulations! Aapne {amt} ka cashback jeeta hai. Claim karne ke liye link kholo {link}",
    "Hello sir, main {bank} head office se bol raha hu. Aapke account me galat transaction hua hai, OTP batayein jo abhi aaya hai",
    "aapka bijli connection aaj raat 9:30 baje kat jayega. Turant electricity officer ko call karein {ph}",
    "Bhai mera number change ho gaya, urgent {amt} chahiye, {upi} kar do is number pe {ph}, kal lauta dunga",
    "Aapka courier customs me ruka hai, illegal items mile hain. CBI officer se baat karein {ph} warna arrest hoga",
    "Ghar baithe kamao {amt} roz! Sirf YouTube video like karo. Join karo Telegram: {link}",
    "Aapke naam pe loan approve hua hai {amt}. Processing fee {amt2} bhejo aur paisa turant account me",
    "Dear customer aapka {upi} wallet suspend ho gaya hai. Reactivate karne ke liye apna UPI PIN daalein {link}",
    "Aapka electricity bill pending hai. Abhi pay karo warna connection cut. Ye app download karo {link}",
    "Mam aapka parcel deliver nahi ho paya, address galat hai. {amt} ka redelivery charge bharein {link}",
    "Beta main police station se bol raha hu, aapka bhai pakda gaya hai. Case band karne ke liye {amt} bhejo turant",
    "आपका {bank} खाता बंद कर दिया जाएगा। तुरंत KYC अपडेट करें: {link}",
    "बधाई हो! आपने {amt} की लॉटरी जीती है। इनाम पाने के लिए {amt2} प्रोसेसिंग फीस भेजें",
    "आपका बिजली कनेक्शन आज रात काट दिया जाएगा। तुरंत इस नंबर पर कॉल करें {ph}",
    "प्रिय ग्राहक, आपके खाते में संदिग्ध लेनदेन। अपना OTP हमें बताएं ताकि खाता सुरक्षित रहे",
    "Aapka SIM card {hrs} ghante me band ho jayega. Re-verify karne ke liye 1 dabaye ya call karein {ph}",
    "Stock market tips group me join karo, 300% guaranteed return. Admin se contact karo {ph}",
    "Aapka Aadhaar misuse hua hai money laundering case me. Digital arrest se bachne ke liye video call pe aao {ph}",
    "Hi {name}, part time job hai, daily {amt} kamao. Bas reply karo YES aur registration fee {amt2} bhejo",
    "{upi} se {amt} aapke account me aa rahe hain. Receive karne ke liye apna PIN dalo is link par {link}",
    "Aapka e-challan pending hai {amt}. Abhi pay na kiya toh licence cancel. APK download karein {link}",
    "Shaadi ka card bheja hai, dekh lo 🙏 {link}",
]
TRAIN_GENUINE = [
    "{bank}: Aapke khate XX{a4} se {amt} debit hue {date} ko. Aapne nahi kiya? Turant 1930 ya bank helpline pe call karein",
    "Apna OTP {otp} kisi ke saath share na karein. {bank} kabhi OTP nahi maangta. - {bank}",
    "{rel} main ghar pahunch gaya, khana kha liya. Kal call karta hu",
    "Bhai kal ki meeting {time} baje hai, laptop le aana",
    "Aapka {upi} payment {amt} {name} ko safal raha. UPI Ref {a4}{a4}",
    "{bank}: Aapka KYC update ho gaya hai. Koi action ki zarurat nahi. Kisi link pe click na karein",
    "Aapka parcel aaj deliver hoga. Delivery OTP {otp} sirf delivery boy ko dikhayein jab parcel mil jaye",
    "Bijli bill {amt} due date {date}. Pay karne ke liye official app ya website use karein",
    "Happy birthday {name}! Bahut saara pyaar, party kab de rahe ho 🎉",
    "आपके खाते XX{a4} में {amt} जमा हुए। - {bank}",
    "{bank} कभी भी आपका PIN या OTP नहीं मांगता। सावधान रहें। शिकायत के लिए 1930 पर कॉल करें",
    "{rel} aaj der se aaunga, office me kaam zyada hai",
    "Aapka recharge {amt} ka safal raha. Validity 28 din. Dhanyavaad",
    "Dear {name}, aapka appointment kal {time} baje confirm hai. - {city} Clinic",
    "Kal school band rahega barish ki wajah se. - Principal",
    "{bank}: Aapka naya debit card dispatch ho gaya hai. Branch se ya {app} app se activate karein",
    "Aapke naam pe koi loan offer nahi hai jab tak aap khud apply na karein. Fake calls se bachein - {bank}",
    "Bhaiya {amt} bhej diye {upi} pe, check kar lo",
    "आज शाम 7 बजे सोसाइटी मीटिंग है, सभी लोग आएं",
    "Train {city} se {time} baje chalegi, platform 3. Seat confirm hai",
]

# ------------------------------------------------------------------ TEST bank (held-out challenge only)
TEST_SCAM = [
    "URGENT {bank} notice: kal se aapki netbanking ruk jayegi. Turant verify kijiye {link} nahi toh khata freeze",
    "Sir aapka refund {amt} pending hai. Refund lene ke liye screen share app install kijiye, hum help karenge",
    "Customer care {bank}: aapke card pe {amt} ka reward point expire ho raha hai, card number aur CVV bhejiye",
    "{rel} ye mera naya number hai, phone kho gaya. Jaldi {amt} {upi} kar do, hospital me hu",
    "TRAI se call: aapke Aadhaar pe 2 SIM illegal use ho rahe hain. Mumbai police se jodne ke liye 9 dabayein",
    "Aapki beti ka accident hua hai, hospital me hai. Turant {amt} bhejiye is account me, baad me baat karte hain",
    "Free laptop yojana 2026! Students ke liye. Form bhariye aur {amt2} registration charge dijiye {link}",
    "Mubarak ho! KBC lucky draw me aapka number aaya, {amt} jeete. Claim ke liye WhatsApp karein {ph}",
    "Aapke account me {amt} galti se aa gaye hain, please wapas bhej dijiye is UPI pe, warna police complaint",
    "Work from home: product review karo aur {amt} pao. Pehle {amt2} deposit karna hoga",
    "Gas connection {hrs} ghante me disconnect hoga. KYC ke liye officer ko call karo {ph}",
    "आपके नाम पर ड्रग्स का पार्सल पकड़ा गया है। गिरफ्तारी से बचने के लिए तुरंत {ph} पर संपर्क करें",
    "आपका पैन कार्ड ब्लॉक हो गया है। अभी इस लिंक पर जाकर अपडेट करें {link}",
    "मुफ्त राशन योजना में नाम जोड़ने के लिए {amt2} का भुगतान करें और अपना आधार नंबर भेजें",
    "Bank manager bol raha hu, aapka ATM block hai, jo 6 digit code aaya hai wo bata dijiye abhi",
    "Insurance policy band ho rahi hai, bonus {amt} lene ke liye aaj hi {amt2} jama karein {link}",
    "Aapka PF claim reject hua. Dobara apply karne ke liye UAN password aur OTP is number pe bhejein {ph}",
    "Crypto me paisa lagao, 1 hafte me double. Hamare VIP group ka link {link}",
    "Hello ji, OLX pe aapka saman kharidna hai, QR scan karke payment receive kar lo",
    "Electricity department: pichle mahine ka bill update nahi hua. Aaj raat line kategi, {ph} pe sampark karein",
]
TEST_GENUINE = [
    "{bank}: {amt} aapke a/c XX{a4} me credit hue {date}. Avl bal {amt2}",
    "Kripya dhyan dein: {bank} ya RBI kabhi bhi call pe OTP, PIN ya CVV nahi maangte. Saavdhan rahein",
    "{rel} dawai le li? Doctor ne bola tha time pe lena",
    "Bhai match dekhne chal raha hai kya shaam ko? {city} stadium",
    "Aapka order deliver ho gaya hai. Dhanyavaad shopping ke liye",
    "{name} kal college aa rahi ho? Assignment submit karna hai",
    "Aapki gas booking confirm. Delivery {date} tak hogi. Booking no {a4}",
    "Aapka bijli bill {amt} ka bhugtan safal raha. Receipt no {a4}",
    "आपका ऑर्डर कल तक पहुंच जाएगा। धन्यवाद",
    "{rel} main {time} tak pahunch jaunga, gate khula rakhna",
    "आपकी पॉलिसी का प्रीमियम {amt} प्राप्त हुआ। धन्यवाद",
    "Kisi ne aapse OTP maanga toh share na karein. Fraud ki report 1930 pe ya cybercrime.gov.in pe karein",
    "Yaar movie ki ticket book kar di, {time} ka show hai",
    "{bank}: Aapka cheque no {a4} clear ho gaya hai",
    "Exam result kal subah 10 baje website pe aayega. Best of luck!",
    "Aapki complaint register ho gayi hai. Ticket {a4}. Hamari team 48 ghante me sampark karegi official number se",
    "Mummy ne bola sabzi le aana aate waqt, aur doodh bhi",
    "{upi}: Aapne {name} ko {amt} bheje. Agar ye aapne nahi kiya toh app me Help section dekhein",
    "आज बिजली की कटौती सुबह 10 से 2 बजे तक रहेगी रखरखाव कार्य के कारण। - विद्युत विभाग",
    "Thank you {name}, gift bahut pasand aaya ❤️",
]

# ------------------------------------------------------------------ TEST B bank (final held-out, scored once)
TEST_B_SCAM = [
    "Namaste, {bank} se KYC executive bol rahi hu. Aapka account kal suspend hoga, verification ke liye jo SMS code aaya hai wo share kijiye",
    "Aapke mobile number pe {amt} ka bonus aaya hai {upi} me. Lene ke liye scan karo aur PIN daalo {link}",
    "{name} ji aapki pension band hone wali hai. Jeevan pramaan update karne ke liye {amt2} bhejiye {ph} pe",
    "Income tax refund {amt} approve ho gaya. Bank details aur OTP verify karein yaha {link}",
    "Hello, Amazon se bol rahe hain, aapke naam pe iPhone order hua hai. Cancel karne ke liye AnyDesk download karo",
    "Aapke bete ko police ne pakda hai. Abhi {amt} bhejo toh chhod denge, kisi ko mat batana",
    "Mubarak ho aapka mobile number {amt} ki lottery me select hua hai. GST charge {amt2} pay karke paisa le lo",
    "Aapki FASTag KYC expire ho gayi. Toll pe double charge lagega. Turant update karo {link}",
    "Sir hotel review karke {amt} per task kamaiye. Pehla task free, baad me {amt2} deposit karna hoga",
    "CBI officer: aapke Aadhaar se fraud bank account khula hai. Video call pe raho aur kisi ko mat batao, warna giraftari",
    "Dear {name}, aapka {bank} credit card limit badh gaya hai. Activate karne ke liye card ke peeche wale 3 number batayein",
    "Aapka DTH connection aaj band ho jayega. Abhi recharge karein is link se {link}",
    "आपके बैंक खाते का केवाईसी अधूरा है। 24 घंटे में खाता ब्लॉक हो जाएगा। लिंक पर क्लिक करें {link}",
    "आपके आधार से जुड़ा सिम गैरकानूनी गतिविधि में इस्तेमाल हुआ है। तुरंत {ph} पर कॉल करें वरना कानूनी कार्रवाई होगी",
    "बधाई हो! प्रधानमंत्री योजना में आपको {amt} मिलेंगे। रजिस्ट्रेशन शुल्क {amt2} भेजें",
    "Aapke account me {amt} ka cashback hai. Claim karne ke liye collect request accept karo aur PIN dalo",
    "{rel} main dost ke phone se bol raha hu, mera wallet chori ho gaya. {amt} turant is UPI pe bhej do",
    "Electricity bill update nahi hua. Aaj raat 10 baje power cut hoga. Officer ka number {ph}, abhi call karein",
]
TEST_B_GENUINE = [
    "{bank}: Rs {a4} aapke card XX{a4} se Swiggy pe kharch hue. Aapne nahi kiya? App me card block karein",
    "Kripya kisi anjaan link pe click na karein. {bank} kabhi SMS se KYC nahi maangta",
    "{rel} bus pakad li hai, 2 ghante me pahunch jaunga",
    "Bhai notes bhej de kal ke lecture ke, exam parso hai",
    "Aapka FASTag recharge {amt} safal raha. Wallet balance {amt2}",
    "Aapki pension {amt} aapke khate me jama ho gayi hai. - Treasury",
    "{name} ka shaadi ka function {date} ko hai, sab log zaroor aana",
    "आपका गैस सिलेंडर बुक हो गया है। बुकिंग संख्या {a4}",
    "Society maintenance {amt} is mahine ka due hai. Office me ya society app se jama karein",
    "{bank}: Aapka home loan EMI {amt} {date} ko kata jayega. Khate me balance rakhein",
    "Dhyan dein: police kabhi video call pe arrest nahi karti. Aise call aaye toh 1930 pe shikayat karein",
    "Aapki train {city} 30 minute late hai. Asuvidha ke liye khed hai",
    "Doctor sahab ne kal {time} baje bulaya hai, reports le aana",
    "आपके खाते XX{a4} से {amt} का यूपीआई भुगतान हुआ। - {bank}",
    "Yaar kal cricket khelne chalna hai subah 6 baje, ground pe milte hain",
    "Aapka Aadhaar address update request {a4} safal raha. Naya card 15 din me ghar aayega",
    "Beta fees jama kar di hai, receipt photo bhej raha hu",
    "{upi}: {name} ne aapko {amt} bheje. Paise aapke bank khate me aa gaye hain",
]


def _render(templates, n, seed, subtype):
    r = random.Random(seed)
    out, seen = [], set()
    tries = 0
    while len(out) < n and tries < n * 50:
        tries += 1
        ti = r.randrange(len(templates))
        t = templates[ti].format(**_slots(r))
        if r.random() < 0.25:
            t = t.lower()
        if t not in seen:
            seen.add(t)
            out.append((t, ti))
    return [{"text": t, "subtype": subtype, "template": f"{subtype}_{ti}"} for t, ti in out]


def _rows(scam_t, gen_t, n_each, seed, source, synthetic):
    rows = [dict(x, label="scam") for x in _render(scam_t, n_each, seed, "hinglish_scam")]
    rows += [dict(x, label="legitimate") for x in _render(gen_t, n_each, seed + 1, "hinglish_genuine")]
    for x in rows:
        x.update(source=source, is_synthetic=synthetic)
    return rows


def _part(templates, dev: bool):
    return [t for i, t in enumerate(templates) if (i % 5 == 4) == dev]


def collected_train_rows() -> list[dict]:
    """Real Hindi/Hinglish messages collected by the team (add_real_indic.py), train half only."""
    import os

    import pandas as pd
    f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "real_indic_collected.csv")
    if not os.path.exists(f):
        return []
    d = pd.read_csv(f)
    d = d[d.split == "train"]
    return [{"text": t, "label": lab, "subtype": "real_indic", "source": "real_indic_collected", "is_synthetic": 0} for t, lab in zip(d.text, d.label)]


def train_rows(n_each: int = 600, seed: int = 42) -> list[dict]:
    return _rows(_part(TRAIN_SCAM, False), _part(TRAIN_GENUINE, False), n_each, seed, "synthetic_hinglish", 1)


def dev_rows(n_each: int = 100, seed: int = 7) -> list[dict]:
    return _rows(_part(TRAIN_SCAM, True), _part(TRAIN_GENUINE, True), n_each, seed, "hinglish_dev", 1)


def test_rows(n_each: int = 150, seed: int = 2026) -> list[dict]:
    return _rows(TEST_SCAM, TEST_GENUINE, n_each, seed, "hinglish_challenge_a", 1)


def test_b_rows(n_each: int = 150, seed: int = 99) -> list[dict]:
    return _rows(TEST_B_SCAM, TEST_B_GENUINE, n_each, seed, "hinglish_challenge_b", 1)
