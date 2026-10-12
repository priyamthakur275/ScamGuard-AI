/** Spot-the-scam rounds. Written by the team from patterns in public
 * advisories (RBI, CERT-In, I4C, TRAI); names and numbers are invented. */
export interface TrainerItem {
  id: string;
  channel: "SMS" | "WhatsApp" | "Phone call" | "Email";
  from: string;
  message: string;
  isScam: boolean;
  lesson: string;
  flags: string[];
}

export const TRAINER_ITEMS: TrainerItem[] = [
  {
    id: "kyc", channel: "SMS", from: "VM-SBIUPD",
    message: "Dear Customer, your SBI YONO account will be blocked today. Update PAN immediately: http://sbi-yono-kyc.xyz",
    isScam: true, lesson: "Banks never send KYC links that threaten to block you today.",
    flags: ["Threat + deadline (blocked today)", "Look-alike link on a .xyz domain", "Asks you to act through a link, not the official app"],
  },
  {
    id: "otp-real", channel: "SMS", from: "AX-HDFCBK",
    message: "482913 is your OTP for a txn of Rs 1,250 at Swiggy. Valid 5 mins. Do not share it with anyone. HDFC Bank never asks for OTP.",
    isScam: false, lesson: "A genuine OTP message tells you NOT to share it and asks you to do nothing.",
    flags: ["No link, no request", "Matches a purchase you made", "Warns you not to share"],
  },
  {
    id: "digital-arrest", channel: "Phone call", from: "+91 70xxx xxx21 (video call)",
    message: "This is Mumbai cyber police. A parcel with drugs was sent on your Aadhaar. You are under digital arrest. Stay on video call, don't tell family, and transfer money to the RBI safe account for verification.",
    isScam: true, lesson: "There is no such thing as 'digital arrest'. Police never ask for money on a call.",
    flags: ["Fear + secrecy (don't tell family)", "Impersonating police/RBI", "Money to a 'safe account'"],
  },
  {
    id: "job", channel: "WhatsApp", from: "+44 7xxx (unknown)",
    message: "Hi! Part-time job: like YouTube videos and earn Rs 150 per like. Daily income Rs 3,000-8,000. Join our Telegram for tasks.",
    isScam: true, lesson: "Being paid to like videos is the opening of a 'task scam' that later asks you to deposit money.",
    flags: ["Too good to be true pay", "Unknown international number", "Moves you to Telegram"],
  },
  {
    id: "delivery-real", channel: "SMS", from: "JD-AMAZON",
    message: "Your Amazon order of 'Boat earphones' has been shipped and will arrive by Thursday. Track in the Amazon app.",
    isScam: false, lesson: "Genuine delivery updates match something you ordered and point to the official app.",
    flags: ["No payment asked", "Matches your order", "Official app, not a random link"],
  },
  {
    id: "electricity", channel: "SMS", from: "+91 98xxx xxx10",
    message: "Dear consumer your electricity power will be disconnected tonight at 9.30 PM because previous month bill was not updated. Contact electricity officer 9812345670.",
    isScam: true, lesson: "Electricity boards don't send disconnection threats from personal numbers.",
    flags: ["Sent from a personal mobile number", "Tonight deadline", "Asks you to call an 'officer'"],
  },
  {
    id: "mistake", channel: "WhatsApp", from: "+91 63xxx xxx88",
    message: "Sorry bhai, I sent Rs 5,000 to your GPay by mistake. I have sent a request, please approve so I get it back. My mother is in hospital.",
    isScam: true, lesson: "Approving a 'request' or entering your UPI PIN always SENDS money; you never need a PIN to receive.",
    flags: ["Collect request disguised as a refund", "Emotional pressure", "Check your bank app: no money actually arrived"],
  },
  {
    id: "interview", channel: "Email", from: "careers@infosys.com",
    message: "Your interview is scheduled for Tuesday 11 am on Microsoft Teams. Please carry a government ID. There is no fee at any stage of our hiring process.",
    isScam: false, lesson: "Real employers never charge fees; this one even says so and uses its own domain.",
    flags: ["Official company domain", "No payment", "Clear, verifiable details"],
  },
  {
    id: "lottery", channel: "WhatsApp", from: "KBC Lucky Draw",
    message: "Congratulations! Your number won Rs 25,00,000 in the KBC lucky draw. To claim, pay processing fee Rs 12,500 and contact manager Rana Singh.",
    isScam: true, lesson: "You can't win a lottery you never entered, and real prizes never need a fee.",
    flags: ["Prize you never entered", "Pay to receive", "Fake 'manager' contact"],
  },
  {
    id: "remote", channel: "Phone call", from: "+91 89xxx xxx40",
    message: "Hello, I am from customer care for your refund. Please install AnyDesk and tell me the 9-digit code on your screen.",
    isScam: true, lesson: "Screen-sharing apps let scammers see your OTPs and control your phone. Never install one for a stranger.",
    flags: ["Remote-access app", "Unrequested 'customer care' call", "Refund bait"],
  },
  {
    id: "family", channel: "WhatsApp", from: "+91 70xxx (new number)",
    message: "Hi Papa, this is my new number, my phone broke. I need Rs 18,000 urgently for college fees, please send on this UPI, will explain later.",
    isScam: true, lesson: "Before sending money to a 'new number', call your family member on their old number.",
    flags: ["Unknown new number", "Urgent money request", "Avoids a call ('will explain later')"],
  },
  {
    id: "debit-real", channel: "SMS", from: "AD-ICICIT",
    message: "INR 650 spent on ICICI Bank card XX4821 at Zomato on 12-Oct. Avl limit INR 42,300. If not you, call the number on the back of your card.",
    isScam: false, lesson: "Real alerts tell you to use the number on your card, never a number inside the SMS.",
    flags: ["Points to the number on your own card", "No link", "Matches a real purchase"],
  },
];
