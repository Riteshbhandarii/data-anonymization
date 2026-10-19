"""Deterministic corpus of CONTEXTUAL identifiers with exact character labels.

Regex already catches emails and IBANs. This corpus measures what has no fixed
format: permit numbers, contract references, business IDs, internal project and
system names, identifying phrases, and details hidden in notes or comments.

Every person, company, number and system here is fictional. Documents are built
from paragraph templates with slots, so offsets come from the rendering step and
cannot drift from the text.

    python -m eval.contextual_corpus --out DIR --seed 42

Offsets are Python string indices (Unicode code points) into the .md file read
as UTF-8 with newlines left untouched.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from itertools import pairwise
from pathlib import Path

LANGUAGES = ("en", "fi")
DOCS_PER_LANGUAGE = 12
DEV_PER_LANGUAGE = 3

# Real partner companies. They must never appear in generated text.
BANNED = ("Swegon", "CTI", "Dinolift", "Kuusi Audit")

CONTEXTUAL_CATEGORIES = (
    "LICENCE",
    "CONTRACT",
    "BUSINESS_ID",
    "PROJECT",
    "SYSTEM",
    "QUASI",
    "HIDDEN",
)
CATEGORIES = CONTEXTUAL_CATEGORIES + ("STANDARD",)

# Slot prefix in a template -> label category.
SLOT_CATEGORY = {
    "PER": "STANDARD",
    "MAIL": "STANDARD",
    "PHONE": "STANDARD",
    "LIC": "LICENCE",
    "CON": "CONTRACT",
    "BIZ": "BUSINESS_ID",
    "VAT": "BUSINESS_ID",
    "PRJ": "PROJECT",
    "SYS": "SYSTEM",
    "TEN": "SYSTEM",
    "HOST": "SYSTEM",
    "REPO": "SYSTEM",
    "QUP": "QUASI",
    "QUC": "QUASI",
    "HID": "HIDDEN",
}

# {PER1} or {PER1.gen} -> labelled slot; [[kind:text]] -> decoy.
TOKEN = re.compile(r"\{([A-Z]+)(\d*)(?:\.([a-z]+))?\}|\[\[([a-z_]+):(.*?)\]\]", re.DOTALL)


# ---------------------------------------------------------------- value pools


def _letters(rng, n):
    return "".join(rng.choice("ABCDEFGHKLMNPRSTVW") for _ in range(n))


def _year(rng):
    return rng.randint(2018, 2025)


def _licence(rng, lang):
    y, n = _year(rng), rng.randint(100, 9999)
    if lang == "en":
        options = [
            f"ENV-{y}-{n:04d}/{_letters(rng, 2)}",
            f"BP/{y}/{n:05d}-{_letters(rng, 1)}",
            f"LIC-{rng.choice(['WW', 'AIR', 'WST'])}-{n:05d}",
            f"EP{rng.randint(10, 99)}/{n}/{y}",
            f"PRM {y}:{n}",
        ]
    else:
        options = [
            f"YSL-{y}-{n:04d}",
            f"LSSAVI/{n}/{y}",
            f"RAK-{y}-{n:04d}-{_letters(rng, 1)}",
            f"LUPA {y}/{n}-{rng.randint(10, 99)}",
            f"JHL{rng.randint(10, 99)}/{n}/{y}",
        ]
    return rng.choice(options)


def _contract(rng, lang):
    y, n = _year(rng), rng.randint(100, 999999)
    if lang == "en":
        options = [
            f"PO-{y}-{n:06d}",
            f"CTR/{y}/{n % 10000:04d}",
            f"INC{n:07d}",
            f"SA-{n % 100000:05d}",
            f"CASE-{_letters(rng, 2)}-{n % 100000:05d}",
            f"ORD-{n % 10000:04d}-{_letters(rng, 2)}",
        ]
    else:
        options = [
            f"KS-{y}-{n % 10000:04d}",
            f"4500{n:06d}",
            f"SOP-{n % 100000:05d}",
            f"TKT-{n:06d}",
            f"DNRO {y}/{n % 10000:04d}",
            f"TIL-{n % 10000:04d}-{_letters(rng, 2)}",
        ]
    return rng.choice(options)


def _business_digits(rng):
    """Seven digits starting with 9 plus a valid Finnish check digit.

    Finnish business IDs do not start with 9 in practice, so these should not
    belong to a real company. The check digit keeps them syntactically valid.
    """
    while True:
        base = 9000000 + rng.randint(0, 999999)
        digits = [int(c) for c in f"{base:07d}"]
        total = sum(d * w for d, w in zip(digits, (7, 9, 10, 5, 8, 4, 2)))
        rest = total % 11
        if rest == 1:
            continue
        check = 0 if rest == 0 else 11 - rest
        return f"{base:07d}", str(check)


def _business_id(rng, lang):
    base, check = _business_digits(rng)
    return f"{base}-{check}"


def _vat(rng, lang):
    base, check = _business_digits(rng)
    digits = base + check
    return rng.choice([f"FI{digits}", f"FI {digits[:4]} {digits[4:]}", f"FI {digits[:3]} {digits[3:6]} {digits[6:]}"])


def _tenant(rng, lang):
    return f"{rng.choice(['HLS', 'KRV', 'OLM', 'TVA', 'NRD', 'PLK'])}-{rng.choice(['PRD', 'QA'])}-{rng.randint(1, 12):02d}"


def _system_phrase(rng, lang):
    return f"{rng.choice(['ERP tenant', 'WMS instance', 'CRM sandbox'])} {_tenant(rng, lang)}"


def _host(rng, lang):
    return (
        f"{rng.choice(['hel', 'tku', 'tre', 'oul'])}-{rng.choice(['db', 'app', 'fs', 'batch'])}"
        f"-{rng.choice(['prod', 'qa'])}-{rng.randint(1, 19):02d}"
    )


def _phone(rng, lang):
    if lang == "en" and rng.random() < 0.5:
        return f"+44 20 7946 {rng.randint(0, 999):04d}"
    prefix = rng.choice(["040", "044", "050"])
    rest = f"{rng.randint(100, 999)} {rng.randint(1000, 9999)}"
    if rng.random() < 0.4:
        return f"+358 {prefix[1:]} {rest}"
    return f"{prefix} {rest}"


EN_PEOPLE = [
    "Hannah Clarke", "Oliver Bennett", "Priya Nair", "Tomas Eklund", "Marta Kowalski",
    "Daniel Okafor", "Eleanor Whitfield", "Lars Henriksen", "Sofia Marin", "Callum Reid",
]  # fmt: skip

# Finnish people: forms for the cases the templates use.
_FI_PEOPLE_RAW = [
    ("Mikko Lehtonen", "Lehtosen", "Lehtoselle", "Lehtosesta", "Lehtosta"),
    ("Sanna Virtanen", "Virtasen", "Virtaselle", "Virtasesta", "Virtasta"),
    ("Jari Koskinen", "Koskisen", "Koskiselle", "Koskisesta", "Koskista"),
    ("Tiina Heikkilä", "Heikkilän", "Heikkilälle", "Heikkilästä", "Heikkilää"),
    ("Antti Mäkelä", "Mäkelän", "Mäkelälle", "Mäkelästä", "Mäkelää"),
    ("Johanna Nieminen", "Niemisen", "Niemiselle", "Niemisestä", "Niemistä"),
    ("Pekka Salmela", "Salmelan", "Salmelalle", "Salmelasta", "Salmelaa"),
    ("Laura Hämäläinen", "Hämäläisen", "Hämäläiselle", "Hämäläisestä", "Hämäläistä"),
    ("Ville Rantanen", "Rantasen", "Rantaselle", "Rantasesta", "Rantasta"),
    ("Kaisa Laine", "Laineen", "Laineelle", "Laineesta", "Lainetta"),
]


def _fi_person(full, gen, all_, ela, par):
    first = full.split()[0]
    return {
        "nom": full,
        "gen": f"{first} {gen}",
        "all": f"{first} {all_}",
        "ela": f"{first} {ela}",
        "par": f"{first} {par}",
    }


FI_PEOPLE = [_fi_person(*row) for row in _FI_PEOPLE_RAW]

_MAIL_DOMAINS = {
    "en": ["tidewater-logistics.example", "brindle-and-oak.example", "greyfriars-supply.example"],
    "fi": ["harjula-kuljetus.example", "pohjolan-pakkaus.example", "saarelan-huolto.example"],
}


def _fold(text):
    table = str.maketrans("äöåÄÖÅ", "aoaAOA")
    return text.translate(table).lower().replace(" ", ".")


def _mail(rng, lang, person=None):
    pool = EN_PEOPLE if lang == "en" else [p["nom"] for p in FI_PEOPLE]
    return f"{_fold(person or rng.choice(pool))}@{rng.choice(_MAIL_DOMAINS[lang])}"


EN_PROJECTS = [
    "Project Kestrel", "Project Larkspur", "Project Ironwood", "Project Saltmarsh",
    "Project Bluebell", "Project Tern", "Project Granite",
]  # fmt: skip

_FI_PROJECTS_RAW = [
    ("Tähtisumu", "Tähtisumun", "Tähtisumussa", "Tähtisumuun", "Tähtisumusta"),
    ("Kalliokotka", "Kalliokotkan", "Kalliokotkassa", "Kalliokotkaan", "Kalliokotkasta"),
    ("Pohjantähti", "Pohjantähden", "Pohjantähdessä", "Pohjantähteen", "Pohjantähdestä"),
    ("Jäänmurtaja", "Jäänmurtajan", "Jäänmurtajassa", "Jäänmurtajaan", "Jäänmurtajasta"),
    ("Meriharakka", "Meriharakan", "Meriharakassa", "Meriharakkaan", "Meriharakasta"),
    ("Lumikello", "Lumikellon", "Lumikellossa", "Lumikelloon", "Lumikellosta"),
]
FI_PROJECTS = [dict(zip(("nom", "gen", "ine", "ill", "ela"), row)) for row in _FI_PROJECTS_RAW]

EN_REPOS = [
    "atlas-pricing", "lumen-invoice-sync", "birch-route-planner", "ledger-bridge",
    "tarn-reporting", "fennel-stock-api",
]  # fmt: skip

EN_HIDDEN = [
    "Harbourline Shipping Ltd", "Ostrobothnia Cold Chain Ltd", "Valmark Foods Ltd",
    "Brindle & Oak Hotels", "Tidewater Marine Services", "Northfield Dairy Cooperative",
]  # fmt: skip


def _oy(stem):
    name = f"{stem} Oy"
    return {
        "nom": name,
        "gen": f"{name}:n",
        "ela": f"{name}:stä",
        "ade": f"{name}:llä",
        "par": f"{name}:tä",
        "all": f"{name}:lle",
    }


FI_HIDDEN = [
    _oy(s) for s in (
        "Pellonpään Pakkaus", "Kyröskosken Kylmäkuljetus", "Lehtimäen Meijeri",
        "Vaaranlinnan Kalatuote", "Harjavuoren Hotellit", "Saaristomeren Varustamo",
    )
]  # fmt: skip

EN_QUASI_PERSON = [
    "the only female site manager at our Salo plant since 2019",
    "the night-shift supervisor at the Kemi depot who reported the audit leak",
    "the welding engineer from the Rauma yard who found the cracked seam on line 4",
    "the former buyer at the Pori harbour office who now runs our main subcontractor",
    "the only data protection officer in the Tampere unit with over ten years at the company",
]  # fmt: skip

EN_QUASI_COMPANY = [
    "our largest customer in Oulu, the one that switched suppliers in March",
    "the regional distributor owned by two sisters from Raahe",
    "the only bakery in Kajaani that still takes pallet deliveries",
    "the dairy cooperative in Vaasa whose warehouse burned down in January",
]  # fmt: skip


def _fi_phrase(nom, gen, par, ela):
    return {"nom": nom, "gen": gen, "par": par, "ela": ela}


def _fi_relative(head_forms, tail):
    return _fi_phrase(*(f"{form}, {tail}" for form in head_forms))


FI_QUASI_PERSON = [
    _fi_relative(
        (
            "Salon tehtaan ainoa naispuolinen työnjohtaja",
            "Salon tehtaan ainoan naispuolisen työnjohtajan",
            "Salon tehtaan ainoaa naispuolista työnjohtajaa",
            "Salon tehtaan ainoasta naispuolisesta työnjohtajasta",
        ),
        "joka aloitti vuonna 2019",
    ),
    _fi_relative(
        (
            "Kemin varaston yövuoron esimies",
            "Kemin varaston yövuoron esimiehen",
            "Kemin varaston yövuoron esimiestä",
            "Kemin varaston yövuoron esimiehestä",
        ),
        "joka ilmoitti auditoinnissa havaitusta vuodosta",
    ),
    _fi_relative(
        (
            "Rauman telakan hitsausinsinööri",
            "Rauman telakan hitsausinsinöörin",
            "Rauman telakan hitsausinsinööriä",
            "Rauman telakan hitsausinsinööristä",
        ),
        "joka löysi linjan 4 halkeaman",
    ),
    _fi_relative(
        (
            "Porin satamatoimiston entinen ostaja",
            "Porin satamatoimiston entisen ostajan",
            "Porin satamatoimiston entistä ostajaa",
            "Porin satamatoimiston entisestä ostajasta",
        ),
        "joka perusti nykyisen alihankkijamme",
    ),
    _fi_relative(
        (
            "Tampereen yksikön ainoa tietosuojavastaava",
            "Tampereen yksikön ainoan tietosuojavastaavan",
            "Tampereen yksikön ainoaa tietosuojavastaavaa",
            "Tampereen yksikön ainoasta tietosuojavastaavasta",
        ),
        "joka on työskennellyt talossa yli kymmenen vuotta",
    ),
]

FI_QUASI_COMPANY = [
    _fi_relative(
        (
            "Oulun suurin asiakkaamme",
            "Oulun suurimman asiakkaamme",
            "Oulun suurinta asiakastamme",
            "Oulun suurimmasta asiakkaastamme",
        ),
        "joka vaihtoi toimittajaa maaliskuussa",
    ),
    _fi_relative(
        (
            "Raahelaisten sisarusten omistama alueellinen jälleenmyyjä",
            "Raahelaisten sisarusten omistaman alueellisen jälleenmyyjän",
            "Raahelaisten sisarusten omistamaa alueellista jälleenmyyjää",
            "Raahelaisten sisarusten omistamasta alueellisesta jälleenmyyjästä",
        ),
        "joka voitti viime syksyn tarjouskilpailun",
    ),
    _fi_relative(
        (
            "Kajaanin ainoa leipomo",
            "Kajaanin ainoan leipomon",
            "Kajaanin ainoaa leipomoa",
            "Kajaanin ainoasta leipomosta",
        ),
        "jonka omistaja on entinen kaupunginvaltuutettu",
    ),
    _fi_relative(
        (
            "Vaasan osuusmeijeri",
            "Vaasan osuusmeijerin",
            "Vaasan osuusmeijeriä",
            "Vaasan osuusmeijeristä",
        ),
        "jonka varasto paloi tammikuussa",
    ),
]

# prefix -> language -> list of entries or generator(rng, lang)
POOLS = {
    "PER": {"en": EN_PEOPLE, "fi": FI_PEOPLE},
    "MAIL": {"en": _mail, "fi": _mail},
    "PHONE": {"en": _phone, "fi": _phone},
    "LIC": {"en": _licence, "fi": _licence},
    "CON": {"en": _contract, "fi": _contract},
    "BIZ": {"en": _business_id, "fi": _business_id},
    "VAT": {"en": _vat, "fi": _vat},
    "PRJ": {"en": EN_PROJECTS, "fi": FI_PROJECTS},
    "SYS": {"en": _system_phrase, "fi": _system_phrase},
    "TEN": {"en": _tenant, "fi": _tenant},
    "HOST": {"en": _host, "fi": _host},
    "REPO": {"en": EN_REPOS, "fi": EN_REPOS},
    "QUP": {"en": EN_QUASI_PERSON, "fi": FI_QUASI_PERSON},
    "QUC": {"en": EN_QUASI_COMPANY, "fi": FI_QUASI_COMPANY},
    "HID": {"en": EN_HIDDEN, "fi": FI_HIDDEN},
}


def _entry(value):
    return value if isinstance(value, dict) else {"nom": value}


def _draw(rng, prefix, lang, used):
    pool = POOLS[prefix][lang]
    if callable(pool):
        for _ in range(100):
            entry = _entry(pool(rng, lang))
            if entry["nom"] not in used:
                return entry
        raise RuntimeError(f"cannot draw a distinct {prefix} value")
    options = [_entry(item) for item in pool if _entry(item)["nom"] not in used]
    return rng.choice(options)


# ------------------------------------------------------------------ templates

EN_TEMPLATES = [
    # 01 internal memo: permit
    """# Internal memo: effluent permit renewal

