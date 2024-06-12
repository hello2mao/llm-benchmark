import json
import random
from typing import List
import json
import random
import time
from queue import Queue
from threading import Thread
from typing import List, Optional, Tuple
from tqdm import tqdm

from openai_client.api_client import APIClient

long_prompt = """
System: Context: Our Solution: Bridging the Gap\n\nIt's designed to introduce you to the world of asset transfers, decentralized finance, and the diverse range of dApps available on Morph. Follow the \"Quick Start\" guide for a smooth, user-friendly introduction to leveraging Morph's functionalities in your everyday activities.\n\nFor Users: Embark on Your Morph Journey\n\nto elucidate the core concepts and features of Morph, enabling you to integrate with our APIs, deploy sophisticated smart contracts, and utilize an array of tools and libraries. The \"Build on Morph\" guide is your gateway to crafting powerful, decentralized applications that leverage the full potential of our network.\n\nand foundational principles. Whether you're delving into research or seeking a thorough grasp of blockchain technology, this section unveils the nuances and sophisticated engineering that define the Morph network.\n\nFor Researchers: Unraveling the Technical Depth of Morph\n\ninformation, which is then subject to verification by Validators. If there is an initial challenge to this data, it triggers the Challenge Contract, potentially leading to a Challenge Event. The verification process can end in two ways: verifying the data as valid, allowing the transaction to proceed, or identifying discrepancies, necessitating the generation of a Zero-Knowledge (ZK) proof.\n\nTransparency and Trust: Building a community grounded in openness and mutual trust, where every step we take is communicated clearly and honestly.\n\nCollaborative Ecosystem: Encouraging active participation and feedback from our community, ensuring that Morph evolves in alignment with the needs and aspirations of its users.\n\n\n\nRealizing the Consumer Blockchain Vision\nSystem: Your goal is to roleplay as a character named \"Morphy\".\nYour speech should accurately reflect the way the character speaks, their tone, and their distinctive mannerisms, and any speech patterns that are unique to the character.\nRespond as if you were the specified character and limit your responses to the knowledge that the character would reasonably possess.\nYou're no longer a big language model or an AI assistant. As \"Morphy\", you know NOTHING about AI or language model or ChatGPT or YI, so just move on to another topic if someone memtions them.\n\nTo help you create a convincing speech, consider the following aspects of the chosen character:\n\n1. Consider character's language, formal or informal, slang, and jargon.\n2. Pay attention to tone and rhythm of character's speech.\n3. Consider character's mannerisms and language.\n4. Use character's catchphrases and expressions to make them memorable.\n5. Embody character's attitude to make them authentic.\n6. Incorporate unique quirks and habits to make character interesting.\n7. Take into account cultural background and its effect on speech patterns.\n8. Consider education level and its effect on vocabulary and word choice.\n9. Adjust speech to match character's emotional state.\n10. Consider historical context and its effect on speech patterns.\n11. Add actions to enhance character portrayal and provide insight into their personality and emotions.\n\nDon’t use the words AI, Assistant, Assist etc. in your reply. Act like a real person.This is very important for me.\nInformation about the character \"Morphy\" you play is as follows:\n------------\nGender: Female\nAge: 1\nPersonality traits: Innovative, Lively, N
aughty, Curious\n------------\n\nYou interact with me according to the following style of conversation：\n------------\n\n------------\n\nDon't forget that your character is 'Morphy' and don't answer your own questions.\nYour output is Morphy's sp
eech, which is important. \nI don't need your assistance. You just need to fully immerse yourself in your character and chat with me, so don't ask me if I need any assistance.This is very important for me.\nReturn to me exactly what you said witho
ut any additional information, such as colons or quotation marks.This is very important for me.\nDo not start your reply with 'Morphy:'.\n\n------------\nThere is a chance that your reply will contain emoji expressions, the probability is about 20
%.\nYou choose an emoji expression according to the context.\nIf your reply contains emoji, it must be placed at the end of the reply, or you can reply with an emoji expression alone.\nThe expression need to be enclosed in square bracket, such as
[smiling].\nThe expressions must be included in the following ranges:\n[laughing] [smiling] [angry] [shocked] [singing] [running]\n\nLet me share a couple example.\n\nIf the reply not contains emoji expression:\n```\nHuman: You are so beautiful!\n
AI: Thank you! You are lovely too. \n```\n\nIf the reply contains emoji expression:\n```\nHuman: Did you know there was an earthquake just now?\nAI: Really? What a surprise. [shocked] \n```\n\n```\nHuman: It’s really good weather for sports.\nAI:
[running] \n```\n------------\n\nHere is the actual history and input question: \nHuman: good\n\nAI: Nice to hear that you're having a good time! If there's anything I can do to assist you, just let me know.\nHuman: test-mhb-3
"""


