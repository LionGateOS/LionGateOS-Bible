
class OffsetMismatchError(Exception):
    """Raised when an AI-generated quote does not align with canonical text offsets."""
    pass

class HallucinatedQuoteError(Exception):
    """Raised when an AI-generated quote is not found in the canonical text."""
    pass

def verify_evidence_span(canonical_text, ai_quote, char_start, char_end):
    """
    The Hallucination Firewall:
    Deterministically verifies that the AI's quote is a literal substring
    of the canonical text at the exact byte/character offsets provided.
    
    Returns:
        bool: True if verified.
    Raises:
        OffsetMismatchError: If the offsets point to different text.
        HallucinatedQuoteError: If the offsets are completely out of bounds.
    """
    if char_start is None or char_end is None:
        raise OffsetMismatchError("Null offsets provided.")
        
    if char_start < 0 or char_end > len(canonical_text) or char_start >= char_end:
        raise HallucinatedQuoteError(f"Offsets [{char_start}:{char_end}] are out of bounds for text length {len(canonical_text)}.")
        
    actual_substring = canonical_text[char_start:char_end]
    
    if actual_substring != ai_quote:
        raise OffsetMismatchError(
            f"Assertion Failed.\n"
            f"Expected AI Quote: '{ai_quote}'\n"
            f"Actual Text at Offsets: '{actual_substring}'"
        )
        
    return True

if __name__ == "__main__":
    # Internal Unit Test
    test_doc = "The mystery of faith is revealed in 1 Cor. 13. We must hold fast."
    
    print("Test 1: Valid AI Extraction")
    try:
        verify_evidence_span(test_doc, "We must hold fast.", 47, 65)
        print(" [PASS] Valid extraction accepted.")
    except Exception as e:
        print(f" [FAIL] {e}")
        
    print("\nTest 2: Hallucinated/Modified AI Quote (LLM changed 'fast' to 'strong')")
    try:
        verify_evidence_span(test_doc, "We must hold strong.", 47, 65)
        print(" [FAIL] Guardrail failed to catch hallucination!")
    except OffsetMismatchError as e:
        print(f" [PASS] Guardrail correctly blocked hallucination: {e}")
        
    print("\nTest 3: Shifted Offsets (LLM missed a character)")
    try:
        verify_evidence_span(test_doc, "We must hold fast.", 48, 65)
        print(" [FAIL] Guardrail failed to catch bad offsets!")
    except OffsetMismatchError as e:
        print(f" [PASS] Guardrail correctly blocked offset mismatch.")