**To:** Facilities and compliance team
**From:** {PER1} ({MAIL1})
**Subject:** Renewal timeline

Team,

The effluent permit for the plant, reference {LIC1}, expires at the end of the year. The authority expects renewal applications at least six months ahead, so we are already behind the usual practice. I have asked Legal to prepare the filing together with {PRJ1}, which also covers the new cooling circuit.

Three things have to happen before submission:

1. Monitoring data for the last 24 months must be exported from {SYS1} and checked by the [[role:environmental specialist]].
2. The discharge limits in the draft must match the commitments we made under [[standard:ISO 14001]] in the last audit round.
3. Any change to the pump layout must appear in the drawings before they go to the authority.

Please quote {LIC1} in every message to the authority, otherwise the case officer cannot find our file. I will chase the missing signatures this week.

{PER1}
""",
    # 02 email: framework agreement
    """Subject: Re: Framework agreement, open points
From: {PER1}
To: Procurement

Hi all,

Following yesterday's call, here is where we stand on the framework agreement ({CON1}). The supplier's company ID is {BIZ1} in our records, but their invoices still show an older trading name, so please do not change the vendor master until finance confirms.

On the commercial side, {QUC1} has been pushing hard on payment terms, and I think we can agree to 30 days if they accept a weekly floor of [[quantity:12 pallets]]. Anything beyond that needs sign-off from the [[role:finance director]].

