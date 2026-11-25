"""Conservative check for an explicitly requested image reference."""
import re


def without_reference(prompt):
    if not isinstance(prompt, str):
        return False
    return bool(re.search(r'(?:참조(?:\s*이미지)?\s*(?:없이|없음|사용하지\s*않)|(?:no|without)\s+(?:any\s+)?reference)', prompt, re.IGNORECASE))


def requires_reference(prompt):
    if not isinstance(prompt, str) or without_reference(prompt):
        return False
    return bool(re.search(r'참조(?:한|할|되는)?\s*(?:이미지|사진|그림)|reference\s+image', prompt, re.IGNORECASE))
