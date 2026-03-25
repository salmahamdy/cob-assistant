# COB Assistant — Free Streamlit Chatbot

This is a complete **free** version of the COB Assistant project.

It runs with **Streamlit only** and does **not require Anthropic, OpenAI, or any paid API key**. The chatbot uses a local knowledge base plus rule-based intent handling for:
- FAQ / knowledge-base answers
- multi-step appointment booking
- human escalation

## What changed

- Removed the Anthropic dependency and API-key sidebar flow
- Replaced LLM logic with a free local rules engine
- Moved the knowledge base into `data/knowledge_base.json`
- Kept the polished Streamlit UI and booking confirmation cards
- Added a project structure that is ready to zip, upload, and run

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

```text
cob-assistant-free/
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   └── config.toml
└── data/
    └── knowledge_base.json
```

## Deploy free

You can deploy this on Streamlit Community Cloud without any secrets.

1. Push the folder to a public GitHub repository.
2. Create a new Streamlit app.
3. Select `app.py`.
4. Deploy.

## Notes

- This version is deterministic, so it is reliable and completely free.
- It is best for demos, student projects, portfolios, and simple customer-care flows.
- If you later want a real AI model, you can plug one in as an optional upgrade.
