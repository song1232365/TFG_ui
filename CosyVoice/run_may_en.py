#!/usr/bin/env python3
"""Run CosyVoice2 zero-shot voice cloning for May (English).

Defaults match TalkingGaussian's test_result assets:
- prompt wav:  ../TalkingGaussian/test_result/may_prompt.wav
- prompt text: ../TalkingGaussian/test_result/may_prompt_en.txt
- tts text:    ../TalkingGaussian/test_result/tts_text_en.txt

Output:
- ../TalkingGaussian/test_result/may_tts_en.wav

Usage:
  python3 run_may_en.py
  python3 run_may_en.py --text_frontend false
"""

import argparse
import sys
from pathlib import Path


def _read_text(path: Path) -> str:
    # Keep it simple: strip leading/trailing whitespace.
    return path.read_text(encoding="utf-8").strip()


def _parse_bool(s: str) -> bool:
    v = s.strip().lower()
    if v in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean: {s}")


def main() -> int:
    parser = argparse.ArgumentParser(description="CosyVoice2 zero-shot (English) using May prompt audio.")
    parser.add_argument(
        "--model_dir",
        default="pretrained_models/CosyVoice2-0.5B",
        help="CosyVoice2 model directory (relative to CosyVoice root).",
    )
    parser.add_argument(
        "--prompt_wav",
        default="../TalkingGaussian/test_result/may_prompt.wav",
        help="Reference prompt wav path.",
    )
    parser.add_argument(
        "--prompt_text",
        default="../TalkingGaussian/test_result/may_prompt_en.txt",
        help="Transcript text for prompt wav.",
    )
    parser.add_argument(
        "--tts_text",
        default="../TalkingGaussian/test_result/tts_text_en.txt",
        help="Target text to synthesize.",
    )
    parser.add_argument(
        "--out_wav",
        default="../TalkingGaussian/test_result/may_tts_en.wav",
        help="Output wav path.",
    )
    parser.add_argument(
        "--text_frontend",
        type=_parse_bool,
        default=True,
        help="Enable text frontend normalization (default: true). Use false to match CosyVoice2 demo settings.",
    )
    args = parser.parse_args()

    # Ensure Matcha-TTS is importable exactly like README/test.py.
    sys.path.append("third_party/Matcha-TTS")

    from cosyvoice.cli.cosyvoice import CosyVoice2  # noqa: E402
    from cosyvoice.utils.file_utils import load_wav  # noqa: E402
    import torchaudio  # noqa: E402

    prompt_wav = Path(args.prompt_wav)
    prompt_text_path = Path(args.prompt_text)
    tts_text_path = Path(args.tts_text)
    out_wav = Path(args.out_wav)

    if not prompt_wav.exists():
        raise FileNotFoundError(f"prompt_wav not found: {prompt_wav}")
    if not prompt_text_path.exists():
        raise FileNotFoundError(f"prompt_text not found: {prompt_text_path}")
    if not tts_text_path.exists():
        raise FileNotFoundError(f"tts_text not found: {tts_text_path}")

    prompt_text = _read_text(prompt_text_path)
    tts_text = _read_text(tts_text_path)

    cosyvoice = CosyVoice2(args.model_dir, load_jit=False, load_trt=False, load_vllm=False, fp16=False)
    prompt_speech_16k = load_wav(str(prompt_wav), 16000)

    # IMPORTANT: API signature is inference_zero_shot(tts_text, prompt_text, prompt_speech_16k, ...)
    wav_chunks = []
    for _, out in enumerate(
        cosyvoice.inference_zero_shot(
            tts_text,
            prompt_text,
            prompt_speech_16k,
            stream=False,
            text_frontend=args.text_frontend,
        )
    ):
        wav_chunks.append(out["tts_speech"])

    if not wav_chunks:
        raise RuntimeError("No audio returned from inference.")

    # If multiple chunks returned, concatenate along time axis.
    import torch

    wav = torch.cat([w.cpu() for w in wav_chunks], dim=1)

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    torchaudio.save(str(out_wav), wav, cosyvoice.sample_rate)
    print(f"Saved: {out_wav}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
