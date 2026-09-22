from presidio_analyzer import AnalyzerEngine

def detect_text_entities(text):
    print("=" * 60)
    print("UNSTRUCTURED TEXT DETECTION (PRESIDIO)")
    print("=" * 60)
    
    analyzer = AnalyzerEngine()
    
    # Detect PII in the text
    results = analyzer.analyze(text=text, language='en')
    
    print("\n[ENTITIES DETECTED]")
    if not results:
        print("No sensitive entities found.")
    
    for result in results:
        detected_value = text[result.start:result.end]
        print(f"Type: {result.entity_type:<12} | "
              f"Score: {result.score:.2f} | "
              f"Value: {detected_value}")
        
    return results

if __name__ == "__main__":
    sample_text = input("Enter sensitive text to analyze: ").strip()
    detect_text_entities(sample_text)