from openai.api_client import APIClient

llm_server_url="http://172.19.46.71:8002"
model_name="/models/Yi-34B-Chat"

client = APIClient(api_server_url=llm_server_url, api_key="")
for output in client.chat_completions_v1(
    model=model_name,
    messages=[
        # {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ],
    temperature=0.0,
    stop_token_ids=["7"],
):
    print(output)