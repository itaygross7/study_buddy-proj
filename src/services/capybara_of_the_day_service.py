"""
Capybara of the Day Service - Daily rotating capybara family member with funny commentary!
Presents Avner's "family" with humor and personality.
"""
import random
from datetime import datetime
from typing import Dict, List

from sb_utils.logger_utils import logger


# Avner's extended capybara family names with personalities
CAPYBARA_FAMILY = [
    {
        "name": "חורחה",
        "name_en": "Jorge",
        "personality": "אוהב אוכל יותר מכל דבר אחר",
        "images": ["avner_eating.jpeg", "avner_drinnking_coffee.jpeg", "avner_holding_whiskey.jpeg"]
    },
    {
        "name": "רוזה",
        "name_en": "Rosa",
        "personality": "תמיד עסוקה בטלפון",
        "images": ["avner_scroling_phon.jpeg", "avner_calling.jpeg"]
    },
    {
        "name": "פבלו",
        "name_en": "Pablo",
        "personality": "מתעייף מכל דבר",
        "images": ["avner_tierd.jpeg", "avner_yaning.jpeg", "avner_drunk.jpeg"]
    },
    {
        "name": "איזבל",
        "name_en": "Isabel",
        "personality": "תמיד חוגגת משהו",
        "images": ["avner_celebrating.jpeg", "avner_dancing.jpeg", "avner_horay.jpeg", "avner_happy_drinking_alcohol.jpeg"]
    },
    {
        "name": "קרלוס",
        "name_en": "Carlos",
        "personality": "הפילוסוף של המשפחה",
        "images": ["avner_thinking.jpeg", "avner_looking_at_page_acratching_head.jpeg", "avner_douting.jpeg"]
    },
    {
        "name": "לואיזה",
        "name_en": "Luisa",
        "personality": "מקצועית ורצינית",
        "images": ["avner_studing.jpeg", "avner_with_laptop.jpeg", "avner_reading.jpeg", "avner_holding_backbak.jpeg"]
    },
    {
        "name": "דייגו",
        "name_en": "Diego",
        "personality": "קצת עצבני לפעמים",
        "images": ["avner_annoied.jpeg", "avner_angry_holding_pencile.jpeg", "avner_cursing.jpeg"]
    },
    {
        "name": "מריה",
        "name_en": "Maria",
        "personality": "ביישנית ומתוקה",
        "images": ["avner_shy.jpeg", "avner_cluless.jpeg", "avner_dont_understand.jpeg"]
    },
    {
        "name": "פרננדו",
        "name_en": "Fernando",
        "personality": "תמיד מנקה אחרי כולם",
        "images": ["avner_cleaning.jpeg", "avner_apatic.jpeg"]
    },
    {
        "name": "ולנטינה",
        "name_en": "Valentina",
        "personality": "מאוהבת בכולם",
        "images": ["avner_in_love.jpeg", "avner_laghting.jpeg"]
    },
    {
        "name": "אנטוניו",
        "name_en": "Antonio",
        "personality": "תמיד אומר 'לא'",
        "images": ["avner_says_nope.jpeg", "avner_arms_crossed.jpeg"]
    },
    {
        "name": "אלנה",
        "name_en": "Elena",
        "personality": "פשוט עומדת שם",
        "images": ["avner_arms_in_pockets.jpeg", "avner_waving.jpeg", "avner_signing_ok.jpeg"]
    }
]

