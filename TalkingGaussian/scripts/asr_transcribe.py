#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{r.stderr.strip()}")
    return r


def _ffmpeg_to_wav16k_mono(src_path: str, dst_path: str):
    # -vn: drop video if exists, robust for mp4
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        src_path,
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        dst_path,
    ]
    _run(cmd)


def transcribe_vosk(wav16k_path: str, model_dir: str, words: bool = False):
    try:
        from vosk import Model, KaldiRecognizer  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Missing dependency: vosk. Install with: pip install vosk\n"
            f"Original error: {e}"
        )

    if not model_dir or not os.path.isdir(model_dir):
        raise RuntimeError(
            "Vosk model_dir not found. Download a model and pass --model_dir.\n"
            "Examples:\n"
            "  Chinese: https://alphacephei.com/vosk/models\n"
            "  English: https://alphacephei.com/vosk/models\n"
            "Then unzip to e.g. ../CosyVoice/asset/vosk-model-small-cn-0.22"
        )

    model = Model(model_dir)
    rec = KaldiRecognizer(model, 16000)
    rec.SetWords(bool(words))

    results = []
    final_text_parts = []

    with open(wav16k_path, "rb") as f:
        while True:
            data = f.read(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                j = json.loads(rec.Result())
                results.append(j)
                if j.get("text"):
                    final_text_parts.append(j["text"])

    j = json.loads(rec.FinalResult())
    results.append(j)
    if j.get("text"):
        final_text_parts.append(j["text"])

    text = " ".join([t for t in final_text_parts if t]).strip()
    return text, results


def main():
    parser = argparse.ArgumentParser(
        description="Offline ASR transcription helper (Vosk). Generates a draft transcript for prompt audio, so you can manually correct it."
    )
    parser.add_argument("--input", required=True, help="Path to audio/video file (wav/mp3/mp4/...)")
    parser.add_argument(
        "--model_dir",
        default="",
        help="Path to Vosk model directory (unzipped). Example: ../CosyVoice/asset/vosk-model-small-cn-0.22",
    )
    parser.add_argument("--out_text", default="", help="Write transcript text to this file")
    parser.add_argument("--out_json", default="", help="Write raw Vosk results json to this file")
    parser.add_argument("--words", action="store_true", help="Include word-level timestamps in json output")

    args = parser.parse_args()

    in_path = str(Path(args.input).expanduser())
    if not os.path.exists(in_path):
        print(f"ERROR: input not found: {in_path}", file=sys.stderr)
        sys.exit(2)

    with tempfile.TemporaryDirectory() as td:
        wav16k = os.path.join(td, "input_16k_mono.wav")
        try:
            _ffmpeg_to_wav16k_mono(in_path, wav16k)
        except Exception as e:
            print(f"ERROR: ffmpeg convert failed: {e}", file=sys.stderr)
            sys.exit(2)

        try:
            text, raw = transcribe_vosk(wav16k, args.model_dir, words=args.words)
        except Exception as e:
            print(f"ERROR: ASR failed: {e}", file=sys.stderr)
            sys.exit(2)

    # Output
    if args.out_text:
        Path(args.out_text).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_text).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)

    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
