"""Learning Center — static seed content.

Curated short reads (~2-3 min each) organised into three hubs:
  * communication — child-centred communication
  * boundaries   — healthy boundaries between co-parenting homes
  * mediation    — how to arrive at mediation prepared

Each article is a plain dict so it can be swapped for a MongoDB collection
later without touching the routes. Bodies are markdown-ish plain text with
paragraphs separated by blank lines; the frontend renders them as
paragraphs. Keep bodies at 300-500 words to honour the "short read" promise.

Author's promise:
  * Non-diagnostic, non-adjudicative, non-legal.
  * Never picks a side. Always child-first.
  * Every article ends with "3 things to try this week" bullets.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


HUBS: List[Dict[str, Any]] = [
    {
        "slug": "communication",
        "name": "Child-centred communication",
        "tagline": "Say the hard things in ways your child stays out of.",
        "accent": "#3D1A78",
        "articles": [
            {
                "slug": "the-two-inbox-rule",
                "title": "The two-inbox rule",
                "read_minutes": 2,
                "summary": (
                    "Separate what your co-parent needs to know from what "
                    "you wish they knew. It changes the tone of every message."
                ),
                "body": (
                    "Most co-parenting messages fail because they carry two "
                    "loads at once: information the other parent needs, and "
                    "emotion you need to release. When the two arrive together, "
                    "the reader hears the emotion first and the information "
                    "second — if at all.\n\n"
                    "Try imagining your writing app has two inboxes. Inbox A "
                    "is what your co-parent has to know so your child's week "
                    "goes well: pickup time, medication dose, a sports kit "
                    "left in your car. Inbox B is everything else: what hurt, "
                    "what confused you, what you wish they understood.\n\n"
                    "Send Inbox A. Save Inbox B for your journal, a friend, "
                    "or a coach. It doesn't mean Inbox B doesn't matter — it "
                    "means your child's Monday morning doesn't ride on it.\n\n"
                    "Two-inbox writing is short, factual, and low-heat. It "
                    "usually looks like: \"Football kit is in your car boot. "
                    "Match Saturday 10am.\" Not: \"You always forget the kit "
                    "and last Saturday was a disaster.\"\n\n"
                    "The upside compounds. Every Inbox-A message that lands "
                    "cleanly is a tiny deposit in the coordination account. "
                    "Every Inbox-B message that arrives dressed up as "
                    "Inbox-A is a small withdrawal."
                ),
                "takeaways": [
                    "Before sending, read your message and highlight only the facts your co-parent needs. Delete the rest.",
                    "If a message has more feelings than facts, park it in a note file for 24 hours.",
                    "End Inbox-A messages with what you'll do, not what you want them to do.",
                ],
            },
            {
                "slug": "kids-are-not-messengers",
                "title": "Kids aren't messengers",
                "read_minutes": 3,
                "summary": (
                    "\"Tell your mum…\" and \"Ask your dad…\" put your child "
                    "in the middle. Here's how to stop, kindly."
                ),
                "body": (
                    "Asking a child to carry information between homes feels "
                    "harmless — until you notice how often they arrive back "
                    "worried, or forget half of it, or feel responsible for "
                    "how the other parent reacts.\n\n"
                    "When children carry adult messages, they carry adult "
                    "emotion, too. \"Tell your dad we need money for the "
                    "school trip\" is not a sentence a nine-year-old can hold "
                    "without also holding a fear that dad might get cross.\n\n"
                    "The fix is simple, but not easy: adults message adults. "
                    "Direct, short, calm. When a message has to travel, use "
                    "the parenting app or email — not the child.\n\n"
                    "If your child does bring a message, receive it warmly, "
                    "then quietly move it to the adult channel. \"Thanks for "
                    "telling me — I'll message dad tonight so you don't have "
                    "to remember.\" You just returned them to being a child.\n\n"
                    "Watch too for messages that travel back the other way — "
                    "asking a child what happened in the other home, or how "
                    "the other parent seemed. Even gentle curiosity turns your "
                    "child into a small reporter."
                ),
                "takeaways": [
                    "Route every logistics message through the parenting app or email, never the child.",
                    "If your child does carry a message, thank them and quietly forward it adult-to-adult.",
                    "Notice \"So, how was mum today?\" and swap it for \"How was your day?\"",
                ],
            },
            {
                "slug": "the-24-hour-cool-down",
                "title": "The 24-hour cool-down draft",
                "read_minutes": 2,
                "summary": (
                    "The angriest message you ever send is the one that took "
                    "you 40 seconds to write."
                ),
                "body": (
                    "You know the feeling: something lands in your inbox that "
                    "makes your chest tight, and by the time your thumb has "
                    "opened the keyboard you're already halfway to a reply "
                    "you'll regret at 2am.\n\n"
                    "Give yourself a rule: no important message goes out the "
                    "same day it was written in anger. Write the draft — "
                    "absolutely, get it out of your body — but save it. Come "
                    "back to it the next morning with coffee and a clearer "
                    "chest.\n\n"
                    "Nine times out of ten you'll delete two paragraphs, soften "
                    "one sentence, and add the one fact you forgot. The message "
                    "that goes out is shorter, kinder, and much more likely to "
                    "get the answer you actually need.\n\n"
                    "This isn't about suppressing your feelings. The 24-hour "
                    "cool-down is a self-respect practice: your future self "
                    "will thank you every time, and your child never has to "
                    "read a screenshot of it years later."
                ),
                "takeaways": [
                    "Write angry drafts freely — just don't send them within 24 hours.",
                    "In the morning, ask: \"What outcome do I actually want from this message?\"",
                    "If a message doesn't move something forward for your child, don't send it at all.",
                ],
            },
            {
                "slug": "praise-in-front-of-them",
                "title": "Praise them in front of your child",
                "read_minutes": 2,
                "summary": (
                    "The single fastest way to lower your child's stress is "
                    "to say something warm about their other parent — out loud."
                ),
                "body": (
                    "Children carry a private worry that goes like this: "
                    "\"If I love them, does that mean I'm being disloyal to "
                    "you?\" They almost never say it. They just get quieter, "
                    "or angrier, or start losing sleep.\n\n"
                    "You can dissolve a lot of that with one habit: say "
                    "something warm about their other parent, in front of "
                    "them, at least once a week. It doesn't have to be huge. "
                    "\"Your dad's really good at packed lunches — mine are "
                    "boring.\" \"Mum knows way more about football than I do.\"\n\n"
                    "You're giving your child permission to love both of you "
                    "at the same time. That permission does more for their "
                    "long-term wellbeing than any perfectly-negotiated custody "
                    "schedule.\n\n"
                    "Two guardrails. First, don't force it — insincere praise "
                    "sounds fake to a nine-year-old. Second, if the other "
                    "parent is unsafe, protect your child; you can still find "
                    "one true, small thing to acknowledge (\"They picked good "
                    "music for you\") without endorsing behaviour that isn't ok."
                ),
                "takeaways": [
                    "Pick one small, true thing you appreciate about your co-parent this week and say it out loud.",
                    "Never say something warm about your co-parent that you don't actually mean.",
                    "Watch your child's shoulders — you'll often see them drop.",
                ],
            },
            {
                "slug": "the-magic-followup",
                "title": "The magic follow-up sentence",
                "read_minutes": 2,
                "summary": (
                    "\"Just checking I got that right\" turns arguments into "
                    "conversations."
                ),
                "body": (
                    "Half of co-parenting misunderstandings come from tiny "
                    "wording mismatches that compound. You wrote \"Friday "
                    "pickup at 5\", they read \"Friday I pick up at 5\", and "
                    "now the child is standing in a school hallway wondering "
                    "where their parents went.\n\n"
                    "Add one sentence to your messages: \"Just checking I got "
                    "that right — you're picking Alex up on Friday at 5?\" It "
                    "sounds redundant. It's not. It's a low-cost check that "
                    "catches misreadings before they turn into a Friday-night "
                    "crisis.\n\n"
                    "Same trick works in the other direction: \"Just so I've "
                    "understood — you'd like me to bring the medicine on "
                    "Sunday?\" You get one of three replies: \"Yes\", \"No, I "
                    "meant Monday\", or silence. All three are useful. Silence "
                    "means it's time to escalate to a call, not an assumption."
                ),
                "takeaways": [
                    "Add one \"just checking I got that right\" line to every logistics message.",
                    "If your co-parent goes silent on a check-back, call — don't guess.",
                    "Never turn a check-back into a jab (\"…because you got it wrong last time\").",
                ],
            },
        ],
    },
    {
        "slug": "boundaries",
        "name": "Healthy boundaries",
        "tagline": "Two homes, one child — clear lines protect all three.",
        "accent": "#1F5C3B",
        "articles": [
            {
                "slug": "boundaries-are-doors-not-walls",
                "title": "Boundaries are doors, not walls",
                "read_minutes": 2,
                "summary": (
                    "A boundary tells your co-parent what you'll do — not "
                    "what they must do."
                ),
                "body": (
                    "Boundaries in co-parenting almost never work when they "
                    "sound like rules for the other adult. \"You can't call "
                    "after 9pm\" is a wall — and walls invite people to try "
                    "the handle just to see if it turns.\n\n"
                    "Boundaries work when they describe what you'll do. \"I'll "
                    "keep my phone off after 9pm on nights the kids are with "
                    "you. If there's an emergency, dial twice — I'll pick up.\" "
                    "Same limit. Very different feel. One is a wall someone "
                    "wants to test; the other is a door with a clear knock.\n\n"
                    "Doors work because they lower the sense of control being "
                    "taken away. You're not policing the other parent's "
                    "behaviour — you're describing your availability. That "
                    "shifts the whole tone.\n\n"
                    "Write your boundaries the same way. \"I won't discuss "
                    "money in front of the kids — I'll respond to money "
                    "messages by 8pm the next day.\" \"I'll drop off ten "
                    "minutes early if the kids look regulated; five minutes "
                    "late if they're mid-meltdown.\"\n\n"
                    "It sounds like semantics. It isn't. Wall-boundaries "
                    "escalate; door-boundaries hold."
                ),
                "takeaways": [
                    "Rewrite each of your current \"you can't\" rules as an \"I will\" statement.",
                    "State the emergency exception up front so the door doesn't feel locked.",
                    "Notice which boundaries you keep having to defend — those are the ones written as walls.",
                ],
            },
            {
                "slug": "one-house-one-set-of-rules",
                "title": "One house, one set of rules",
                "read_minutes": 3,
                "summary": (
                    "Kids can absolutely live with two different homes. What "
                    "they can't do is live in one home with two conflicting rulebooks."
                ),
                "body": (
                    "It's tempting to want alignment on everything: bedtimes, "
                    "screen limits, homework rules, dessert rules. But children "
                    "adapt beautifully to \"at mum's we do this, at dad's we "
                    "do that\" — as long as the rules inside each home are "
                    "clear and predictable.\n\n"
                    "What genuinely destabilises children isn't difference "
                    "between homes. It's inconsistency inside a home. "
                    "Bedtime is 8:30 tonight, 9:30 tomorrow, whenever-you-want "
                    "on Sunday because you had a fight with your co-parent "
                    "and are too tired to enforce it.\n\n"
                    "Focus first on being predictable in your home. Written on "
                    "the fridge if it helps. Then, with your co-parent, pick "
                    "just two or three cross-home consistencies that matter "
                    "most — usually safety, medication, and how big transitions "
                    "are handled. Everything else can differ.\n\n"
                    "When your child pushes back with \"but at dad's I can…\", "
                    "the best response is warm and short: \"I know. And here "
                    "we do it this way. Both are fine.\" No competing, no "
                    "criticising."
                ),
                "takeaways": [
                    "Write down the 5 rules that are actually non-negotiable at your house.",
                    "Pick 2-3 cross-home consistencies to agree on — leave the rest be.",
                    "Practise the \"I know, and here we do it this way\" line.",
                ],
            },
            {
                "slug": "not-your-therapist",
                "title": "Your child is not your therapist",
                "read_minutes": 3,
                "summary": (
                    "The relief of venting to your child costs them far more "
                    "than you save."
                ),
                "body": (
                    "When you're exhausted and the person who most understands "
                    "the situation is a small, loyal, ever-present child, the "
                    "temptation to unload is enormous. Just a sentence. Just a "
                    "sigh. \"Your mother is impossible.\" \"I don't know how "
                    "we'll manage this month.\"\n\n"
                    "Children hear it all. Even the sighs. And because they "
                    "can't fix any of it, they store it — sometimes for years — "
                    "as a low, background hum of worry.\n\n"
                    "Find someone your own size. A friend, a therapist, a "
                    "coach, a support group, a journal. Not your child, not "
                    "even the older one, not even the wise one, not even the "
                    "one who \"gets it\".\n\n"
                    "This doesn't mean pretending everything is fine. Kids "
                    "read the room. Naming the weather is ok — \"Today's a bit "
                    "hard for me, but I've got it, and I love you\" — as long "
                    "as it comes with reassurance that you're the adult and "
                    "they're the child."
                ),
                "takeaways": [
                    "Name your top 3 adult confidants — actually text one this week.",
                    "When you catch yourself venting to your child, pause and swap the vent for a hug.",
                    "\"Today's a bit hard for me, but I've got it\" is enough — you don't owe them detail.",
                ],
            },
            {
                "slug": "the-front-door-transition",
                "title": "The front-door transition",
                "read_minutes": 2,
                "summary": (
                    "The first 20 minutes at pickup and drop-off shape the "
                    "whole weekend."
                ),
                "body": (
                    "Handovers are the highest-stress moments of the week for "
                    "most co-parenting families. Everyone's clock is different, "
                    "everyone's regulated differently, and children are often "
                    "trying to be brave for two adults at once.\n\n"
                    "Two small habits change everything. First: hand over on "
                    "the doorstep, not in the living room. Long-conversation "
                    "handovers give both adults enough time to notice something "
                    "irritating; short ones don't. If you must speak, keep it "
                    "to logistics and step back to the pavement.\n\n"
                    "Second: build a 20-minute soft landing on the receiving "
                    "side. No questions about the other home. No launching "
                    "into homework. A snack, a couch, maybe a shared silly "
                    "video. Ask them anything meaningful only after the 20 "
                    "minutes are up.\n\n"
                    "You can name the soft landing out loud — \"Welcome home, "
                    "here's your snack, we don't have to talk for 20 minutes.\" "
                    "Most kids exhale visibly."
                ),
                "takeaways": [
                    "Move all logistics conversations to the doorstep or the app — not inside either home.",
                    "Protect the first 20 minutes after every handover from questions and demands.",
                    "Ask about the other home only if your child brings it up first.",
                ],
            },
            {
                "slug": "new-partners-slowly",
                "title": "New partners, introduced slowly",
                "read_minutes": 2,
                "summary": (
                    "There's no perfect timeline, but there is a wrong speed."
                ),
                "body": (
                    "Two rules to hold, then everything else is judgement.\n\n"
                    "One: kids meet a new partner only after the relationship "
                    "is stable and serious enough that a break-up would be a "
                    "meaningful loss to you. Their attachment system is not "
                    "designed to bond with a rotating cast.\n\n"
                    "Two: your co-parent hears about it from you, not from "
                    "the child. Not because they have veto power — they "
                    "don't — but because your child will regulate the transition "
                    "much more easily if it isn't news to the other adult in "
                    "their life.\n\n"
                    "Everything else is judgement: how, when, what to call them, "
                    "how to introduce them, whether to sleep over the first "
                    "weekend. Err slower than feels necessary. Kids can always "
                    "get to know someone faster later; they can't unmeet them."
                ),
                "takeaways": [
                    "Ask yourself: would a break-up with this person be a real loss to me?",
                    "Tell your co-parent before you tell your child.",
                    "Slow is almost always kinder than fast — you can accelerate anytime.",
                ],
            },
        ],
    },
    {
        "slug": "mediation",
        "name": "Mediation prep",
        "tagline": "Walk in prepared, leave with a plan you'll actually keep.",
        "accent": "#8A6B12",
        "articles": [
            {
                "slug": "what-mediators-actually-do",
                "title": "What mediators actually do (and don't)",
                "read_minutes": 3,
                "summary": (
                    "A mediator is not a judge, a therapist, or your lawyer. "
                    "Knowing this changes how you prepare."
                ),
                "body": (
                    "Mediators are trained to help two people who disagree "
                    "arrive at a set of practical arrangements they can both "
                    "live with. That's it. That's their whole job.\n\n"
                    "They don't decide who's right. They don't diagnose "
                    "anyone. They don't give legal advice. They don't tell "
                    "one parent they're a better parent than the other. The "
                    "moment they try, they've stopped mediating and started "
                    "adjudicating.\n\n"
                    "Which means the people who get the most out of mediation "
                    "are the ones who arrive with two things: (1) clarity about "
                    "what they actually want out of the day, and (2) willingness "
                    "to hear a version of it they didn't picture.\n\n"
                    "Parents who arrive hoping the mediator will pick a side "
                    "leave disappointed. Parents who arrive hoping to build a "
                    "workable calendar tend to leave with one — even if it's "
                    "not the calendar they started the day imagining."
                ),
                "takeaways": [
                    "Write down 3 outcomes you would consider a good day.",
                    "Write down 1 outcome you would refuse — and know why.",
                    "Do not walk in expecting the mediator to declare a winner.",
                ],
            },
            {
                "slug": "the-one-page-brief",
                "title": "Write the one-page brief",
                "read_minutes": 3,
                "summary": (
                    "If you can't say your case in one page, you're not ready. "
                    "Here's the structure that always works."
                ),
                "body": (
                    "Before every mediation session, write yourself a one-page "
                    "brief. Not for the mediator — for you.\n\n"
                    "Four short sections:\n\n"
                    "1. **What my child needs.** Two or three sentences. "
                    "Concrete: sleep, stability, contact with both parents, "
                    "predictability around school, medical continuity.\n\n"
                    "2. **What I want to leave the day with.** Three things "
                    "max. Concrete: a school-holiday plan, an agreement on "
                    "medical decisions, a written pickup schedule.\n\n"
                    "3. **What I'm willing to give.** Three things. If you "
                    "arrive giving nothing, the day will not move. Choose "
                    "trades in advance so you're not doing it in the heat.\n\n"
                    "4. **What I refuse — and why in one sentence.** Non-"
                    "negotiables. The \"why\" is the child's need, not your "
                    "preference.\n\n"
                    "That's the whole brief. Keep it in front of you. If a "
                    "conversation starts drifting into old wounds, glance at "
                    "it. You wrote it exactly for that moment."
                ),
                "takeaways": [
                    "Draft the one-page brief this week — even if mediation is months away.",
                    "Make \"what I'm willing to give\" as long as \"what I want\".",
                    "Every non-negotiable must have a child-centred reason.",
                ],
            },
            {
                "slug": "regulate-then-negotiate",
                "title": "Regulate, then negotiate",
                "read_minutes": 2,
                "summary": (
                    "A dysregulated parent is a bad negotiator. The 10 minutes "
                    "before you walk in matter more than you think."
                ),
                "body": (
                    "You cannot think clearly with a racing heart, and you "
                    "cannot advocate for your child with a locked jaw. "
                    "Regulation isn't a wellness suggestion — it's a "
                    "negotiation prerequisite.\n\n"
                    "Ten minutes before the session, do something boringly "
                    "physical. Walk around the building. Splash cold water on "
                    "your wrists. Slow your exhale to twice the length of your "
                    "inhale for two minutes. Yes, really. It works because it "
                    "works.\n\n"
                    "Once you're inside, notice the first sign of "
                    "dysregulation early: tight shoulders, shortening breath, "
                    "a jump in your pulse, a spike of certainty that the other "
                    "person is being unreasonable. Ask for a five-minute break "
                    "the moment you notice. Every mediator will honour it. "
                    "The best negotiators use them liberally."
                ),
                "takeaways": [
                    "Plan a 10-minute regulation ritual for right before the session.",
                    "Give yourself explicit permission to ask for breaks — mediators expect it.",
                    "The moment certainty spikes (\"they're being ridiculous!\") is the moment to breathe.",
                ],
            },
            {
                "slug": "the-two-hats",
                "title": "Two hats: parent and party",
                "read_minutes": 2,
                "summary": (
                    "You are simultaneously a party in a negotiation and a "
                    "parent to a child. When those two roles argue, the "
                    "parent hat wins."
                ),
                "body": (
                    "You will feel two pulls in every mediation. The party-"
                    "hat pull says: win, protect what's mine, don't get "
                    "played. The parent-hat pull says: what will actually "
                    "let my child thrive on Wednesday nights?\n\n"
                    "Most bad mediation outcomes happen when the party hat "
                    "wins the internal fight. You leave with a technically-"
                    "correct arrangement that doesn't actually work for a "
                    "seven-year-old.\n\n"
                    "Before you agree to any point, ask yourself out loud "
                    "if it helps: \"Wearing my parent hat, is this good for "
                    "my child on a Wednesday night?\" If the answer is yes, "
                    "sign. If the answer is \"well, it's what I want\", "
                    "pause.\n\n"
                    "This isn't about being a martyr. Your own wellbeing "
                    "matters — an exhausted parent is not good for a child. "
                    "It's about which hat gets to break the tie."
                ),
                "takeaways": [
                    "Before every agreement, silently ask: \"parent hat — is this good on a Wednesday night?\"",
                    "Notice when the party hat is louder — that's the moment to slow down.",
                    "Bring a photo of your child in your wallet. Look at it during breaks.",
                ],
            },
            {
                "slug": "write-it-down-that-day",
                "title": "Write it down that day",
                "read_minutes": 2,
                "summary": (
                    "The best-mediated agreement in the world evaporates by "
                    "Wednesday if it's only in your head."
                ),
                "body": (
                    "By the time you leave the session you'll be tired, "
                    "hungry, and half-processing the day. Do one thing before "
                    "you sleep: write the agreement down in your own words in "
                    "one place both parents can find.\n\n"
                    "The parenting app is ideal. A shared document works. A "
                    "screenshot on both phones will do in a pinch. What "
                    "doesn't work is \"we both know what we agreed\" — you "
                    "don't, because human memory is not a scanner.\n\n"
                    "Include: the actual arrangement, who's responsible for "
                    "what, dates it starts and ends, and how it gets reviewed. "
                    "Two lines is fine. Three is better. Nine paragraphs is a "
                    "sign the session isn't finished.\n\n"
                    "Then, and only then, sleep."
                ),
                "takeaways": [
                    "Write the agreement in one shared place the same night — no exceptions.",
                    "Add a review date so no arrangement lives forever without a check-in.",
                    "If you can't write it in two lines, the deal isn't clear enough — go back.",
                ],
            },
        ],
    },
]


def get_hub(slug: str) -> Optional[Dict[str, Any]]:
    for hub in HUBS:
        if hub["slug"] == slug:
            return hub
    return None


def get_article(hub_slug: str, article_slug: str) -> Optional[Dict[str, Any]]:
    hub = get_hub(hub_slug)
    if not hub:
        return None
    for a in hub["articles"]:
        if a["slug"] == article_slug:
            return {**a, "hub_slug": hub_slug, "hub_name": hub["name"]}
    return None


def find_article(article_slug: str) -> Optional[Dict[str, Any]]:
    """Locate an article by slug across all hubs. Returns hub-context enriched."""
    for hub in HUBS:
        for a in hub["articles"]:
            if a["slug"] == article_slug:
                return {**a, "hub_slug": hub["slug"], "hub_name": hub["name"]}
    return None


def hubs_summary() -> List[Dict[str, Any]]:
    """Lightweight card payload for the /learning index — no article bodies."""
    return [
        {
            "slug": h["slug"],
            "name": h["name"],
            "tagline": h["tagline"],
            "accent": h["accent"],
            "article_count": len(h["articles"]),
            "articles": [
                {
                    "slug": a["slug"],
                    "title": a["title"],
                    "summary": a["summary"],
                    "read_minutes": a["read_minutes"],
                }
                for a in h["articles"]
            ],
        }
        for h in HUBS
    ]
