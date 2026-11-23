# ScamGuard pilot kit (v2)

A 10-minute usability pilot for 15-50 people. It produces a System Usability Scale (SUS) score, task success
rates and comments. **No pilot has been run yet. Do not report any pilot numbers until real people have taken it.**

## 1. Make the Google Form (about 10 minutes)

Create a form with these items, in this order. Name the columns exactly as shown (Forms uses the question text as
the CSV header), because `backend/scripts/sus_score.py` finds them by their first word.

**Consent (required, yes/no):** "I agree to take part. I will not paste real personal messages that contain my
OTPs, account numbers or other private data. My answers are anonymous."

**Tasks.** Give each participant the same three messages (copy them into the form description) and ask them to
check each one on the website or the Telegram bot.

| Column | Message to check | Correct answer |
|---|---|---|
| `Task 1 correct?` | "Dear customer, your SBI account will be blocked today. Update KYC: http://sbi-kyc-update.xyz" | Scam |
| `Task 2 correct?` | "Rs 1,250 debited from A/c XX4821 on 12-11 at AMAZON. Not you? Call the number on your card." | Genuine |
| `Task 3 correct?` | "Beta mera naya number hai, phone kho gaya. Jaldi 5000 PhonePe kar do, hospital me hu" | Scam |

For each task ask: "What did ScamGuard say, and did you agree?" with options *Yes - it was right*, *No - it was wrong*,
*Not sure*. (Score "Yes" as success.)

**SUS (1 = Strongly disagree ... 5 = Strongly agree).** Start each question with `SUS1` ... `SUS10`:

1. SUS1 I think that I would like to use ScamGuard frequently.
2. SUS2 I found ScamGuard unnecessarily complex.
3. SUS3 I thought ScamGuard was easy to use.
4. SUS4 I think that I would need the support of a technical person to be able to use ScamGuard.
5. SUS5 I found the various functions in ScamGuard were well integrated.
6. SUS6 I thought there was too much inconsistency in ScamGuard.
7. SUS7 I would imagine that most people would learn to use ScamGuard very quickly.
8. SUS8 I found ScamGuard very cumbersome to use.
9. SUS9 I felt very confident using ScamGuard.
10. SUS10 I needed to learn a lot of things before I could get going with ScamGuard.

**Explanations (1-5):** `Explain: The warning signs (Scam X-Ray) helped me understand why a message was risky.`

**Comments (free text):** `Comments: What confused you or what would you change?`

## 2. Run it

Share the form and the site link (and the Telegram bot, if set up). Open the site five minutes before, because the free
server sleeps.

## 3. Score it

Responses → three dots → Download responses (.csv), then:

    cd backend
    python scripts/sus_score.py ~/Downloads/responses.csv

A SUS of 68 is average; above 80 is in the top 10% of products. Report the number of participants, the mean with its
95% confidence interval, and task success, and keep the raw CSV private.
