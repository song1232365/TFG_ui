# test.py
import sys
sys.path.append('third_party/Matcha-TTS')
from cosyvoice.cli.cosyvoice import CosyVoice2
from cosyvoice.utils.file_utils import load_wav
import torchaudio
import os

# 检查音频文件是否存在
audio_file = './asset/zero_shot_prompt.wav'
if not os.path.exists(audio_file):
    print(f"警告: 音频文件 {audio_file} 不存在")
    # 尝试使用项目自带的示例音频
    audio_file = './asset/zero_shot_prompt.wav'
    if not os.path.exists(audio_file):
        print(f"错误: 项目示例音频文件 {audio_file} 也不存在")
        print("请确保有可用的音频文件用于语音克隆")
        exit(1)

# 加载模型
cosyvoice = CosyVoice2('pretrained_models/CosyVoice2-0.5B', load_jit=False, load_trt=False, load_vllm=False, fp16=False)

# 准备参考音频（用于零样本语音克隆）
prompt_speech_16k = load_wav(audio_file, 16000)

# 执行零样本语音克隆
for i, j in enumerate(cosyvoice.inference_zero_shot(
    '我今天想和你聊聊未来的人工智能技术。',
    '希望你以后能够做的比我还好呦。',
    prompt_speech_16k,
    stream=False)):
    torchaudio.save(f'zero_shot_{i}.wav', j['tts_speech'], cosyvoice.sample_rate)
    
print("语音克隆完成，生成的文件保存为 zero_shot_0.wav")