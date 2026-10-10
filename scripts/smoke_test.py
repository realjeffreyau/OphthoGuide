from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

model, tokenizer = load("Qwen/Qwen3-4B-MLX-4bit")

messages = [{
    "role": "user",
    "content": "Explain what an ophthalmologist does in three sentences."
}]

prompt = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
    enable_thinking=False,
)

answer = generate(
    model,
    tokenizer,
    prompt=prompt,
    max_tokens=300,
    sampler=make_sampler(temp=0.7, top_p=0.8, top_k=20),
)

print(answer)