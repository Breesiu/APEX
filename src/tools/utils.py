import re
import os
import json
import time
import random
import asyncio
import json_repair
from pydantic import parse_obj_as

_MAX_INVOKE_RETRIES = int(os.getenv("MAX_INVOKE_RETRIES", "10"))
_INVOKE_BACKOFF_BASE_S = float(os.getenv("INVOKE_BACKOFF_BASE_S", "1.0"))
_INVOKE_BACKOFF_MAX_S = float(os.getenv("INVOKE_BACKOFF_MAX_S", "8.0"))

# Stop retrying "hard" HTTP failures after 3 attempts (attempt index 0,1,2).
# Status codes requested: 400 401 403 413 502 503
_HARD_HTTP_STATUS_CODES = {401, 403, 413}


def _get_http_status_code(exc: Exception) -> int | None:
    """
    Best-effort extraction of HTTP status code from various client/library exception shapes.
    """
    # Common direct attribute
    code = getattr(exc, "status_code", None)
    if isinstance(code, int):
        return code

    # Requests/httpx-style: exc.response.status_code
    resp = getattr(exc, "response", None)
    if resp is not None:
        code = getattr(resp, "status_code", None)
        if isinstance(code, int):
            return code

    # Some libs store it in args or message text
    msg = str(exc)
    m = re.search(r"\b(400|401|403|413|502|503)\b", msg)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None
    
def _is_corrupted_thought_signature(exc: Exception) -> bool:
    """
    Gemini sometimes returns 400 upstream_error: 'Corrupted thought signature.'
    This is not recoverable by retrying.
    """
    status = _get_http_status_code(exc)
    if status != 400:
        return False
    msg = str(exc)
    return "Corrupted thought signature" in msg

def _backoff_sleep_s(attempt: int) -> float:
    # attempt: 0,1,2,...
    base = min(_INVOKE_BACKOFF_MAX_S, _INVOKE_BACKOFF_BASE_S * (2 ** attempt))
    jitter = random.uniform(0.4, 0.6 * base)
    return base + jitter

def _invoke_with_retries(llm, prompt, *, logger=None, max_retries: int | None = None, config=None):
    n = _MAX_INVOKE_RETRIES if max_retries is None else max_retries
    last_err: Exception | None = None
    for attempt in range(n):
        try:
            return llm.invoke(prompt, config=config)
        except Exception as e:
            last_err = e
            status = _get_http_status_code(e)

            if logger:
                logger.warning(
                    f"llm.invoke failed (attempt {attempt+1}/{n})"
                    + (f", status={status}" if status is not None else "")
                    + f": {e}"
                )
            # ✅ Do NOT retry this specific 400 error
            if _is_corrupted_thought_signature(e):
                print("❌ Detected corrupted thought signature error; not retrying.")
            #     raise
            
            # For specified HTTP codes: after 3 tries (attempt index 0,1,2) -> raise immediately
            if status in _HARD_HTTP_STATUS_CODES and attempt >= 0:
                raise

            if attempt < n - 1:
                time.sleep(_backoff_sleep_s(attempt))
    raise last_err  # type: ignore[misc]


async def _ainvoke_with_retries(llm, prompt, *, logger=None, max_retries: int | None = None, config=None):
    n = _MAX_INVOKE_RETRIES if max_retries is None else max_retries
    last_err: Exception | None = None
    for attempt in range(n):
        try:
            return await llm.ainvoke(prompt, config=config)
        except Exception as e:
            last_err = e
            status = _get_http_status_code(e)

            if logger:
                logger.warning(
                    f"llm.ainvoke failed (attempt {attempt+1}/{n})"
                    + (f", status={status}" if status is not None else "")
                    + f": {e}"
                )
            # ✅ Do NOT retry this specific 400 error
            if _is_corrupted_thought_signature(e):
                print("❌ Detected corrupted thought signature error, not retrying.")
            #     raise
            
            # For specified HTTP codes: after 3 tries (attempt index 0,1,2) -> raise immediately
            if status in _HARD_HTTP_STATUS_CODES and attempt >= 0:
                raise

            if attempt < n - 1:
                await asyncio.sleep(_backoff_sleep_s(attempt))
    raise last_err  # type: ignore[misc]

def extract_json_from_glm_output(raw_output: str)->dict:
    
    # 用正则匹配两者之间的内容
    try:
        match = re.search(r"<\|begin_of_box\|>(.*?)<\|end_of_box\|>", raw_output, re.S)
        json_str = match.group(1).strip()
    except Exception as e:
        json_str = raw_output

        print(f"❌ Unable to extract JSON from the output: {e}\nContent:\n{raw_output}")
        
    # json_str = raw_output
    # 验证 JSON 格式
    # print(json_str)
    try:
        data = json_repair.loads(json_str)
        # print(data)
    except json.JSONDecodeError as e:
        # raise ValueError(f"❌ JSON 格式错误: {e}\n内容为:\n{json_str}")
        raise ValueError(f"❌ JSON format error: {e}")

    # 返回格式化后的 JSON
    return data