Two open items remain in the annexes: the notice period for price changes and the penalty for late deliveries. I suggest we park them until the payment terms are settled, otherwise the discussion splits in too many directions.

I will send the revised draft tomorrow. Call me on {PHONE1} if you want to go through it first.

Regards,
{PER1}
""",
    # 03 meeting notes: weekly sync
    """# Weekly operations sync: notes

**Attendees:** {PER1}, {PER2}, plus two people from IT
**Length:** 30 minutes

## Updates

- {PRJ1}: the pilot moves to the second line next week. We still wait for one more sign-off.
- Cutover of the order system to {SYS1} slips by a week because the test data was incomplete.
- Ticket {CON1} (label printer drivers) is still open. IT promises a fix by Thursday.
- Returned stock is still sitting in [[place:the warehouse]], and the count is off by [[quantity:three pallets]].

## Discussion

We talked about the risk that {QUP1} is stretched too thin after covering two shifts. Nobody wants a repeat of last winter.

## Actions

- {PER2} chases the supplier about the missing paperwork.
- Everyone reads the one-page summary of [[law:GDPR Article 6]] before the next workshop.
""",
    # 04 short report: supplier qualification
    """# Supplier qualification report: packaging

## 1. Summary

We reviewed the packaging supplier shortlisted under {PRJ1}. The supplier is registered under company ID {BIZ1} and holds waste-handling permit {LIC1}. Both were checked against the public registers during the review. The aim was to find out whether the supplier can grow its volumes without losing quality, so we also looked at contract documents and a year of delivery tracking. Their current supply agreement with us is {CON1}.

