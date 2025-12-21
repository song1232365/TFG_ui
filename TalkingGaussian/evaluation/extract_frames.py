import argparse
import os
import subprocess


def main():
    parser = argparse.ArgumentParser(description="Extract frames from a video into an image directory (ffmpeg).")
    parser.add_argument("video", help="Input video path")
    parser.add_argument("out_dir", help="Output directory for frames")
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        help="Optional FPS to sample (default: keep original)",
    )
    parser.add_argument(
        "--pattern",
        default="%06d.png",
        help="Output filename pattern (default: %%06d.png)",
    )
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    out_pattern = os.path.join(args.out_dir, args.pattern)

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        args.video,
    ]
    if args.fps is not None:
        cmd += ["-vf", f"fps={args.fps}"]
    cmd += [out_pattern]

    print("Running:", " ".join(cmd))
    ret = subprocess.call(cmd)
    if ret != 0:
        raise SystemExit(ret)


if __name__ == "__main__":
    main()
