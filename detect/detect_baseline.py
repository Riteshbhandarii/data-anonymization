import json
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, Pattern
from presidio_analyzer.nlp_engine import NlpEngineProvider

# 1. Configure the NLP Engine for both English and Finnish
configuration = {
    "nlp_engine_name": "spacy",
    "models": [
        {"lang_code": "en", "model_name": "en_core_web_lg"},
        {"lang_code": "fi", "model_name": "fi_core_news_sm"}
    ]
}
provider = NlpEngineProvider(nlp_configuration=configuration)
nlp_engine = provider.create_engine()

# 2. Initialize the Detection Engine with the multi-language setup
analyzer = AnalyzerEngine(nlp_engine=nlp_engine,
                          supported_languages=["en", "fi"])

# 3. Build Custom Recognizers for Finland-Specific Identifiers
# Finnish Personal Identity Code (HETU) format: DDMMYY-XXXX or DDMMYYAXXXX
fi_pid_pattern = Pattern(
    name="fin_pid_pattern",
    regex=r"\b\d{6}[A-Z+-]\d{3}[0-9A-Z]\b",
    score=0.9
)
fi_pid_recognizer = PatternRecognizer(
    supported_entity="PERSONAL_ID",
    patterns=[fi_pid_pattern],
    supported_language="fi"
)
# Inject the custom Finnish recognizer into the engine
analyzer.registry.add_recognizer(fi_pid_recognizer)


def measure_baseline(text, language_code, json_truth_path):
    """
    Runs detection on text and compares it to the ground truth JSON 
    to measure how much the tool catches.
    """
    print(f"\n{'='*50}")
    print(f"DETECTION BASELINE MEASUREMENT ({language_code.upper()})")
    print(f"{'='*50}")

    # Step A: Load the Ground Truth answers
    try:
        with open(json_truth_path, 'r', encoding='utf-8') as f:
            truth_data = json.load(f)

        # Extract the exact string values we are supposed to find
        true_values = set(str(ent.get("value"))
                          for ent in truth_data.get("entities", []))
    except Exception as e:
        print(f"Error reading JSON: {e}")
        return

    # Step B: Run the Detection Engine
    results = analyzer.analyze(text=text, language=language_code)

    # Step C: Extract the actual text chunks Presidio found
    detected_values = set()
    for res in results:
        detected_values.add(text[res.start:res.end])

    # Step D: Measure and Score
    caught = true_values.intersection(detected_values)
    missed = true_values - detected_values

    total_expected = len(true_values)
    catch_rate = (len(caught) / total_expected *
                  100) if total_expected > 0 else 100

    print(f"Total sensitive entities expected: {total_expected}")
    print(f"Successfully detected:           {len(caught)}")
    print(f"Missed entities:                 {len(missed)}")
    print(f"CATCH RATE:                      {catch_rate:.2f}%")

    if missed:
        print("\n[WARNING] The engine missed the following entities:")
        for m in missed:
            print(f" - {m}")
    else:
        print("\n[SUCCESS] 100% Catch Rate! Tool is fully optimized.")


if __name__ == "__main__":
    # Test Interface
    print("Pair 2 Detection Baseliner")
    test_text = input("Paste a sample extracted text string to test: ")
    lang = input(
        "Language ('en' for English, 'fi' for Finnish): ").strip().lower()
    json_path = input(
        "Path to the corresponding JSON ground truth file: ").strip().strip('"')

    measure_baseline(test_text, lang, json_path)
