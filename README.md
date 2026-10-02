# 💼 JobMatch AI

AI-powered job matching and career analysis tool.

JobMatch AI analyzes a candidate's CV against a job description and identifies how closely the candidate's experience aligns with the role.

The project combines generative AI with deterministic Python logic to make the analysis more transparent and reproducible.

## 🚀 Demo

Live demo:

[Open JobMatch AI](YOUR_STREAMLIT_URL)

## 🎯 Problem

Job applications often require candidates to compare their CV with different job descriptions.

This process can be time-consuming and it is easy to overlook:

- Required skills
- Experience gaps
- Tools and technologies
- Education requirements
- Language requirements
- Availability or location requirements

JobMatch AI was built as a lightweight tool to automate this initial comparison.

## 💡 Solution

The application takes two inputs:

1. A candidate CV in PDF format
2. A job description

It then:

1. Extracts the text from the CV
2. Uses Gemini to identify job requirements
3. Categorizes each requirement
4. Compares the requirements against the CV
5. Classifies each requirement as:
   - Matched
   - Partial
   - Missing
6. Calculates an estimated match score using Python
7. Generates practical recommendations

## 🧠 How it works

```text
             ┌─────────────────┐
             │   CV PDF        │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │  PDF extraction │
             │     pypdf       │
             └────────┬────────┘
                      │
                      │
             ┌────────▼────────┐
             │                 │
             │     Gemini      │
             │                 │
             │ Requirement     │
             │ extraction +    │
             │ CV comparison   │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │ Structured JSON │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │     Python      │
             │                 │
             │ Score           │
             │ calculation     │
             └────────┬────────┘
                      │
                      ▼
             ┌─────────────────┐
             │   Streamlit     │
             │   dashboard     │
             └─────────────────┘