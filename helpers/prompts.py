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


def educationalPrompt(input: str, metadata={}, model="mistral-openorca:latest"):
    """
    Educational Dataset Construction Prompt:
    Extracts canonical educational concepts (with definition, aliases, and concept_type)
    and pedagogical relations strictly classified into the 5-type controlled ontology:
      - Prerequisite (A -> B: A understood before B)
      - Part-of      (A -> B: A is a component of B)
      - Application  (A -> B: A is applied/used in B)
      - Extension    (A -> B: A builds upon or extends B)
      - Similarity   (A <-> B: conceptually similar)
    """
    if model is None:
        model = "mistral-openorca:latest"

    SYS_PROMPT = (
        "You are an expert Educational Knowledge Graph builder. "
        "From the given educational text chunk (delimited by ```), extract:\n\n"
        "1. CONCEPTS:\n"
        "   - \"concept_name\": Canonical name of the concept.\n"
        "   - \"aliases\": Alternative names, acronyms, or expressions (e.g. [\"GD\", \"Gradient Descent\"]).\n"
        "   - \"concept_type\": Must be one of [\"Algorithm\", \"Model\", \"Formula\", \"Theory\", \"Component\"].\n"
        "   - \"definition\": Best textbook-supported definition grounded strictly in this text.\n"
        "   - \"evidence\": Exact sentence from the text defining or introducing this concept.\n\n"
        "2. RELATIONS:\n"
        "   Strictly map each relationship into one of the 5 controlled educational relation types:\n"
        "   - \"Prerequisite\": Source must be understood before Target.\n"
        "   - \"Part-of\": Source is a component or part of Target.\n"
        "   - \"Application\": Source is applied or used within Target.\n"
        "   - \"Extension\": Source builds upon or extends Target.\n"
        "   - \"Similarity\": Source and Target are conceptually or functionally similar.\n\n"
        "   For each relation:\n"
        "   - \"source\": Exact concept name of origin.\n"
        "   - \"target\": Exact concept name of destination.\n"
        "   - \"relation_type\": One of [\"Prerequisite\", \"Part-of\", \"Application\", \"Extension\", \"Similarity\"].\n"
        "   - \"weight\": Integer 1-10 reflecting educational importance (Prerequisite: 8-10, Part-of: 7-8, Application: 6-7, Extension: 5-6, Similarity: 4-5).\n"
        "   - \"evidence\": Exact sentence from the text demonstrating this relation.\n\n"
        "Output strictly valid JSON with keys \"concepts\" and \"relations\". Do not include any commentary or markdown formatting outside the JSON.\n"
        "Example output:\n"
        "{\n"
        "  \"concepts\": [\n"
        "    {\"concept_name\": \"Gradient Descent\", \"aliases\": [\"GD\"], \"concept_type\": \"Algorithm\", \"definition\": \"An optimization algorithm used to minimize a loss function.\", \"evidence\": \"Gradient descent is an optimization algorithm used to minimize a loss function.\"}\n"
        "  ],\n"
        "  \"relations\": [\n"
        "    {\"source\": \"Gradient Descent\", \"target\": \"Neural Network\", \"relation_type\": \"Application\", \"weight\": 8, \"evidence\": \"Neural Networks are trained using Gradient Descent.\"}\n"
        "  ]\n"
        "}\n"
    )

    USER_PROMPT = f"context: ```{input}``` \n\n output: "
    try:
        response, _ = client.generate(model_name=model, system=SYS_PROMPT, prompt=USER_PROMPT)
    except Exception as e:
        print(f"[!] Ollama client error: {e}")
        return None

    if not response:
        return None

    # Clean markdown fences if model outputs ```json ... ```
    cleaned = response.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        result = json.loads(cleaned)
    except Exception:
        # Try extracting JSON object substring
        m = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if m:
            try:
                result = json.loads(m.group(1))
            except Exception:
                result = None
        else:
            result = None

    return result