## 2. Findings

| Area | Result |
|---|---|
| Quality system | Certified to [[standard:ISO 9001]] |
| Delivery performance | 96 % on time over the last year |
| Capacity | Can absorb [[quantity:40 pallets]] per week |

The audit did not find any critical deviations. Two minor findings relate to document control and are tracked by the [[role:quality manager]].

## 3. Recommendation

Approve the supplier for the pilot volume and review again after six months. Questions to {PER1}, {MAIL1}.
""",
    # 05 slide deck with speaker notes
    """# Offer presentation: cold-chain monitoring

---

## Slide 1: The offer

- Sensor network for chilled transport
- Dashboard with alerts, code kept in the repo `{REPO1}`
- Pilot in [[place:Finland]] first, wider rollout later

**Speaker notes:** Keep this slide short. Mention that the work runs internally as {PRJ1}, but do not read the code name out to the customer. Spend the saved time on the alert examples.

---

## Slide 2: Timeline

- Month 1: install sensors in [[quantity:15 trucks]]
- Month 3: first monthly report
- Month 6: decision on the wider rollout

**Speaker notes:** The customer is really {HID1}, although the invitation only says "a large food company". Do not name them in the shared copy of this deck. The VAT number for the quote is {VAT1}. The contact for questions is {PER1}, {PHONE1}.
""",
    # 06 tracked changes / comment style
    """# Draft service agreement: tracked changes view

Clause 4.2 ~~The supplier shall deliver within 10 days~~ **The supplier shall deliver within [[quantity:14 days]]** of a written order.

> **Comment ({PER1}):** The new period only works for us if the order is placed under {CON1}. Please ask the supplier to repeat that reference on every confirmation.

Clause 7 ~~Liability is unlimited.~~ **Liability is capped at the annual fee.**

> **Comment (Legal):** The cap is acceptable under [[law:the Sale of Goods Act]]. Nothing further from my side.

Clause 9 The supplier confirms that it holds the operating permit {LIC1}.

> **Note:** The counterparty in this draft is really acting for {HID1}. The board has not approved naming them in the document that goes out, so the name stays in this comment thread only and must be stripped before sending.

> **Comment ({PER2}):** I will send my own edits to {MAIL1} tonight.
""",
    # 07 incident email
    """Subject: Order portal outage, follow-up
From: {PER1} <{MAIL1}>

Hello,

A short summary of last night's outage. The order portal stopped taking new orders at about 02:10 because the database on {HOST1} ran out of disk space. The batch job that archives old orders had been failing silently for weeks. The incident is tracked as {CON1}.

The fix was done by hand during the night: we freed space, restarted the service and replayed the queued orders. No orders were lost. The disk alert rules live in the repo `{REPO1}` and will be tightened this week.

{QUP1.cap} was the first to notice and phoned the [[role:on-call engineer]], which is why the downtime stayed under an hour. Portal [[version:version 2.1]] does not yet surface archive errors to users, but that is planned for the next release.

Regards,
{PER1}
""",
    # 08 memo: tool migration
    """# Memo: moving the planning team to the new tools

The planning team moves to the new tool during {PRJ1}. Accounts are created by invitation in {SYS1}, and every user receives written instructions by email. For [[quantity:two weeks]] after the switch the old system stays available in read-only mode.

A few people need extra support. {QUP1.cap} has asked for a longer handover period, and I think that is reasonable, because the work is tied closely to the old register. We also need to agree who supports {QUP2} when the old register is closed.

Personal data is processed in the new tool on the basis of [[law:GDPR Article 6]], and the [[role:team lead]] is responsible for the local instructions.

For questions or accounts, contact {PER1} on {PHONE1} or at {MAIL1}. Please do not forward this memo outside the planning team until the schedule is confirmed.
""",
    # 09 invoice email with hidden note
    """Subject: Invoice query, order {CON1}

Hello,

We received an invoice for order {CON1}, but the supplier details do not match our vendor file. The invoice shows company ID {BIZ1}, while the vendor file lists the same business under VAT number {VAT1}. These should be one and the same entity, so I assume one of the two records contains a typing error. Could you confirm which one is right before we release a payment of [[quantity:EUR 8,400]]?

We have seen the same problem before, so I suggest we check the whole vendor file in one go. If you have a current registry extract, please attach it to your reply and we can correct both records at once.

Our payment run closes on Friday, and the [[role:accounts payable clerk]] needs your answer by Thursday at the latest.

Thanks,
{PER1}
{MAIL1}

Note: this invoice is really for the {HID1} account, which we handle through an intermediary supplier at the customer's request. Do not mention the end customer in anything that goes to the supplier.
""",
    # 10 meeting notes: safety committee
    """# Safety committee: minutes

**Present:** {PER1}, {PER2} and the [[role:safety representative]]

## Items

- Lifting equipment: the crane inspection certificate {LIC1} is valid until June.
- A near miss at the loading area was written up by {QUP1}. The committee asked for the report to be circulated to all shift leads.
- Incident logging moves to {SYS1} from next month.
- The forklift trial with [[quantity:two forklifts]] belongs to {PRJ1}. Results go into the management review that follows [[standard:ISO 45001]] requirements.

## Decisions

The trial continues for another month. The committee will not decide on a purchase before the results are in. The next meeting is in four weeks, and the agenda is open until the end of the week.
""",
    # 11 quarterly supplier review
    """# Quarterly supplier review

## Overview

