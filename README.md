# Project Charter Generator

This Flask application collects basic project details and uses the Gemini API to draft a project charter from them, shown as a formatted document.

## Features

- Input form for project name, objective, stakeholders, budget, timeline, and team resources
- Dynamic stakeholder row management in the browser
- Gemini API integration for charter generation
- Charter rendered as a formatted business document
- Clear error handling when the API call fails or returns invalid JSON

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the project root with your Gemini key:

   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

4. Run the app:

   ```bash
   python app.py
   ```

5. Open the app in your browser at:

   ```text
   http://127.0.0.1:5000/
   ```

## Notes

- The charter is displayed as HTML. There is no PDF or Word export yet.
- If the API key is missing or the Gemini response is not valid JSON, the app shows a clear error message instead of crashing.
