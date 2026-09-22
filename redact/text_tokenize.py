from typing import Dict
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_anonymizer.operators import Operator, OperatorType

class ConsistentMappingOperator(Operator):
    def operator_name(self) -> str:
        return "ConsistentMappingOperator"
        
    def operator_type(self) -> OperatorType:
        return OperatorType.Anonymize

    def operate(self, text: str, params: Dict = None) -> str:
        entity_type: str = params["entity_type"]
        entity_mapping: Dict[str, Dict[str, str]] = params["entity_mapping"]
        
        if entity_type not in entity_mapping:
            entity_mapping[entity_type] = {}
            
        mapping_for_type = entity_mapping[entity_type]
        
        if text in mapping_for_type:
            return mapping_for_type[text]
            
        new_index = len(mapping_for_type) + 1
        new_placeholder = f"[{entity_type}_{new_index:03d}]"
        
        mapping_for_type[text] = new_placeholder
        return new_placeholder
        
    def validate(self, params: Dict = None):
        pass 

def tokenize_text(text):
    analyzer = AnalyzerEngine()
    anonymizer = AnonymizerEngine()
    anonymizer.add_anonymizer(ConsistentMappingOperator)
    
    detected_pii = analyzer.analyze(text=text, language='en')
    translation_key = {} 
    
    sanitized_result = anonymizer.anonymize(
        text=text, 
        analyzer_results=detected_pii,
        operators={"DEFAULT": OperatorConfig("ConsistentMappingOperator", {"entity_mapping": translation_key})}
    )
    
    print("\n[TOKENIZED AI PROMPT]")
    print(sanitized_result.text)
    
    print("\n[LOCAL TRANSLATION KEY]")
    for entity_type, mappings in translation_key.items():
        for original_value, token in mappings.items():
            print(f"{entity_type:<12} | {original_value} -> {token}")

if __name__ == "__main__":
    sample_text = input("Enter sensitive text to tokenize: ").strip()
    tokenize_text(sample_text)