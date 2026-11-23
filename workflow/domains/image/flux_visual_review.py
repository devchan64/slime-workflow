"""격리된 CPU 프로세스에서 FLUX PNG의 시각 관찰을 생성한다."""
import hashlib
import io
import json
import sys
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parents[3] / ".model/flux-report-vision"
MODEL_ID = "HuggingFaceTB/SmolVLM-500M-Instruct"
REVISION = "753c1752602b5e739af7a7fa6947a635051897a3"


def observe(path, expected_hash):
    import torch
    from PIL import Image
    from transformers import AutoModelForImageTextToText, AutoProcessor

    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError("검수할 이미지 해시 불일치")
    with Image.open(io.BytesIO(data), formats=["PNG"]) as source:
        image = source.convert("RGB")
    torch.set_num_threads(6)
    processor = AutoProcessor.from_pretrained(MODEL_DIR, local_files_only=True)
    model = AutoModelForImageTextToText.from_pretrained(MODEL_DIR, local_files_only=True, dtype=torch.float32).eval()
    question = "Describe the visible image. Identify the main subject, number, colors, background, composition and art style. Describe only what you can see."
    messages = [{"role":"user", "content":[{"type":"image"}, {"type":"text", "text":question}]}]
    prompt = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    inputs = processor(text=prompt, images=[image], return_tensors="pt",
                       do_image_splitting=False, size={"longest_edge":512})
    with torch.inference_mode():
        tokens = model.generate(**inputs, max_new_tokens=180, do_sample=False)
    caption = processor.decode(tokens[0, inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
    if not caption:
        raise ValueError("시각 모델 관찰 결과 누락")
    return {"model":MODEL_ID, "revision":REVISION, "image_sha256":expected_hash, "observation":caption}


if __name__ == "__main__":
    print(json.dumps(observe(Path(sys.argv[1]), sys.argv[2]), ensure_ascii=False))