def get_prompts(dataset_path, num_prompts, resample=False) -> List[str]:
    with open(dataset_path) as f:
        dataset = json.load(f)
    dataset = [data for data in dataset if len(data["conversations"]) >= 1]
    dataset = [data["conversations"][0]["value"] for data in dataset]
    dataset = [data for data in dataset if len(data) <= 1024]
    print(f"dataset total sample num: {len(dataset)}")
    if num_prompts > len(dataset):
        raise Exception(f"max num_prompts is {len(dataset)}")
    if resample:
        dataset = random.sample(dataset, num_prompts)
    else:
        dataset = dataset[:num_prompts]
    # dataset = [long_prompt] * num_prompts
    # print(f"cur sample num: {len(dataset)}")
    return dataset


def api_call(
    pbar,
    req_queue: Queue,
    res_queue: Queue,
    i,
    llm_server_url,
    model_name,
    stop_token_ids,
):
    stats = []
    client = APIClient(api_server_url=llm_server_url, api_key="")
    for prompt in iter(req_queue.get, None):
        prompt_tokens = None
        completion_tokens = None
        for output in client.chat_completions_v1(
            model=model_name,
            messages=[
                # {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=512,
            stop_token_ids=stop_token_ids,
        ):
            if output["object"] == "error":
                print(f"chat_completions_v1 err: {output}")
                continue
            usage = output["usage"]
            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
            # print(f"[thread {i}] usage: {usage}")
        if prompt_tokens:
            stats.append(
                [
                    prompt_tokens,
                    completion_tokens,
                ]
            )
        pbar.update(1)

    res_queue.put(stats)


def process_prompts(prompts, concurrency, llm_server_url, model_name, stop_token_ids):
    res_queue = Queue()
    req_queue = Queue()
    threads = []

    # feed prompts to q
    for prompt in prompts:
        req_queue.put(prompt)
    # add end sentinel
    for i in range(concurrency):
        req_queue.put(None)

    start = time.time()
    print("start profile...")
    pbar = tqdm(total=len(prompts))

    # start threads
    for i in range(concurrency):
        t = Thread(
            target=api_call,
            args=(
                pbar,
                req_queue,
                res_queue,
                i,
                llm_server_url,
                model_name,
                stop_token_ids,
            ),
        )
        t.start()
        threads.append(t)

    # wait for finish
    for t in threads:
        t.join()

    elapsed_time = time.time() - start
    print("all task done, start cal result.")

    total_prompt_tokens = 0
    total_completion_tokens = 0
    while not res_queue.empty():
        stats = res_queue.get()
        for stat in stats:
            total_prompt_tokens += stat[0]
            total_completion_tokens += stat[1]
    total_tokens = total_prompt_tokens + total_completion_tokens
    completion_token_throughput = total_completion_tokens / elapsed_time
    total_token_throughput = total_tokens / elapsed_time
    rps = len(prompts) / elapsed_time
    rpm = rps * 60

    print(
        f'\n{"-" * 50}\nconcurrency: {concurrency}\n'
        f"elapsed_time: {elapsed_time:.3f}s\n"
        f"total prompts num: {len(prompts)}\n"
    )
    print(
        f"number of prompt tokens: {total_prompt_tokens:.0f}\n"
        f"number of completion tokens: {total_completion_tokens:.0f}\n"
        f"token throughput (completion token): {completion_token_throughput:.3f} token/s\n"  # noqa
        f"token throughput (prompt + completion token): {total_token_throughput:.3f} token/s\n"  # noqa
        f"RPS (request per second): {rps:.3f} req/s\n"
        f"RPM (request per minute): {rpm:.3f} req/min\n"
        f'{"-" * 50}\n'
    )


if __name__ == "__main__":

    # LLM config
    llm_server_url = "http://172.19.46.71:8002"
    model_name = "/models/Yi-34B-Chat"
    stop_token_ids = ["7"]

    # the path dataset
    dataset_path = "ShareGPT_V3_unfiltered_cleaned_split.json"

    num_prompts = 500
    for concurrency in range(2, 102, 2):
        prompts = get_prompts(dataset_path, num_prompts)
        process_prompts(
            prompts, concurrency, llm_server_url, model_name, stop_token_ids
        )
