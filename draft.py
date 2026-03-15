# Draft rosters — order = pick order (pick 1 first, pick 15 last)
DRAFT = {
    "Elaina": [
        "Sabalenka, Aryna", "Gauff, Cori", "Shelton, Ben", "Djokovic, Novak",
        "Paul, Tommy", "Zheng, Qinwen", "Rublev, Andrey", "Tauson, Clara",
        "Shnaider, Diana", "Mensik, Jakub", "Norrie, Cameron", "Michelsen, Alex",
        "Tsitsipas, Stefanos", "Eala, Alex", "Sakkari, Maria",
    ],
    "Michael": [
        "Swiatek, Iga", "Rybakina, Elena", "De Minaur, Alex", "Andreeva, Mirra",
        "Medvedev, Daniil", "Osaka, Naomi", "Ruud, Casper", "Mboko, Victoria",
        "Muchova, Karolina", "Davidovich Fokina, Alejandro", "Cobolli, Flavio",
        "Cerundolo, Francisco", "Krejcikova, Barbora", "Joint, Maya", "Munar, Jaume",
    ],
    "Sreesha": [
        "Sinner, Jannik", "Pegula, Jessica", "Fritz, Taylor", "Paolini, Jasmine",
        "Draper, Jack", "Keys, Madison", "Musetti, Lorenzo", "Navarro, Emma",
        "Khachanov, Karen", "Lehecka, Jiri", "Svitolina, Elina", "Ostapenko, Jelena",
        "Tiafoe, Frances", "Samsonova, Liudmila", "Rinderknech, Arthur",
    ],
    "Jeff": [
        "Alcaraz, Carlos", "Anisimova, Amanda", "Auger-Aliassime, Felix", "Bencic, Belinda",
        "Fils, Arthur", "Bublik, Alexander", "Noskova, Linda", "Alexandrova, Ekaterina",
        "Tien, Learner", "Fonseca, Joao", "Fernandez, Leylah", "Hurkacz, Hubert",
        "Dimitrov, Grigor", "Valentova, Tereza", "Vondrousova, Marketa",
    ],
}

# Draft order: snake draft
# Round 1: Sreesha, Jeff, Elaina, Michael
# Round 2: Michael, Elaina, Jeff, Sreesha (snake)
# etc.
DRAFT_ORDER = []
participants = ["Sreesha", "Jeff", "Elaina", "Michael"]
picks = {p: list(DRAFT[p]) for p in participants}

for round_num in range(15):
    order = participants if round_num % 2 == 0 else list(reversed(participants))
    for p in order:
        if picks[p]:
            DRAFT_ORDER.append({
                "overall_pick": len(DRAFT_ORDER) + 1,
                "round": round_num + 1,
                "owner": p,
                "player": picks[p].pop(0),
            })

SEED_POINTS = {
    "Sabalenka, Aryna": 2450, "Gauff, Cori": 1045, "Shelton, Ben": 1000,
    "Djokovic, Novak": 1400, "Paul, Tommy": 565, "Zheng, Qinwen": 130,
    "Rublev, Andrey": 610, "Tauson, Clara": 617, "Shnaider, Diana": 470,
    "Mensik, Jakub": 845, "Norrie, Cameron": 400, "Michelsen, Alex": 310,
    "Tsitsipas, Stefanos": 335, "Eala, Alex": 591, "Sakkari, Maria": 616,
    "Swiatek, Iga": 1010, "Rybakina, Elena": 3093, "De Minaur, Alex": 1035,
    "Andreeva, Mirra": 1193, "Medvedev, Daniil": 1650, "Osaka, Naomi": 282,
    "Ruud, Casper": 405, "Mboko, Victoria": 1712, "Muchova, Karolina": 1555,
    "Davidovich Fokina, Alejandro": 450, "Cobolli, Flavio": 680,
    "Cerundolo, Francisco": 650, "Krejcikova, Barbora": 166,
    "Joint, Maya": 248, "Munar, Jaume": 200,
    "Sinner, Jannik": 1550, "Pegula, Jessica": 2190, "Fritz, Taylor": 665,
    "Paolini, Jasmine": 497, "Draper, Jack": 250, "Keys, Madison": 521,
    "Musetti, Lorenzo": 575, "Navarro, Emma": 261, "Khachanov, Karen": 310,
    "Lehecka, Jiri": 245, "Svitolina, Elina": 2190, "Ostapenko, Jelena": 597,
    "Tiafoe, Frances": 655, "Samsonova, Liudmila": 257, "Rinderknech, Arthur": 200,
    "Alcaraz, Carlos": 2900, "Anisimova, Amanda": 1010, "Auger-Aliassime, Felix": 915,
    "Bencic, Belinda": 864, "Fils, Arthur": 580, "Bublik, Alexander": 750,
    "Noskova, Linda": 710, "Alexandrova, Ekaterina": 426, "Tien, Learner": 725,
    "Fonseca, Joao": 160, "Fernandez, Leylah": 255, "Hurkacz, Hubert": 325,
    "Dimitrov, Grigor": 65, "Valentova, Tereza": 323, "Vondrousova, Marketa": 61,
}

PLAYER_TOUR = {
    "Sinner, Jannik": "atp", "Alcaraz, Carlos": "atp", "Djokovic, Novak": "atp",
    "Shelton, Ben": "atp", "Paul, Tommy": "atp", "Medvedev, Daniil": "atp",
    "Fritz, Taylor": "atp", "De Minaur, Alex": "atp", "Rublev, Andrey": "atp",
    "Mensik, Jakub": "atp", "Tsitsipas, Stefanos": "atp", "Auger-Aliassime, Felix": "atp",
    "Fils, Arthur": "atp", "Bublik, Alexander": "atp", "Musetti, Lorenzo": "atp",
    "Hurkacz, Hubert": "atp", "Tiafoe, Frances": "atp", "Khachanov, Karen": "atp",
    "Dimitrov, Grigor": "atp", "Norrie, Cameron": "atp", "Michelsen, Alex": "atp",
    "Lehecka, Jiri": "atp", "Tien, Learner": "atp", "Fonseca, Joao": "atp",
    "Cerundolo, Francisco": "atp", "Cobolli, Flavio": "atp",
    "Davidovich Fokina, Alejandro": "atp", "Ruud, Casper": "atp",
    "Draper, Jack": "atp", "Rinderknech, Arthur": "atp", "Munar, Jaume": "atp",
    "Sabalenka, Aryna": "wta", "Swiatek, Iga": "wta", "Gauff, Cori": "wta",
    "Rybakina, Elena": "wta", "Pegula, Jessica": "wta", "Andreeva, Mirra": "wta",
    "Muchova, Karolina": "wta", "Mboko, Victoria": "wta", "Keys, Madison": "wta",
    "Paolini, Jasmine": "wta", "Zheng, Qinwen": "wta", "Svitolina, Elina": "wta",
    "Ostapenko, Jelena": "wta", "Noskova, Linda": "wta", "Sakkari, Maria": "wta",
    "Tauson, Clara": "wta", "Eala, Alex": "wta", "Shnaider, Diana": "wta",
    "Navarro, Emma": "wta", "Samsonova, Liudmila": "wta", "Anisimova, Amanda": "wta",
    "Bencic, Belinda": "wta", "Alexandrova, Ekaterina": "wta", "Fernandez, Leylah": "wta",
    "Osaka, Naomi": "wta", "Krejcikova, Barbora": "wta", "Vondrousova, Marketa": "wta",
    "Valentova, Tereza": "wta", "Joint, Maya": "wta",
}
