# Synapx Insurance Claims Automation — Junior Software Developer Assignment

## 📌 Overview  
This project implements an **automated claims processing agent** that analyzes an ACORD Automobile Loss Notice (FNOL) PDF, extracts key information, validates required fields, and recommends a routing decision based on business rules provided in the Synapx assessment brief.

The solution demonstrates:
- PDF text extraction  
- Data parsing from unstructured documents  
- Basic validation logic  
- Rule-based decision making  
- Structured JSON output  

---

## 📁 What this repository contains  

| File | Purpose |
|------|---------|
| `synapx_agent.py` | Main Python program that processes the claim |
| `ACORD-Automobile-Loss-Notice-12.05.16.pdf` | Sample input document used for testing |
| `Assessment_Brief_Synapx.pdf` | Original assignment instructions |

> **Note:** `fnol_text.txt` is intentionally **not included** — it was only a temporary testing artifact. The program reads text directly from the PDF.

---

## 🛠️ Tech Stack Used  

- **Python 3**
- **pypdf** – for PDF text extraction  
- **re (regex)** – for pattern matching  
- **JSON** – for structured output  

---

## ▶️ How to Run the Program  

### Step 1 — Install dependency  
Run in terminal:

```bash
pip install pypdf

Step 2 — Place the PDF in the same folder

Ensure this file exists in the repository folder:

ACORD-Automobile-Loss-Notice-12.05.16.pdf

Step 3 — Run the script
python synapx_agent.py
Sample out put
{
  "extractedFields": {
    "policyNumber": "OTHER",
    "dateOfLoss": null,
    "estimatedDamage": 638,
    "claimType": "auto"
  },
  "missingFields": [],
  "recommendedRoute": "Fast-track",
  "reasoning": "Estimated damage 638 below 25000"
}
