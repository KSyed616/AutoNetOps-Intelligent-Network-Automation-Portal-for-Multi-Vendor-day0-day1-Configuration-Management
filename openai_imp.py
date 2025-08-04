import os

import mysql.connector
from mysql.connector import Error

import openai
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam


def generate_netconf_filter(prompt: str, model_name: str, entry_name: str):
    system_prompt = f"""You are a network automation assistant. Given a request and a YANG model name, generate a 
NETCONF subtree <filter> XML payload using only that YANG model.

- Model to use: {model_name}
- Make sure all XML tags follow the namespace and structure of the YANG model.
- Do not explain anything. Only output a <filter> XML payload compatible with the specified YANG model.
- Do not include XML declaration or comments, and no markups or formatting of any kind..
- Do not include <filter> tags as manger ncclient already does this
- All relevant information must be pullable from configuration
"""

    print("[GPT SYSTEM PROMPT]:")
    print(system_prompt)
    print("\n[USER PROMPT]:")
    print(prompt)
    #openai.api_key = "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"

    messages = [
        ChatCompletionSystemMessageParam(role="system", content=system_prompt),
        ChatCompletionUserMessageParam(role="user", content=prompt)
    ]

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0
    )

    result = response.choices[0].message.content.strip()

    print("\n[GPT RESPONSE]:")
    print(result)

    save_filter_to_db(entry_name, result)

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
        """,  (model_name,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Error as e:
        print(f"MySQL Error: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