Three suppliers were reviewed this quarter. The review used contract documents, quality audits and delivery tracking. Details for the two suppliers with open points follow below.

## Supplier A

Company ID {BIZ1}. The transport licence number is {LIC1}. The contract {CON1} runs until the end of next year. Deliveries arrive at [[place:the main warehouse]] and the audit found nothing unusual.

## Supplier B

Supplier B is {QUC1}, and the relationship has lasted [[quantity:18 months]]. Delivery quality is steady, but the audit found gaps in the document trail and the supplier has no [[standard:ISO 9001]] certificate yet.

## Recommendation

Supplier A continues unchanged. Supplier B is asked for a corrective plan within one month, and the procurement group takes the final decision at its meeting.

## Contact

{PER1}, {PHONE1}
""",
    # 12 steering deck
    """# Steering group update

**Presenter:** {PER1}, {MAIL1}

---

## Slide 1: Status

- {PRJ1}: on track
- Data has been migrated to {SYS1}
- Next review in [[quantity:six weeks]]

**Speaker notes:** The sponsor we cannot name on the slide is {HID1}. Say only "a strategic partner". Keep the tone calm; nobody outside this group has been told about the budget change.

---

## Slide 2: Risks

- Key-person dependency
- Version [[version:3.4]] of the planning tool is out of support

**Speaker notes:** The key-person risk concerns {QUP1}. Do not say this aloud, it is a sensitive staffing matter. Questions from the audience go to the [[role:programme manager]].

---

## Slide 3: Next steps

- Budget proposal for the steering group
- Updated risk register
- Communication plan for staff

**Speaker notes:** Go through the steps quickly. The main point is to get approval for the communication plan before anything is said to staff.
""",
]

FI_TEMPLATES = [
    # 01 muistio: ympäristölupa
    """# Sisäinen muistio: jätevesilupa uusittava

**Vastaanottaja:** Tilat ja vaatimustenmukaisuus
**Lähettäjä:** {PER1} ({MAIL1})
**Aihe:** Lupahakemuksen aikataulu

Hei tiimi,

tehtaan jätevesilupa, lupatunnus {LIC1}, päättyy vuoden lopussa. Viranomainen odottaa uusimishakemuksen vähintään kuusi kuukautta etukäteen, joten olemme jo myöhässä tavanomaisesta aikataulusta. Hakemus valmistellaan {PRJ1.gen} yhteydessä, koska se kattaa myös uuden jäähdytyspiirin.

Ennen jättämistä on tehtävä kolme asiaa:

1. Viimeisen 24 kuukauden seurantatiedot viedään ERP-ympäristöstä {TEN1}, ja [[role:ympäristöasiantuntija]] tarkistaa ne.
2. Päästörajojen on vastattava viimeisellä auditointikierroksella antamiamme sitoumuksia, jotka perustuvat standardiin [[standard:ISO 14001]].
3. Pumppuasettelun muutokset on päivitettävä piirustuksiin ennen kuin ne lähtevät viranomaiselle.

Lisäksi hakemukseen liitetään selvitys nykyisestä jätevesien käsittelystä sekä yhteenveto viime vuoden poikkeamista. Käsittelijä on aiemmin pyytänyt lisätietoja erityisesti kemikaalien varastoinnista, joten kokoamme nekin valmiiksi. Jos aineistosta puuttuu jotain, ilmoita siitä minulle mahdollisimman pian.

Mainitse lupatunnus {LIC1} jokaisessa viranomaiselle lähtevässä viestissä, muuten käsittelijä ei löydä asiaamme. Selvitän puuttuvat allekirjoitukset tällä viikolla.

{PER1}
""",
    # 02 sähköposti: puitesopimus
    """Aihe: VS: Puitesopimuksen avoimet kohdat
Lähettäjä: {PER1}
Vastaanottaja: Hankinta

Hei kaikki,

eilisen puhelun jälkeen tilanne puitesopimuksen ({CON1}) osalta on tämä. Toimittajan Y-tunnus on kirjanpidossamme {BIZ1}, mutta laskuilla on edelleen vanha kauppanimi, joten toimittajarekisteriä ei pidä muuttaa ennen kuin talousosasto on vahvistanut asian.

Sopimuksen liitteissä on edelleen kaksi avointa kohtaa, jotka koskevat hinnanmuutosten ilmoitusaikaa ja toimitusten viivästyssakkoja. Ehdotan, että käsittelemme ne vasta, kun maksuehdot on saatu lukkoon, koska muuten keskustelu hajoaa liian moneen suuntaan.

Kaupallisesti {QUC1.nom}, on painostanut maksuehdoista. Uskon, että voimme hyväksyä 30 päivän maksuajan, jos he hyväksyvät viikoittaiseksi vähimmäismääräksi [[quantity:12 lavaa]]. Kaikki tämän ylittävä vaatii [[role:talousjohtajan]] hyväksynnän.

Lähetän päivitetyn luonnoksen huomenna. Soita numeroon {PHONE1}, jos haluat käydä sen läpi ensin.

Terveisin,
{PER1}
""",
    # 03 palaveri
    """# Viikoittainen operatiivinen palaveri: muistio

**Läsnä:** {PER1}, {PER2} sekä kaksi henkilöä IT:stä
**Kesto:** 30 minuuttia

## Kuulumiset

- {PRJ1.nom}: pilotti siirtyy ensi viikolla toiselle linjalle. Odotamme vielä yhtä hyväksyntää.
- Tilausjärjestelmän siirto ympäristöön {TEN1} lykkääntyy viikolla eteenpäin, koska testidata oli puutteellista.
- Tiketti {CON1} (tarrakirjoittimien ajurit) on edelleen auki. IT lupaa korjauksen torstaiksi.
- Palautetut tuotteet ovat yhä [[place:varastolla]], ja laskenta heittää [[quantity:kolmella lavalla]].
- Uuden työvuorolistan pilotti alkaa maanantaina, ja palaute kerätään lyhyellä kyselyllä viikon lopussa.

## Keskustelu

Keskustelimme huolesta, että {QUP1.nom}, on venytetty liian ohueksi kahden vuoron kattamisen jälkeen. Kukaan ei halua toistaa viime talvea. Seuraava palaveri pidetään samaan aikaan ensi viikolla, ja silloin käymme läpi myös varapäivystyksen.

## Toimenpiteet

