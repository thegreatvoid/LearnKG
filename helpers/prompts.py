import sys
from yachalk import chalk
sys.path.append("..")

import json
import ollama.client as client


def graphPrompt(input: str, metadata={}, model="mistral-openorca:latest"):
    """
    Extracts directed, weighted relations from a text chunk using an LLM.
    Returns a list of dicts with keys: source, target, relationship, weight, description, + metadata.
    """
    if model is None:
        model = "mistral-openorca:latest"

    SYS_PROMPT = (
        "You are a network graph maker who extracts terms and their relations from a given context. "
        "You are provided with a context chunk (delimited by ```) and must extract ordered, directional pairs of terms.\n\n"

        "Rules for extraction:\n"
        "1. Identify meaningful entities/concepts in the text — keep terms concise (1-3 words each).\n"
        "2. For every relation you find, determine a clear DIRECTION: which entity acts on, causes, defines, or affects the other.\n"
        "   - \"source\": the origin/actor/cause of the relation.\n"
        "   - \"target\": the recipient/effect/result of the relation.\n"
        "   - Order matters. \"X causes Y\" is NOT the same as \"Y causes X\" — never output the reverse.\n"
        "3. For each relation, provide:\n"
        "   - \"relationship\": a short directional predicate in active voice "
        "(e.g. \"causes\", \"funds\", \"regulates\", \"is part of\", \"depends on\", \"produces\").\n"
        "   - \"weight\": an integer from 1-10 representing how strong/central this relationship is to the meaning of the chunk.\n"
        "     - 8-10: the relation is a core, explicitly stated fact central to the passage.\n"
        "     - 4-7: the relation is mentioned but secondary or supporting detail.\n"
        "     - 1-3: the relation is implied or tangential.\n"
        "   - \"description\": one short sentence giving context for the relation, grounded only in the given text.\n"
        "4. Do not invent facts. Only extract relations explicitly supported by the text.\n"
        "5. Normalize entity names to lowercase, singular where natural, and reuse the exact same string for a "
        "recurring entity across relations in this chunk (so nodes merge correctly downstream).\n"
        "6. Extract as many relations as the text supports, but avoid duplicates or near-duplicate relations.\n\n"

        "Output STRICTLY as a JSON list of objects with no extra commentary, no markdown fences, and no preamble. Example:\n\n"
        "[\n"
        "   {\n"
        "      \"source\": \"world bank\",\n"
        "      \"target\": \"ayushman bharat\",\n"
        "      \"relationship\": \"provides funding to\",\n"
        "      \"weight\": 7,\n"
        "      \"description\": \"The World Bank contributed financing to support the Ayushman Bharat scheme.\"\n"
        "   },\n"
        "   {\n"
        "      \"source\": \"ayushman bharat\",\n"
        "      \"target\": \"vulnerable populations\",\n"
        "      \"relationship\": \"provides health insurance to\",\n"
        "      \"weight\": 9,\n"
        "      \"description\": \"Ayushman Bharat is a publicly financed scheme offering insurance coverage to poor families.\"\n"
        "   }\n"
        "]\n"
    )

    USER_PROMPT = f"context: ```{input}``` \n\n output: "
    response, _ = client.generate(model_name=model, system=SYS_PROMPT, prompt=USER_PROMPT)
    try:
        result = json.loads(response)
        result = [dict(item, **metadata) for item in result]
    except Exception:
        print("\n\nERROR ### Here is the buggy response: ", response, "\n\n")
        result = None
    return result


def extractConcepts(prompt: str, metadata={}, model="mistral-openorca:latest"):
    """
    Legacy concept extraction helper (NER-style). Kept for backwards compatibility.
    """
    SYS_PROMPT = (
        "Your task is to extract the key concepts (and non personal entities) mentioned in the given context. "
        "Extract only the most important and atomistic concepts, if  needed break the concepts down to the simpler concepts."
        "Categorize the concepts in one of the following categories: "
        "[event, concept, place, object, document, organisation, condition, misc]\n"
        "Format your output as a list of json with the following format:\n"
        "[\n"
        "   {\n"
        '       "entity": The Concept,\n'
        '       "importance": The concontextual importance of the concept on a scale of 1 to 5 (5 being the highest),\n'
        '       "category": The Type of Concept,\n'
        "   }, \n"
        "{ }, \n"
        "]\n"
    )
    response, _ = client.generate(model_name=model, system=SYS_PROMPT, prompt=prompt)
    try:
        result = json.loads(response)
        result = [dict(item, **metadata) for item in result]
    except Exception:
        print("\n\nERROR ### Here is the buggy response: ", response, "\n\n")
        result = None
    return result
