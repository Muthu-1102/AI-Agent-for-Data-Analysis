"""
Deterministic Answer Matching Engine
Matches raw captured computation output and report insights summaries
against ground truth answers using strict type-specific rules.
"""

import re
from typing import Any, Dict, Optional, Tuple, List

class AnswerMatcher:
    @staticmethod
    def extract_numbers(text: str) -> List[float]:
        """
        Extracts all numeric representations from text, handling:
        - Decimals (20.0, 0.05)
        - Commas in thousands (1,373.78 -> 1373.78)
        - Currency symbols ($1,234.56 -> 1234.56)
        - Percentages (25.4% -> 25.4 or 0.254)
        - Negative values (-15.2)
        """
        if not text:
            return []
        
        # Clean markdown formatting like **1,373.78**
        cleaned = re.sub(r"[*_`]", "", text)
        
        # Regex for numbers with optional negative sign, currency symbol, commas, and decimals.
        # Prioritize matching comma-formatted numbers first, then arbitrary digit strings.
        pattern = r"(?<![A-Za-z0-9_])-?\$?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?%?)"
        matches = re.findall(pattern, cleaned)
        
        results = []
        for m in matches:
            raw = m.replace("$", "").replace(",", "").strip()
            is_pct = raw.endswith("%")
            raw = raw.rstrip("%").strip()
            try:
                val = float(raw)
                results.append(val)
                if is_pct:
                    # Also include the fraction equivalent e.g. 25% -> 0.25
                    results.append(val / 100.0)
            except ValueError:
                continue
        return results

    @staticmethod
    def match_numeric(candidate_text: str, ground_truth: float, tolerance: float = 0.01) -> Tuple[bool, Optional[float], str]:
        """
        Matches candidate text against expected numeric ground truth within tolerance.
        Checks both absolute tolerance and 0.1% relative tolerance.
        """
        if not candidate_text:
            return False, None, "empty_text"
            
        numbers = AnswerMatcher.extract_numbers(candidate_text)
        if not numbers:
            return False, None, "no_numbers_found"
            
        best_diff = float("inf")
        best_candidate = None
        
        for num in numbers:
            abs_diff = abs(num - ground_truth)
            rel_denom = max(abs(ground_truth), 1e-6)
            rel_diff = abs_diff / rel_denom
            
            # Match condition: within specified tolerance OR within 0.1% relative tolerance
            tol = max(tolerance, 1e-3)
            if abs_diff <= tol or rel_diff <= 0.002: # 0.2% tolerance window
                return True, num, "exact_match"
                
            if abs_diff < best_diff:
                best_diff = abs_diff
                best_candidate = num
                
        return False, best_candidate, f"closest_candidate_{best_candidate}_diff_{best_diff:.4f}"

    @staticmethod
    def match_categorical(candidate_text: str, ground_truth: str) -> Tuple[bool, Optional[str], str]:
        """
        Matches candidate text against expected categorical string.
        Case-insensitive word boundary match.
        """
        if not candidate_text:
            return False, None, "empty_text"
            
        target = ground_truth.strip().lower()
        text_lower = candidate_text.lower()
        
        # Word boundary search
        pattern = r"\b" + re.escape(target) + r"\b"
        if re.search(pattern, text_lower):
            return True, target, "categorical_matched"
            
        return False, None, "categorical_not_found"

    @classmethod
    def match(cls, candidate_text: str, question_spec: Dict[str, Any]) -> Tuple[bool, Optional[Any], str]:
        """
        Dispatches to numeric or categorical matching based on question specification.
        """
        q_type = question_spec.get("type", "numeric")
        gt = question_spec["ground_truth"]
        
        if q_type == "numeric":
            tol = question_spec.get("tolerance", 0.01)
            return cls.match_numeric(candidate_text, float(gt), tolerance=tol)
        elif q_type == "categorical":
            return cls.match_categorical(candidate_text, str(gt))
        else:
            return False, None, f"unsupported_type_{q_type}"
