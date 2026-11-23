"""모델 관리 화면과 공용 관측이 공유하는 모델 서비스 목록."""

MODEL_PREPARATION_SERVICES = (
    ('AnimationGPT 전투 모션 FP16 (파일만)', 'animationgpt'),
    ('FLUX 3 Image Klein', 'flux-image'),
    ('Hermes 코딩 모델 Qwen3.8 27B IQ4_XS', 'hermes-model'),
    ('Qwen Image 2.1', 'prop-generator'),
    ('Qwen 2.1 표정 LoRA', 'expression-lora'),
    ('Kimodo', 'kimodo'),
    ('DWPose 포즈 모델', 'dwpose'),
    ('Wan Animate-2', 'wan22-animate2'),
    ('Wan Fun Control', 'wan22-fun-control'),
    ('Wan VACE', 'wan22-vace'),
    ('Wan VACE Q8_0 · 파일 준비', 'wan22-vace-q8'),
    ('Wan 2.2 Videogame Fighting LoRA · High', 'wan22-fighting-lora'),
    ('Wan VACE Lightning T2V LoRA · High/Low', 'wan22-vace-lightning'),
    ('Wan 2.2 I2V · 본체 및 Lightning·KungFu LoRA 파일', 'wan22-i2v-assets'),
    ('HeartMuLa', 'music-heartmula'),
    ('Dasheng-AudioGen', 'sfx-dasheng-audiogen'),
    ('작가 AI', 'writer-agent'),
    ('TranslateGemma 4B', 'prompt-translation'),
)
