"""
REASON CODE DICTIONARY
Project: Geospatial Triage for Elder Safeguarding in Rural Communities
Reason Code Workflow
Author: Luke A. Lynch
Date: 2026-04-15

This module defines the rule set used by the reason-code workflow. It stores
the regex patterns, priority ordering, and label text that drive structured
reason-code assignment from notes and related case fields.

The point of this module is central rule definition. It does not open ArcGIS
data, update feature classes, or calculate scores by itself.
"""

REASON_CODES = {
    "RC_NoAnswer": [
        r"\bno answer\b",
        r"\bdid not answer\b",
        r"\bno response\b",
        r"\bunanswered door\b",
        r"\bno one answered\b",
        r"\bunable to contact\b"
    ],

    "RC_PhoneUnreachable": [
        r"\bunreachable by phone\b",
        r"\bphone unreachable\b",
        r"\bphone disconnected\b",
        r"\bdisconnected phone\b",
        r"\bnumber not working\b",
        r"\bphone not working\b",
        r"\bunable to reach by phone\b"
    ],

    "RC_AccessRefused": [
        r"\baccess refused\b",
        r"\brefused access\b",
        r"\brefused entry\b",
        r"\bdenied entry\b",
        r"\bwould not allow visit\b",
        r"\bwould not allow entry\b",
        r"\bdeclined visit\b"
    ],

    "RC_ThirdPartyGatekeeping": [
        r"\bthird[- ]party gatekeeping\b",
        r"\bcaregiver refused\b",
        r"\bfamily refused\b",
        r"\bdaughter refused\b",
        r"\bson refused\b",
        r"\brelative refused\b",
        r"\bcaregiver blocked\b",
        r"\bfamily blocked\b",
        r"\bcaregiver would not allow\b",
        r"\bfamily would not allow\b"
    ],

    "RC_SocialIsolation": [
        r"\bisolated\b",
        r"\bsocially isolated\b",
        r"\blives in isolation\b",
        r"\bno family nearby\b",
        r"\bno support nearby\b",
        r"\blimited social support\b",
        r"\blives alone\b"
    ],

    "RC_LimitedIncome": [
        r"\blimited income\b",
        r"\bfixed income\b",
        r"\bfinancial strain\b",
        r"\bfinancial hardship\b",
        r"\bincome concerns\b",
        r"\bpoverty\b",
        r"\blow income\b"
    ],

    "RC_MobilityConcern": [
        r"\bmobility issue\b",
        r"\bmobility issues\b",
        r"\bmobility concern\b",
        r"\bmobility concerns\b",
        r"\blimited mobility\b",
        r"\bdifficulty walking\b",
        r"\btrouble walking\b",
        r"\buses walker\b",
        r"\buses wheelchair\b",
        r"\bwheelchair\b",
        r"\bwalker\b",
        r"\bcane\b",
        r"\bfall risk\b",
        r"\bfall history\b"
    ],

    "RC_RecentHospitalization": [
        r"\brecently hospitalized\b",
        r"\brecent hospitalization\b",
        r"\bdischarged from hospital\b",
        r"\bhospital discharge\b",
        r"\bpost hospital\b",
        r"\brecent er visit\b",
        r"\brecent emergency room visit\b"
    ]
}

LABELS = {
    "RC_NoAnswer": "No Answer",
    "RC_PhoneUnreachable": "Phone Unreachable",
    "RC_AccessRefused": "Access Refused",
    "RC_ThirdPartyGatekeeping": "Third Party Gatekeeping",
    "RC_SocialIsolation": "Social Isolation",
    "RC_LimitedIncome": "Limited Income",
    "RC_MobilityConcern": "Mobility Concern",
    "RC_RecentHospitalization": "Recent Hospitalization",
    "RC_ActiveInvestigation": "Active Investigation",
    "RC_APSHistory": "APS History",
    "RC_RefusesMedicalHelp": "Refuses Medical Help",
    "RC_NoActiveServices": "No Active Services",
    "RC_EconomicHardship": "Economic Hardship",
    "RC_OverdueContact": "Overdue Contact",
    "RC_Hospice": "Hospice",
    "RC_Veteran": "Veteran"
}

PRIMARY_PRIORITY = [
    "RC_AccessRefused",
    "RC_ThirdPartyGatekeeping",
    "RC_ActiveInvestigation",
    "RC_RefusesMedicalHelp",
    "RC_NoAnswer",
    "RC_PhoneUnreachable",
    "RC_OverdueContact",
    "RC_RecentHospitalization",
    "RC_MobilityConcern",
    "RC_SocialIsolation",
    "RC_NoActiveServices",
    "RC_APSHistory",
    "RC_EconomicHardship",
    "RC_Hospice",
    "RC_Veteran",
    "RC_LimitedIncome"
]