- {PER2.nom} selvittää toimittajalta puuttuvat paperit.
- Kaikki lukevat [[law:GDPR:n 6 artiklan]] yhden sivun tiivistelmän ennen seuraavaa työpajaa.
""",
    # 04 raportti
    """# Toimittajakelpoisuusraportti: pakkausmateriaalit

## 1. Yhteenveto

Arvioimme {PRJ1.gen} yhteydessä lyhytlistalle valitun pakkaustoimittajan. Toimittaja on rekisteröity Y-tunnuksella {BIZ1}, ja sillä on jätehuoltolupa {LIC1}. Molemmat tarkistettiin julkisista rekistereistä arvioinnin aikana. Arvioinnin tarkoitus oli selvittää, voiko toimittaja kasvattaa volyymejaan ilman laadun heikkenemistä. Aineistona käytettiin sopimusasiakirjoja, auditointiraporttia ja viimeisen vuoden toimitusseurantaa. Nykyinen toimitussopimuksemme toimittajan kanssa on {CON1}.

## 2. Havainnot

| Osa-alue | Tulos |
|---|---|
| Laatujärjestelmä | Sertifioitu ([[standard:ISO 9001]]) |
| Toimitusvarmuus | 96 % ajallaan viimeisen vuoden aikana |
| Kapasiteetti | Pystyy toimittamaan [[quantity:40 lavaa]] viikossa |

Auditoinnissa ei löytynyt kriittisiä poikkeamia. Kaksi vähäistä havaintoa liittyy dokumenttien hallintaan, ja niitä seuraa [[role:laatupäällikkö]].

## 3. Suositus

Hyväksytään toimittaja pilottimäärälle ja arvioidaan uudelleen kuuden kuukauden kuluttua. Päätös viedään hankintaryhmän seuraavaan kokoukseen, ja samalla sovitaan, kuka seuraa toimitusten laatua pilotin aikana. Kysymykset: {PER1}, {MAIL1}.
""",
    # 05 diaesitys
    """# Tarjousesitys: kylmäketjun seuranta

---

## Dia 1: Tarjous

- Anturiverkko kylmäkuljetuksiin
- Hälytyksillä varustettu hallintanäkymä, jonka koodi sijaitsee repositoriossa `{REPO1}`
- Pilotti ensin [[place:Suomessa]], laajennus myöhemmin

**Puhujan muistiinpanot (Speaker notes):** Pidä tämä dia lyhyenä. Mainitse, että työ kulkee sisäisesti nimellä {PRJ1.nom}, mutta älä lue koodinimeä ääneen asiakkaalle. Käytä säästynyt aika hälytysesimerkkeihin. Kerro lopuksi, että asennus tehdään yön aikana, jotta ajoneuvot eivät seiso, ja että hälytykset lähtevät sekä tekstiviestinä että sähköpostina.

---

## Dia 2: Aikataulu

- Kuukausi 1: anturit asennetaan [[quantity:15 rekkaan]]
- Kuukausi 3: ensimmäinen kuukausiraportti
- Kuukausi 6: päätös laajennuksesta

**Puhujan muistiinpanot (Speaker notes):** Asiakas on todellisuudessa {HID1.nom}, vaikka kutsussa lukee vain "iso elintarvikeyritys". Älä mainitse nimeä tämän esityksen jaetussa versiossa. Tarjouksen arvonlisäverotunnus on {VAT1}. Kysymyksiin vastaa {PER1.nom}, puh. {PHONE1}. Muista kertoa myös, että hinta kattaa koulutuksen ja ensimmäisen vuoden tuen.
""",
    # 06 muutosseuranta ja kommentit
    """# Palvelusopimusluonnos: muutosseurannan näkymä

Kohta 4.2 ~~Toimittaja toimittaa 10 päivän kuluessa~~ **Toimittaja toimittaa [[quantity:14 päivän]] kuluessa** kirjallisesta tilauksesta.

> **Kommentti ({PER1.nom}):** Uusi aikataulu toimii meille vain, jos tilaus tehdään tunnuksella {CON1}. Pyydä toimittajaa toistamaan tunnus jokaisessa vahvistuksessa.

Kohta 7 ~~Vastuu on rajoittamaton.~~ **Vastuu rajataan vuosimaksuun.**

> **Kommentti (lakiosasto):** Rajaus on hyväksyttävä [[law:kauppalain]] nojalla. Minulla ei ole muuta lisättävää.

Kohta 9 Toimittaja vakuuttaa, että sillä on toimintaan vaadittava lupa {LIC1}.

Kohta 11 Sopimus on voimassa toistaiseksi, ja kumpikin osapuoli voi irtisanoa sen kolmen kuukauden irtisanomisajalla.

> **Kommentti (talous):** Irtisanomisaika on riittävä, kunhan hinnastoa ei muuteta kesken sopimuskauden.

> **Huomio:** Tämän luonnoksen vastapuoli on käytännössä {HID1.nom}. Hallitus ei ole hyväksynyt sen nimeämistä ulos lähtevässä asiakirjassa, joten nimi pidetään vain tässä kommenttiketjussa ja poistetaan ennen lähettämistä.

> **Kommentti ({PER2.nom}):** Lähetän omat muutokseni osoitteeseen {MAIL1} tänä iltana.
""",
    # 07 häiriöviesti
    """Aihe: Tilausportaalin katkos, jälkiseuranta
Lähettäjä: {PER1} <{MAIL1}>

Hei,

lyhyt yhteenveto viime yön katkoksesta. Tilausportaali lakkasi ottamasta vastaan uusia tilauksia noin kello 02.10, koska palvelimen {HOST1} tietokannan levytila loppui. Vanhoja tilauksia arkistoiva eräajo oli epäonnistunut hiljaa jo viikkoja. Häiriötä seurataan tunnuksella {CON1}.

Korjaus tehtiin yöllä käsin: vapautimme tilaa, käynnistimme palvelun uudelleen ja ajoimme jonossa olleet tilaukset sisään. Yhtään tilausta ei hävinnyt. Seuraavaksi selvitämme, miksi eräajon virhe ei näkynyt valvonnassa. Alustava havainto on, että virheilmoitukset menivät lokiin mutta eivät hälytykseen. Tarkempi analyysi valmistuu ensi viikon alussa, ja jaan sen kaikille asianosaisille. Levytilan hälytyssäännöt ovat repositoriossa `{REPO1}`, ja ne tiukennetaan tällä viikolla.

