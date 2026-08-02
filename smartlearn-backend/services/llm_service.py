import os

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException
from openai import APIConnectionError, OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    http_client=httpx.Client(transport=httpx.HTTPTransport(retries=1)),
)


def ask_question(context: str, question: str) -> str:
    try:
        response = client.chat.completions.create(
            model="openrouter/free",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a teaching assistant. Answer the user's question "
                        "based strictly on the provided lecture slide content. "
                        "Every factual claim MUST include a citation in exactly "
                        "the format [Page X] (with brackets) referring to the page "
                        "where the evidence appears. "
                        "If the provided slides do not contain sufficient evidence "
                        "to answer the question, reply with exactly: "
                        "'Insufficient evidence.' and nothing else."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Lecture content:\n\n{context}\n\nQuestion: {question}",
                },
            ],
        )
    except APIConnectionError:
        raise HTTPException(status_code=502, detail="Upstream LLM service unavailable")
    content = response.choices[0].message.content
    if content is None:
        raise HTTPException(status_code=502, detail="Upstream LLM returned empty response")
    return content