# Funny capybara family comments (Chandler-style humor)
FAMILY_COMMENTS = [
    {
        "template": "זה {name}, אני אוהב אותו. לא כמו שהוא אוהב אותי... או אוכל. בהחלט אוכל יותר.",
        "personality_match": "אוהב אוכל"
    },
    {
        "template": "פגשו את {name}! {personality}. לפעמים אני מקנא בזה... לפעמים לא.",
        "personality_match": "any"
    },
    {
        "template": "{name} הוא/היא הדוד/דודה שלי. Could this BE any more capybara? 🦫",
        "personality_match": "any"
    },
    {
        "template": "זה {name} מהמשפחה. {personality}. כן, זה קצת מוזר... אבל מי אני לשפוט?",
        "personality_match": "any"
    },
    {
        "template": "{name} - בן/בת משפחה אהוב/ה! {personality}. סיפור ארוך, אל תשאלו.",
        "personality_match": "any"
    },
    {
        "template": "היי, זה {name}! אם הוא/היא שואל/ת - כן, סיפרתי לך עליו/ה. {personality}.",
        "personality_match": "any"
    },
    {
        "template": "{name} תמיד מגיע/ה לאירועי משפחה. {personality}. זה לא בחירה, זו משפחה 🦫",
        "personality_match": "any"
    },
    {
        "template": "זה הקפיברה היפה {name} שלנו! {personality}. כולם צריכים קפיברה כזו בחיים.",
        "personality_match": "any"
    },
    {
        "template": "{name}... מה אגיד לכם? {personality}. המשפחה שלנו קצת משוגעת, אבל זה בסדר.",
        "personality_match": "any"
    },
    {
        "template": "פגשו את {name} מהמשפחה! {personality}. רגע, למה אני מספר לכם את זה?",
        "personality_match": "any"
    }
]


def get_day_of_year() -> int:
    """Get current day of year (1-366) for daily rotation."""
    return datetime.now().timetuple().tm_yday


def get_capybara_of_the_day() -> Dict[str, str]:
    """
    Get the capybara family member of the day with funny commentary.
    
    Returns:
        Dict with name, image, personality, and Avner's funny comment
    """
    try:
        # Use day of year to deterministically select family member
        day = get_day_of_year()
        member_index = day % len(CAPYBARA_FAMILY)
        member = CAPYBARA_FAMILY[member_index]
        
        # Select random image for this member
        image = random.choice(member["images"])
        
        # Generate funny comment
        # Try to find personality-specific comment first
        matching_comments = [
            c for c in FAMILY_COMMENTS 
            if c["personality_match"] == "any" or c["personality_match"] in member["personality"]
        ]
        
        comment_template = random.choice(matching_comments if matching_comments else FAMILY_COMMENTS)
        
        # Format comment with member details
        comment = comment_template["template"].format(
            name=member["name"],
            personality=member["personality"]
        )
        
        logger.info(f"Capybara of the day: {member['name']} ({member['name_en']})")
        
        return {
            "name": member["name"],
            "name_en": member["name_en"],
            "personality": member["personality"],
            "image": image,
            "comment": comment,
            "day": day
        }
        
    except Exception as e:
        logger.error(f"Error getting capybara of the day: {e}", exc_info=True)
        # Fallback to a safe default
        return {
            "name": "אבנר",
            "name_en": "Avner",
            "personality": "הקפיברה המיוחד שלכם",
            "image": "avner_signing_ok.jpeg",
            "comment": "היי! זה אני, אבנר! 🦫",
            "day": 0
        }


def get_random_family_fact() -> str:
    """Get a random funny fact about the capybara family."""
    facts = [
        "🦫 במשפחה שלנו יש 12 קפיברות - וכולם אוהבים לטבול במים!",
        "🦫 המשפחה שלי מורכבת מהקפיברות הכי צ'יל בעולם. זה גנטי.",
        "🦫 ידעתם? קפיברות הן בעלי החיים החברותיים ביותר! כמו המשפחה שלי... רוב הזמן.",
        "🦫 בכל מפגש משפחתי, אנחנו 90% מהזמן במים ו-10% אוכלים. זו עובדה.",
        "🦫 המשפחה שלי? גדולה, רועשת, ותמיד רעבה. אבל אוהבת!",
        "🦫 ראיתי משפחות של אריות, נמרים, דובים... אבל קפיברות? פשוט הכי טובות.",
    ]
    return random.choice(facts)
