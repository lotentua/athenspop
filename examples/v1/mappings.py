from typing import Final

gender: Final[dict[str, str]] = {
    # 280
    "0: feamale": "female",
    # 181
    "1: male": "male",
}

age: Final[dict[str, str]] = {
    # 223
    **dict.fromkeys(range(15, 30), "15-29"),
    # 132
    **dict.fromkeys(range(30, 45), "30-44"),
    # 79
    **dict.fromkeys(range(45, 60), "45-59"),
    # 26 --> 30
    **dict.fromkeys(range(60, 75), "60+"),
    # 4 --> 0
    # Merge the "60-74" and "75+" age groups.
    **dict.fromkeys(range(75, 85), "60+"),
}
age_group = age

education: Final[dict[str, str]] = {
    # 186
    "2: high school": "secondary",
    # 179
    "3: bachelor": "graduate",
    # TODO: Merge postgraduate with graduate respondents?
    # 96
    "4: master or phd": "postgraduate",
}

employment: Final[dict[str, str]] = {
    # 23 --> 31
    "1: inactive": "inactive",
    # 8 --> 0
    # Merge the professionally inactive and unemployed respondents.
    "2: unemployed": "inactive",
    # 79
    "3: student": "student",
    # 351
    "4: active": "active",
}

income: Final[dict[str, str]] = {
    # 54
    "0: no income": "0",
    # 91
    "1: 750 or less": "750-",
    # 229
    "2: 750-1500": "750-1500",
    # 75 --> 87
    "3: 1500-2500": "1500+",
    # 12 --> 0
    # Merge the "1500-2000" and "2500+" income groups.
    "4: 2500 or more": "1500+",
}
income_all_categories = income

car_own: Final[dict[str, bool]] = {
    # 72
    "0: no": False,
    # 389
    "1: yes": True,
}

purpose: Final[dict[str, str]] = {
    # 409
    "1: work": "work",
    # 467
    "2: return home": "home",
    # 59
    "3: education": "education",
    # 79
    "4: market": "market",
    # 232
    "5: recreation": "recreation",
    # 8 --> 0
    # Merge the "Service" and "Other" trip purposes.
    "6: service": "other",
    # 116 --> 124
    "7: other": "other",
}

modes: Final[dict[str, str]] = {
    # 623 --> 676
    "1: car": "car",
    # 53 --> 0
    # Merge the "Car" and "Taxi" travel modes.
    "2: taxi": "car",
    # TODO: How to handle public transport modes?
    # 169
    "3: bus": "bus",
    # 266
    "4: train": "train",
    # TODO: How to handle motorcycles?
    # 56
    "5: motorcycle": "motorcycle",
    # 19 --> 21
    "6: bicycle": "bicycle",
    # 182
    "7: walk": "walk",
    # 2 --> 0
    # Merge the "Bicycle" and "E-scooter" travel modes.
    "8: escooter": "escooter",
}
