from deep_translator import GoogleTranslator

def translate_text(text: str, target_lang: str):
    try:
        # limit size (important)
        text = text[:3000]

        translated = GoogleTranslator(
            source='auto',
            target=target_lang
        ).translate(text)

        return translated

    except Exception as e:
        print("Translation Error:", e)
        return text  # fallback