Katkoksen huomasi ensimmäisenä {QUP1.nom}, ja hän soitti [[role:päivystäjälle]], minkä vuoksi seisokki jäi alle tunnin. Portaalin [[version:versio 2.1]] ei vielä näytä arkistointivirheitä käyttäjille, mutta se on suunniteltu seuraavaan julkaisuun.

Terveisin,
{PER1}
""",
    # 08 muistio: työkaluvaihto
    """# Muistio: suunnitteluryhmän siirtyminen uusiin työkaluihin

Suunnitteluryhmä siirtyy uuteen työkaluun {PRJ1.gen} aikana. Tunnukset luodaan kutsun perusteella ympäristöön {TEN1}, ja jokainen käyttäjä saa kirjalliset ohjeet sähköpostitse. Siirtymän jälkeen vanha järjestelmä pysyy lukutilassa [[quantity:kaksi viikkoa]].

Koulutus järjestetään kahdessa osassa: ensimmäisessä käydään läpi perusasiat ja toisessa vaativammat raportit. Osallistuminen on pakollista kaikille, jotka käyttävät suunnittelutyökalua päivittäin.

Muutama henkilö tarvitsee erityistä tukea. {QUP1.nom}, on pyytänyt pidempää perehdytysaikaa, ja pidän sitä perusteltuna, koska hänen työnsä on sidottu tiiviisti vanhaan rekisteriin. Lisäksi on sovittava, kuka tukee {QUP2.par}, kun vanha rekisteri suljetaan.

Henkilötietojen käsittelyn oikeusperuste uudessa työkalussa on [[law:GDPR:n 6 artikla]], ja paikallisesta ohjeistuksesta vastaa [[role:tiimipäällikkö]].

Lisätietoja ja tunnukset: {PER1.nom}, puh. {PHONE1}, {MAIL1}. Älä välitä tätä muistiota suunnitteluryhmän ulkopuolelle ennen kuin aikataulu on vahvistettu.
""",
    # 09 laskukysely
    """Aihe: Laskukysely, tilaus {CON1}

Hei,

saimme laskun tilauksesta {CON1}, mutta toimittajan tiedot eivät täsmää toimittajarekisterimme kanssa. Laskulla on Y-tunnus {BIZ1}, kun taas rekisterissä saman yrityksen arvonlisäverotunnus on {VAT1}. Näiden pitäisi olla sama yritys, joten oletan, että jommassakummassa tiedossa on kirjoitusvirhe. Voitko vahvistaa, kumpi on oikein, ennen kuin vapautamme [[quantity:8 400 euron]] maksun?

Olemme huomanneet saman ongelman aiemminkin, joten ehdotan, että tarkistamme toimittajarekisterin kerralla kokonaan. Jos sinulla on ajantasainen rekisteriote, liitä se vastaukseen, niin voimme korjata tiedot samalla.

Maksuajo sulkeutuu perjantaina, ja [[role:ostoreskontran hoitaja]] tarvitsee vastauksen viimeistään torstaina.

Vastaa mieluiten tähän samaan viestiin, niin keskustelu pysyy yhdessä paikassa.

Kiitos,
{PER1}
{MAIL1}

Huomio: lasku koskee todellisuudessa asiakasta {HID1.nom}, jonka laskutusta hoidamme välittäjätoimittajan kautta asiakkaan pyynnöstä. Älä mainitse loppuasiakasta toimittajalle lähtevissä viesteissä.
""",
    # 10 turvallisuustoimikunta
    """# Turvallisuustoimikunta: kokousmuistio

**Paikalla:** {PER1}, {PER2} ja [[role:työsuojeluvaltuutettu]]

## Asiat

- Nostolaitteet: nosturin tarkastustodistus {LIC1} on voimassa kesäkuuhun asti.
- Lastausalueen läheltä piti -tilanteen kirjasi {QUP1.nom}. Toimikunta pyysi jakamaan raportin kaikille vuoroesimiehille.
- Poikkeamaloki siirtyy ympäristöön {TEN1} ensi kuun alusta.
- Trukkikokeilu, jossa on [[quantity:kaksi trukkia]], kuuluu {PRJ1.gen} piiriin. Tulokset viedään johdon katselmukseen, joka tehdään [[standard:ISO 45001]] -vaatimusten mukaan.

## Aiemmat toimenpiteet

Toimikunta kävi läpi edellisen kokouksen toimenpiteet. Suurin osa niistä on tehty, mutta ensiapuvälineiden tarkastus on yhä kesken. Vastuuhenkilö on luvannut saada sen valmiiksi ennen seuraavaa kokousta.

## Päätökset

Kokeilua jatketaan vielä kuukauden. Toimikunta ei päätä hankinnasta ennen kuin tulokset ovat käytettävissä. Seuraava kokous pidetään neljän viikon päästä, ja esityslista on auki viikon loppuun asti.
""",
    # 11 toimittajakatsaus
    """# Neljännesvuosikatsaus: toimittajat

## Yleistä

Tällä neljänneksellä arvioitiin kolme toimittajaa. Arviointi perustui sopimusasiakirjoihin, laatuauditointeihin ja toimitusseurantaan. Alla on tiedot kahdesta toimittajasta, joilla on avoimia kohtia. Kolmannen toimittajan osalta ei ole huomautettavaa, eikä sitä käsitellä tässä katsauksessa.

## Toimittaja A

Y-tunnus {BIZ1}. Kuljetusluvan numero on {LIC1}. Sopimus {CON1} on voimassa ensi vuoden loppuun. Toimitukset tulevat [[place:päävarastolle]], eikä auditoinnissa havaittu mitään poikkeavaa.

## Toimittaja B

Toimittaja B on {QUC1.nom}, ja yhteistyö on kestänyt [[quantity:18 kuukautta]]. Toimitusten laatu on tasaista, mutta auditoinnissa havaittiin puutteita dokumentaatiossa, eikä toimittajalla ole vielä [[standard:ISO 9001]] -sertifikaattia.

## Suositus

Katsauksen tavoitteena on antaa hankintaryhmälle riittävä kuva toimittajista ennen sopimusneuvotteluja. Toimittaja A jatkaa ennallaan. Toimittajalta B pyydetään korjaussuunnitelma kuukauden kuluessa, ja lopullinen päätös tehdään ryhmän kokouksessa.

## Yhteyshenkilö

{PER1}, {PHONE1}
""",
    # 12 ohjausryhmä
    """# Ohjausryhmän tilannekatsaus

