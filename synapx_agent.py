from pypdf import PdfReader
import re
import json
import os


def read_pdf_text(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text
    except Exception as e:
        return None


def _parse_int_from_string(s: str):
    if not s:
        return None
    # remove currency symbols and non-digit except dot and comma
    s = s.replace('$', '').replace('USD', '')
    s = s.replace(' ', '')
    # keep digits and commas and dots
    m = re.search(r"[\d,]+(?:\.\d+)?", s)
    if not m:
        return None
    num = m.group(0)
    num = num.replace(',', '')
    try:
        if '.' in num:
            return int(float(num))
        return int(num)
    except Exception:
        return None


def extract_fields(text):
    extracted = {
        "policyNumber": None,
        "dateOfLoss": None,
        "estimatedDamage": None,
        "claimType": None,
    }

    if not text:
        return extracted

    low = text.lower()

    # --- Policy Number ---
    # try several common patterns
    pol_patterns = [r"policy\s*number[:#\s]*([A-Z0-9\-_/]+)",
                    r"policy[:#\s]*([A-Z0-9\-_/]+)",
                    r"pol\.?\s*#[:\s]*([A-Z0-9\-_/]+)",
                    r"policy\s*no[:\s]*([A-Z0-9\-_/]+)"]
    for pat in pol_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            extracted["policyNumber"] = m.group(1).strip()
            break

    # fallback: look for line with 'policy' and take last token
    if not extracted["policyNumber"]:
        for line in text.splitlines():
            if 'policy' in line.lower():
                parts = line.split()
                if len(parts) >= 2:
                    candidate = parts[-1].strip(':').strip()
                    if len(candidate) >= 4:
                        extracted["policyNumber"] = candidate
                        break

    # --- Date of Loss ---
    # look for 'date of loss' lines first
    date_patterns = [r"date\s*of\s*loss[:\s]*([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})",
                     r"date\s*of\s*loss[:\s]*([A-Za-z]{3,9}\s+[0-9]{1,2},?\s*[0-9]{4})",
                     r"date\s*of\s*loss[:\s]*([0-9]{4}-[0-9]{2}-[0-9]{2})"]
    for pat in date_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            extracted["dateOfLoss"] = m.group(1).strip()
            break

    # fallback: find any date-like token
    if not extracted["dateOfLoss"]:
        # common date regexes
        any_date = re.search(r"([0-9]{1,2}[\/\-][0-9]{1,2}[\/\-][0-9]{2,4})", text)
        if any_date:
            extracted["dateOfLoss"] = any_date.group(1)
        else:
            any_date2 = re.search(r"([A-Za-z]{3,9}\s+[0-9]{1,2},?\s*[0-9]{4})", text)
            if any_date2:
                extracted["dateOfLoss"] = any_date2.group(1)

    # --- Estimated Damage ---
    # Look for lines with common labels and extract currency/number
    damage_keywords = ['estimated amount', 'estimated damage', 'amount of loss', 'estimated loss', 'est amount', 'estimate of loss', 'amount claimed']
    found_damage = None
    for line in text.splitlines():
        lower = line.lower()
        if any(k in lower for k in damage_keywords):
            # try to find a currency/number on the same line
            m = re.search(r"\$?\s*[\d,]+(?:\.\d+)?", line)
            if m:
                val = _parse_int_from_string(m.group(0))
                if val is not None:
                    found_damage = val
                    break
            # if no clear number, try following lines (small window)
            # take next 2 lines
            # (helps when label and number are on separate lines)
            # using index
            # create a safe window
    if found_damage is None:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if any(k in line.lower() for k in damage_keywords):
                # check same line first
                m = re.search(r"\$?\s*[\d,]+(?:\.\d+)?", line)
                if m:
                    found_damage = _parse_int_from_string(m.group(0))
                    break
                # check next two lines
                for j in range(i+1, min(i+3, len(lines))):
                    m2 = re.search(r"\$?\s*[\d,]+(?:\.\d+)?", lines[j])
                    if m2:
                        found_damage = _parse_int_from_string(m2.group(0))
                        break
            if found_damage is not None:
                break

    # broader fallback: find all currency-like numbers and pick a reasonable one
    if found_damage is None:
        candidates = re.findall(r"\$?\s*[\d,]{3,}(?:\.\d+)?", text)
        nums = [(_parse_int_from_string(c), c) for c in candidates]
        nums = [n for n in nums if n[0] is not None]
        # prefer values between 500 and 200000
        nums_sorted = sorted(nums, key=lambda x: x[0])
        chosen = None
        for val, raw in nums_sorted:
            if 500 <= val <= 200000:
                chosen = val
                break
        if chosen is None and nums_sorted:
            chosen = nums_sorted[0][0]
        found_damage = chosen

    if found_damage is not None:
        extracted["estimatedDamage"] = found_damage

    # --- Claim Type ---
    # For ACORD Automobile form default to 'auto' if keywords present
    if 'automobile' in low or 'auto' in low or 'motor vehicle' in low or 'vehicle' in low:
        extracted["claimType"] = 'auto'
    else:
        # default to 'auto' per assignment, but keep None if not confident
        extracted["claimType"] = 'auto'

    return extracted


def find_missing_fields(extracted):
    # dateOfLoss is optional per requirements; only these are mandatory
    mandatory = ["policyNumber", "estimatedDamage", "claimType"]
    missing = [f for f in mandatory if not extracted.get(f)]
    return missing


def decide_route(extracted, missing):
    if missing:
        return "Manual Review", "Mandatory fields are missing: {}".format(
            ", ".join(missing)
        )

    est = extracted.get("estimatedDamage")
    try:
        if est is None:
            return "Manual Review", "Estimated damage not parsed"
        if int(est) < 25000:
            return "Fast-track", f"Estimated damage {est} below 25000"
        else:
            return "Standard Processing", f"Estimated damage {est} meets routing for standard processing"
    except Exception as e:
        return "Manual Review", "Error evaluating routing: {}".format(str(e))


def build_output(extracted, missing, route, reason):
    # Normalize extracted fields (ensure estimatedDamage numeric or null)
    out_fields = {
        "policyNumber": extracted.get("policyNumber"),
        "dateOfLoss": extracted.get("dateOfLoss"),
        "estimatedDamage": extracted.get("estimatedDamage"),
        "claimType": extracted.get("claimType"),
    }

    return {
        "extractedFields": out_fields,
        "missingFields": missing,
        "recommendedRoute": route,
        "reasoning": reason,
    }


def main():
    pdf_name = "ACORD-Automobile-Loss-Notice-12.05.16.pdf"
    pdf_path = os.path.join(os.getcwd(), pdf_name)

    text = read_pdf_text(pdf_path)

    if text is None:
        # Could not read PDF; output manual review with missing fields
        extracted = {"policyNumber": None, "dateOfLoss": None, "estimatedDamage": None, "claimType": None}
        # dateOfLoss is optional; only report the true mandatory fields as missing
        missing = ["policyNumber", "estimatedDamage", "claimType"]
        route, reason = "Manual Review", f"Could not read PDF: {pdf_name}"
        output = build_output(extracted, missing, route, reason)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    extracted = extract_fields(text)
    missing = find_missing_fields(extracted)
    route, reason = decide_route(extracted, missing)

    output = build_output(extracted, missing, route, reason)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
