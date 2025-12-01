from langdetect import detect
from deep_translator import GoogleTranslator

def translate_to_english(text: str):
    try:
        lang = detect(text)
        if lang == "en":
            return text, "en"

        translated = GoogleTranslator(source='auto', target='en').translate(text)
        return translated, lang
    except:
        return text, "en"