def _strip_code_fences(s: str) -> str:
    if not s:
        return ""
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", s, flags=re.DOTALL | re.IGNORECASE)
    return (m.group(1) if m else s).strip()

def _extract_first_json_object(s: str) -> str:
    s = _strip_code_fences(s)

    # remove // comments
    s = re.sub(r"(?m)^\s*//.*$", "", s)
    # remove trailing commas
    s = re.sub(r",\s*([}\]])", r"\1", s).strip()

    if s.startswith("{") and s.endswith("}"):
        return s

    m = re.search(r"(\{.*\})", s, flags=re.DOTALL)
    return m.group(1) if m else s

def _response_to_text(resp) -> str:
    """
    Normalize LangChain AIMessage (or provider-specific objects) to a plain string.
    """
    if resp is None:
        return ""
    content = getattr(resp, "content", resp)

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        # join all text parts
        texts = []
        for p in content:
            if isinstance(p, dict) and isinstance(p.get("text"), str):
                texts.append(p["text"])
        if texts:
            return "\n".join(texts)
        # fallback if non-text list parts
        return json.dumps(content, ensure_ascii=False)

    return str(content)

def extract_json_from_qwen_output(raw_output: str)->dict:
    
    # 用正则匹配两者之间的内容
    # match = re.search(r"<\|begin_of_box\|>(.*?)<\|end_of_box\|>", raw_output, re.S)
    # json_str = match.group(1).strip()
    json_str = _extract_first_json_object(raw_output)
    # 验证 JSON 格式
    # print(json_str)
    try:
        data = json_repair.loads(json_str)
        # print(data)
    except json.JSONDecodeError as e:
        # raise ValueError(f"❌ JSON 格式错误: {e}\n内容为:\n{json_str}")
        raise ValueError(f"❌ JSON format error: {e}")

    # 返回格式化后的 JSON
    return data

def extract_llm_result(model, prompt, llm, Schema, logger=None,):
    if model == 'glm-4.5v':
        response_text = llm.invoke(prompt).content
        # print("Raw model output:\n", response_text)  # TODO: 
        logger.info(f"Raw model output{response_text}")   
        with open("kapu_progress2.json", "w", encoding="utf-8") as f:
            json.dump(response_text, f, ensure_ascii=False, indent=4)
        result_json = extract_json_from_glm_output(response_text)
        result = parse_obj_as(Schema, result_json)
    elif model in ['qwen3-vl-plus','qwen3.5-vl-plus', 'qwen-vl-max', 'qvq-max-latest'] or 'qwen' in model or 'Qwen' in model:
        # Use structured output
        try:
            response_text = _invoke_with_retries(llm, prompt, logger=logger, max_retries=_MAX_INVOKE_RETRIES)
            result_json = extract_json_from_qwen_output(response_text.content)
            result = parse_obj_as(Schema, result_json)
            
        except:
            # response_text = _invoke_with_retries(llm, prompt, logger=logger, max_retries=_MAX_INVOKE_RETRIES)
            print("extract_llm_result: error, retry")
        if logger:
            logger.info(f"Raw model output{response_text}")   

        # structured_llm = content_editor_llm.with_structured_output(
            # ActionPlan,
            # method='json_schema'
            # )
        # result = structured_llm.invoke(prompt)
    elif model in ['gemini-3-flash-preview']:
        try:
            response_text = _invoke_with_retries(llm, prompt, logger=logger, max_retries=_MAX_INVOKE_RETRIES)
        except Exception as e:
            # response_text = _invoke_with_retries(llm, prompt, logger=logger, max_retries=_MAX_INVOKE_RETRIES)
            # result_json = extract_json_from_qwen_output(response_text.content)
            # result = parse_obj_as(Schema, result_json)
            print(f"extract_llm_result: error, retry:{e}")
        if logger:
            logger.info(f"Raw model output{response_text}")   
        else:
            print(f"Raw model output{response_text}")
        try:
            text = _response_to_text(response_text)
            result_json = extract_json_from_qwen_output(text)
            
        except Exception as e:
            print(f"extract_llm_result: error in extract_json_from_qwen_output, retry:{e}")
            text = _response_to_text(response_text)
            result_json = extract_json_from_qwen_output(text)
            # result_json = extract_json_from_qwen_output(response_text.content[1]['text'])
        result = parse_obj_as(Schema, result_json)
    else:
        structured_llm = llm.with_structured_output(
            Schema,
            method='json_schema'
            )
        try:
            result = structured_llm.invoke(prompt)
        except:
            result = structured_llm.invoke(prompt)
            logger.info("extract_llm_result: error, retry")
    
    return result