**Esittäjä:** {PER1.nom}, {MAIL1}

---

## Dia 1: Tilanne

- {PRJ1.nom}: aikataulussa
- Data on siirretty ympäristöön {TEN1}
- Seuraava katselmus [[quantity:kuuden viikon]] kuluttua

**Puhujan muistiinpanot (Speaker notes):** Sponsori, jota emme voi nimetä dialla, on {HID1.nom}. Sano vain "strateginen kumppani". Pidä sävy rauhallisena, sillä ryhmän ulkopuolella kukaan ei ole kuullut budjettimuutoksesta.

---

## Dia 2: Riskit

- Avainhenkilöriippuvuus
- Suunnittelutyökalun [[version:versio 3.4]] ei ole enää tuettu

**Puhujan muistiinpanot (Speaker notes):** Avainhenkilöriski koskee {QUP1.par}. Älä sano tätä ääneen, koska kyse on arkaluonteisesta henkilöstöasiasta. Yleisön kysymykset ohjataan [[role:ohjelmapäällikölle]].

---

## Dia 3: Seuraavat askeleet

- Budjettiesitys ohjausryhmälle
- Päivitetty riskirekisteri
- Viestintäsuunnitelma henkilöstölle

**Puhujan muistiinpanot (Speaker notes):** Käy askeleet läpi nopeasti. Tärkeintä on saada ryhmältä hyväksyntä viestintäsuunnitelmalle ennen kuin mitään kerrotaan henkilöstölle.
""",
]

TEMPLATES = {"en": EN_TEMPLATES, "fi": FI_TEMPLATES}


# -------------------------------------------------------------------- building


def render(template, lang, rng):
    """Fill a template and return (text, labels, decoys) with exact offsets."""
    chosen: dict[str, dict] = {}
    used: dict[str, set] = {}
    parts: list[str] = []
    labels: list[dict] = []
    decoys: list[dict] = []
    pos = 0
    length = 0
    for match in TOKEN.finditer(template):
        literal = template[pos : match.start()]
        parts.append(literal)
        length += len(literal)
        pos = match.end()
        if match.group(1):
            prefix, number, form = match.group(1), match.group(2), match.group(3) or "nom"
            slot = prefix + number
            if slot not in chosen and prefix == "MAIL" and "PER" + number in chosen:
                chosen[slot] = {"nom": _mail(rng, lang, chosen["PER" + number]["nom"])}
            elif slot not in chosen:
                chosen[slot] = _draw(rng, prefix, lang, used.setdefault(prefix, set()))
                used[prefix].add(chosen[slot]["nom"])
            if form == "cap":
                value = chosen[slot]["nom"][:1].upper() + chosen[slot]["nom"][1:]
            else:
                value = chosen[slot][form]
            labels.append(
                {
                    "value": value,
                    "category": SLOT_CATEGORY[prefix],
                    "start": length,
                    "end": length + len(value),
                }
            )
        else:
            value = match.group(5)
            decoys.append(
                {"value": value, "kind": match.group(4), "start": length, "end": length + len(value)}
            )
        parts.append(value)
        length += len(value)
    parts.append(template[pos:])
    return "".join(parts), labels, decoys


def _make_doc(seed, lang, index):
    doc_id = f"{lang}-{index + 1:02d}"
    rng = random.Random(f"{seed}:{doc_id}")
    text, labels, decoys = render(TEMPLATES[lang][index], lang, rng)
    return {
        "id": doc_id,
        "language": lang,
        "split": "test",
        "text": text,
        "labels": labels,
        "decoys": decoys,
    }


def generate(seed=42):
    """Return all 24 documents, deterministic for a given seed."""
    docs = []
    for lang in LANGUAGES:
        dev = set(random.Random(f"{seed}:split:{lang}").sample(range(DOCS_PER_LANGUAGE), DEV_PER_LANGUAGE))
        for index in range(DOCS_PER_LANGUAGE):
            doc = _make_doc(seed, lang, index)
            doc["split"] = "dev" if index in dev else "test"
            verify(doc)
            docs.append(doc)
    return docs


def verify(doc):
    """Raise ValueError if any offset is wrong, spans overlap, or a value repeats unlabelled."""
    text = doc["text"]
    spans = []
    for kind, items in (("label", doc["labels"]), ("decoy", doc["decoys"])):
        for item in items:
            start, end, value = item["start"], item["end"], item["value"]
            if not 0 <= start < end <= len(text):
                raise ValueError(f"{doc['id']}: bad range {start}:{end} for {value!r}")
            if text[start:end] != value:
                raise ValueError(f"{doc['id']}: {value!r} is not at {start}:{end} ({text[start:end]!r})")
            if kind == "label" and item["category"] not in CATEGORIES:
                raise ValueError(f"{doc['id']}: unknown category {item['category']!r}")
            spans.append((start, end, value))
    spans.sort()
    for (s1, e1, v1), (s2, _e2, v2) in pairwise(spans):
        if s2 < e1:
            raise ValueError(f"{doc['id']}: {v1!r} overlaps {v2!r}")
    # Every occurrence of a labelled or decoy value must itself be annotated.
    for value in {s[2] for s in spans}:
        at = text.find(value)
        while at != -1:
            if not any(s <= at and at + len(value) <= e for s, e, _ in spans):
                raise ValueError(f"{doc['id']}: unlabelled occurrence of {value!r} at {at}")
            at = text.find(value, at + 1)


def label_record(doc):
    return {
        "id": doc["id"],
        "language": doc["language"],
        "split": doc["split"],
        "labels": doc["labels"],
        "decoys": doc["decoys"],
    }


def write_corpus(docs, out):
    """Write documents, labels and index.json. Refuses a non-empty directory."""
    out = Path(out)
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise FileExistsError(f"{out} exists and is not empty")
    out.mkdir(parents=True, exist_ok=True)
    for doc in docs:
        (out / f"{doc['id']}.md").write_text(doc["text"], encoding="utf-8", newline="")
        (out / f"{doc['id']}.json").write_text(
            json.dumps(label_record(doc), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    index = [{"id": d["id"], "language": d["language"], "split": d["split"]} for d in docs]
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, help="empty or new directory")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    try:
        write_corpus(generate(args.seed), args.out)
    except FileExistsError as exc:
        print(f"refusing to overwrite: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {2 * DOCS_PER_LANGUAGE} documents to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
