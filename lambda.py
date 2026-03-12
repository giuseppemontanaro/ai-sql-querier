import json
import os
import duckdb
import requests
import re
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('QueryCache')

def normalize_query(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    return " ".join(text.split())

def call_llm(user_query):
    s3_path = "s3://e-commerce-analytics-data-gm/ecommerce_transactions.parquet" 
    hf_token = os.environ.get('HF_TOKEN')
    API_URL = "https://router.huggingface.co/v1/chat/completions"
    model_id = "Qwen/Qwen2.5-Coder-7B-Instruct:fastest"

    payload = {
        "model": model_id,
        "messages": [
            {
                "role": "system",
                "content": f"Sei un esperto SQL per DuckDB. Genera SOLO la query SQL senza spiegazioni. Tabella: read_parquet('{s3_path}'). Colonne: Transaction_ID, User_Name, Age, Country, Product_Category, Purchase_Amount, Payment_Method, Transaction_Date"
            },
            {
                "role": "user",
                "content": f"Genera la query SQL per: {user_query}"
            }
        ],
        "max_tokens": 150,
        "stream": False
    }

    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
    
    if response.status_code != 200:
        raise Exception(f"Errore API Hugging Face: {response.text}")

    res_json = response.json()
    sql_query = res_json['choices'][0]['message']['content'].strip()
    sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
    return sql_query

def lambda_handler(event, context):
    try:
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
    except:
        body = event
        
    user_query = body.get('question', 'What is the total purchase amount?')
    
    # --- CACHING ---
    cache_key = normalize_query(user_query)
    
    try:
        response_cache = table.get_item(Key={'user_query': cache_key})
        
        if 'Item' in response_cache:
            print("Cache HIT")
            sql_query = response_cache['Item']['sql_query']
        else:
            print("Cache MISS")
            sql_query = call_llm(user_query)
            table.put_item(Item={
                'user_query': cache_key, 
                'sql_query': sql_query,
                'original_question': user_query
            })

        # --- DUCKDB EXECUTION ---
        con = duckdb.connect()    
        con.execute("SET home_directory='/tmp';")
        con.execute("INSTALL httpfs; LOAD httpfs;")

        query_result = con.execute(sql_query)
        rows = query_result.fetchall()
        columns = [desc[0] for desc in query_result.description]
        data = [dict(zip(columns, row)) for row in rows]

        return {
            'statusCode': 200,
            'body': json.dumps({
                'generated_query': sql_query,
                'result': data
            }, default=str)
        }

    except Exception as e:
        print(f"Errore: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': str(e)})
        }