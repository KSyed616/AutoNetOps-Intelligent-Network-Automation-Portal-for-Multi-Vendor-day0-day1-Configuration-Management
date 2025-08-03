import os

import mysql.connector
from mysql.connector import Error

import openai

def generate_netconf_filter(prompt: str, model_name: str):
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

    save_filter_to_db(model_name, result)

    return result


def save_filter_to_db(model_name, filter_payload):

    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )
    db_cursor = conn.cursor()
    db_cursor.execute("""
            INSERT IGNORE INTO netconf_filters (model_name, filter_payload)
            VALUES (%s, %s)
        """, (model_name, filter_payload))
    conn.commit()
    db_cursor.close()
    conn.close()


def get_filter_from_db(model_name):
    cursor = None
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", "password"),
        database=os.getenv("DB_NAME", "AutoNetOps")
    )
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT filter_payload FROM netconf_filters
            WHERE model_name = %s
        """, model_name)
        result = cursor.fetchone()
        return result[0] if result else None
    except Error as e:
        print(f"MySQL Error: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

