import os
from pydantic import BaseModel, Field
from typing import List, Optional

class ScriptureRef(BaseModel):
    reference: str = Field(description="The explicitly mentioned or heavily implied scripture reference (e.g., '1 Corinthians 13:4').")

class ExtractionFinding(BaseModel):
    topic: str = Field(description="The primary biblical or historical theme.")
    exact_quote: str = Field(description="The EXACT, literal string from the source text. Do not fix spelling or punctuation.")
    char_start: int = Field(description="The starting character offset of the quote within the text chunk.")
    char_end: int = Field(description="The ending character offset of the quote within the text chunk.")
    scripture_refs: List[ScriptureRef] = Field(description="List of associated scripture references.")
    research_note: str = Field(description="Brief explanation of why this quote maps to the theme and scripture.")

class ExtractionResponse(BaseModel):
    findings: List[ExtractionFinding] = Field(description="List of all findings in this text chunk. Return an empty list if no relevant evidence is found.")

def test_xgrammar_compilation():
    """Validates that XGrammar can compile our schema before loading heavy models."""
    try:
        import xgrammar as xg
        print("Compiling Pydantic schema into XGrammar JSON compiler...")
        compiler = xg.JSONCompiler()
        grammar = compiler.compile(ExtractionResponse)
        print(" [SUCCESS] XGrammar compiled the JSON schema successfully.")
        print(" [READY] The constraints are ready to be passed to vLLM.")
    except Exception as e:
        print(f" [ERROR] XGrammar compilation failed: {e}")

if __name__ == "__main__":
    test_xgrammar_compilation()
