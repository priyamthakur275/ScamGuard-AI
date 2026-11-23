# Collecting real Hindi and Hinglish messages

ScamGuard v2 scores 66.7% F1 with 26% false alarms on real Hindi messages (results_v2.md, X8), against 97.5% on
English. Almost all of its Hindi training data is synthetic. Real messages are the only fix. Target: **at least 200
messages, about half scams and half genuine**, from at least 4 different phones.

## What to collect

**Genuine messages matter as much as scams.** Most of the current Hindi errors are genuine messages wrongly flagged.

| Genuine (about 100) | Scams (about 100) |
|---|---|
| Bank debit/credit alerts in Hindi or Hinglish | KYC / PAN / Aadhaar "account will be blocked" |
| OTP messages ("OTP kisi ko na batayein") | Electricity "connection will be cut tonight, call ..." |
| Recharge, plan and validity reminders (Jio, Airtel, Vi) | Lottery, KBC, "aapne inaam jeeta" |
| Electricity, gas, water bills and booking confirmations | "PM loan yojana", cheap loans, 4G tower rent |
| Government notices (ration, scholarship, Covid, CM helpline) | Part-time job / task / investment groups |
| Delivery, train, school, hospital messages | "Mera naya number hai, paise bhej do" |
| Family and friends chat in Hinglish | Fake courier, customs, police or "digital arrest" |

Spam ads (sales, offers) that do not ask for money, codes or a call to a private number are **not scams**; label them
genuine or leave them out.

## How (about 20 minutes per person)

1. Open SMS and WhatsApp, search for Hindi words such as *aapka*, *khata*, *turant*, *आपका*, *खाता*.
2. Copy each message into one row of a shared Google Sheet with two columns, `text` and `label` (`scam` or `genuine`).
   An optional third column, `note`, can say where it came from ("SMS, mum's phone").
3. **Before pasting, delete people's names.** Phone numbers, account numbers, OTPs, emails and UPI IDs are replaced
   automatically with random stand-ins, but names are not.
4. Unsure whether it is a scam? Leave it out. A wrong label hurts more than a missing message.
5. Ask the owner of the phone before you copy their messages.

## Then (one command)

Download the sheet as CSV and, from `backend/`:

    python -m ml_training.datasets.scamguard_in_2026.add_real_indic ~/Downloads/collected.csv
    python -m ml_training.research.train_production
    python -m ml_training.research.v2_experiments

The first command masks personal data, drops duplicates and anything already in the dataset or close to the frozen
77-message test set, groups near-duplicates, and splits whole groups 50/50 into train and test. The second retrains
the production model with the train half. The third reports the frozen test set (X8) and the collected test half
(X8b) in results_v2.md. Run the first command again whenever more messages come in; earlier rows keep their split.
