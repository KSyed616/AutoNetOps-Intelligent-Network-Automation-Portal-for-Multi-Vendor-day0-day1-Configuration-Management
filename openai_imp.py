from openai import OpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)


client = OpenAI(
    api_key="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")


def generate_netconf_filter(prompt: str, model_name: str) -> str:
    system_prompt = f"""You are a network automation assistant. Given a request and a YANG model name, generate a 
NETCONF subtree <filter> XML payload using only that YANG model.

- Model to use: {model_name}
- Make sure all XML tags follow the namespace and structure of the YANG model.
- Do not explain anything. Only output a <filter> XML payload compatible with the specified YANG model.
- Do not include XML declaration or comments, and no markups or formatting of any kind..
- Do not include <filter> tags as manger ncclient already does this
- All relevant information must be pullable from configuration
"""
    print("🟢 [SYSTEM PROMPT]:", system_prompt)
    print("🟡 [USER PROMPT]:", prompt)

    messages = [
        ChatCompletionSystemMessageParam(role="system", content=system_prompt),
        ChatCompletionUserMessageParam(role="user", content=prompt)
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0
    )

    result = response.choices[0].message.content.strip()
    print("🔵 [GPT RESPONSE]:", result)
    return result


