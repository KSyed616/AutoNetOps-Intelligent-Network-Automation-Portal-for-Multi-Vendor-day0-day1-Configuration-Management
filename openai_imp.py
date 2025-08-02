import openai


def generate_netconf_filter(prompt: str, model_name: str) -> str:
    system_prompt = f"""You are a network automation assistant. Given a request and a YANG model name, generate a 
NETCONF subtree <filter> XML payload using only that YANG model.

- Model to use: {model_name}
- Make sure all XML tags follow the namespace and structure of the YANG model.
- Do not explain anything. Only output a <filter> XML payload compatible with the specified YANG model.
- Do not include XML declaration or comments.
"""

    print("[GPT SYSTEM PROMPT]:")
    print(system_prompt)
    print("\n[USER PROMPT]:")
    print(prompt)
    openai.api_key = ("sk-proj-nPK1q2MVvmuTmCxz1Ff446y1kMzHHRrPR_x0UbjGUzux1G3lwZXt-U"
                      "-qpxSR7NKS8DHsF9udGgT3BlbkFJeXI6oMe5lUZfO5uZ_EYKCO9IKejaP9"
                      "-GVXaPMtth6thUHlK7YPC0cqadqrUEVsNaEKAtz2u4UA")

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
    )

    result = response['choices'][0]['message']['content'].strip()

    print("\n[GPT RESPONSE]:")
    print(result)

    return result