def _invoke_with_retries_judge(llm, prompt, *, logger=None, max_retries: int | None = None, Schema=None, config=None):
    n = _MAX_INVOKE_RETRIES if max_retries is None else max_retries
    last_err: Exception | None = None
    for attempt in range(n):
        try:
            response_text =  llm.invoke(prompt, config=config)
            # result_json = extract_json_from_qwen_output(response_text.content)
            # result = parse_obj_as(Schema, result_json)
            return response_text
        except Exception as e:
            last_err = e
            status = _get_http_status_code(e)

            if logger:
                logger.warning(
                    f"llm.invoke failed (attempt {attempt+1}/{n})"
                    + (f", status={status}" if status is not None else "")
                    + f": {e}"
                )

            # For specified HTTP codes: after 3 tries (attempt index 0,1,2) -> raise immediately
            if status in _HARD_HTTP_STATUS_CODES and attempt >= 0:
                raise

            if attempt < n - 1:
                time.sleep(_backoff_sleep_s(attempt))
    raise last_err  # type: ignore[misc]

def extract_llm_result_judge(model, prompt, llm, Schema, logger=None,):
    if model in ['gemini-3-flash-preview']:
        try:
            response_text = _invoke_with_retries_judge(llm, prompt, logger=logger, max_retries=10, Schema=Schema)
        except Exception as e:
            print(f"extract_llm_result: error, retry:{e}")
        try:
            text = _response_to_text(response_text)
            result_json = extract_json_from_qwen_output(text)
            result = parse_obj_as(Schema, result_json)
        except Exception as e:
            print(f"extract_llm_result: error in extract_json_from_qwen_output, retry:{e}")
            print(response_text)
            return response_text
    return result

if __name__ == "__main__":
    raw_output = """
    ```json
    {\n  "thought_process": "The user\'s plan requires swapping the \'Signal Dissection Method\' section (elements 4, 22, 16, 28, 10) with the \'Translation Performance\' section (elements 6, 24, 18, 30, 12). This involves moving each element in the first group to the position of its counterpart in the second group and vice versa. After the swap, the text content in elements 10 and 12 must be updated to reflect their new context: element 10 should now explain how grammatical examples and explanations contribute differently to model performance (based on insights from the paper), while element 12 should reflect the swapped context by focusing on the methodological innovation. The relative positioning within each section must be preserved to maintain visual integrity. I will use the move_group function to move all elements of each section together to ensure they stay aligned. Then, I will update the text content using set_text_content for elements 10 and 12 with concise, impactful academic language that matches the poster style.",\n  "operations": [\n    //step \n{\n      "function": "move_group",\n      "params": {\n        "element_ids": [\n          "4",\n          "22",\n          "16",\n          "28",\n          "10"\n        ],\n        "dx": 17.66,\n        "dy": 0.0\n      }\n    },\n    {\n      "function": "move_group",\n      "params": {\n        "element_ids": [\n          "6",\n          "24",\n          "18",\n          "30",\n          "12"\n        ],\n        "dx": -17.66,\n        "dy": 0.0\n      }\n    },\n    {\n      "function": "set_text_content",\n      "params": {\n        "element_id": "10",\n        "text": "• Core Insight: Parallel examples (BOOKpara) drive translation performance; explanatory text (BOOKnon-para) contributes minimally\\n◦ BOOKpara alone matches BOOKall performance\\n◦ BOOKnon-para reduces quality by up to 8 CHRF++\\n• Typological Extraction: Grambank features → structured prompts\\n• Tasks: Translation, grammaticality judgment, IGT prediction"\n      }\n    },\n    {\n      "function": "set_text_content",\n      "params": {\n        "element_id": "12",\n        "text": "• Method Innovation: Separate grammar books into:\\n◦ BOOKpara: Parallel examples only\\n◦ BOOKnon-para: Explanatory text only\\n• Key Finding: BOOKpara matches/outperforms BOOKall\\n◦ BOOKnon-para reduces quality by up to 8 CHRF++\\n• Fine-tuning: Small models match LLM performance\\n• Efficiency: Parallel data is token-efficient"\n      }\n    }\n  ]\n}
    ```
    """
    extracted_output = extract_json_from_qwen_output(raw_output)

    print(extracted_output)