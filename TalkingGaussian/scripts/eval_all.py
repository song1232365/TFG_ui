import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile


def _run(cmd, cwd=None, allow_fail=False):
    printable = cmd if isinstance(cmd, str) else " ".join(cmd)
    print(f"\n[RUN] {printable}")
    ret = subprocess.call(cmd, cwd=cwd, shell=isinstance(cmd, str))
    if ret != 0 and not allow_fail:
        raise SystemExit(ret)
    return ret


def _project_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _extract_frames(py, video, out_dir, fps=None):
    cmd = [py, os.path.join("evaluation", "extract_frames.py"), video, out_dir]
    if fps is not None:
        cmd += ["--fps", str(fps)]
    _run(cmd, cwd=_project_root())


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run all evaluation metrics (frame metrics / NIQE / FID / LSE) via the scripts in evaluation/."
        )
    )

    # Inputs
    parser.add_argument("--pred-video", default=None, help="Pred/generated video path (for PSNR/SSIM/LPIPS, NIQE, FID)")
    parser.add_argument("--gt-video", default=None, help="GT/reference video path (for PSNR/SSIM/LPIPS, FID)")
    parser.add_argument(
        "--gen-videos-dir",
        default=None,
        help="Directory containing generated .mp4 files (for LSE presets)",
    )

    # What to run
    parser.add_argument("--frame", action="store_true", help="Run frame metrics (PSNR/SSIM, optional LPIPS) on pred/gt videos")
    parser.add_argument("--niqe", action="store_true", help="Run NIQE on frames extracted from pred video")
    parser.add_argument("--fid", action="store_true", help="Run FID on frames extracted from pred/gt videos")
    parser.add_argument("--lse", action="store_true", help="Run LSE-C/LSE-D using SyncNet/Wav2Lip scripts")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run everything possible given the provided inputs",
    )

    # Frame-metrics options
    parser.add_argument("--lpips", action="store_true", help="Also compute LPIPS in frame metrics")
    parser.add_argument(
        "--lpips-net",
        default="alex",
        choices=["alex", "vgg", "squeeze"],
        help="LPIPS backbone (only used when --lpips)",
    )

    # Frame extraction options
    parser.add_argument(
        "--fps",
        type=float,
        default=None,
        help="Optional FPS used when extracting frames for NIQE/FID (default: original)",
    )

    # FID options
    parser.add_argument(
        "--fid-backend",
        default="clean-fid",
        choices=["clean-fid", "torch-fidelity"],
        help="FID backend (recommended: clean-fid)",
    )

    # LSE options
    parser.add_argument(
        "--lse-preset",
        default="wav2lip-real",
        choices=["wav2lip-real", "wav2lip-lrs"],
        help="LSE preset to run via evaluation/eval_lse.py",
    )
    parser.add_argument(
        "--syncnet-dir",
        default=os.path.join(_project_root(), "third_party", "syncnet_python"),
        help="Path to syncnet_python repo (for LSE)",
    )
    parser.add_argument(
        "--tmp-dir",
        default="tmp_dir/",
        help="tmp_dir passed to some LSE pipelines",
    )
    parser.add_argument(
        "--setup-lse",
        action="store_true",
        help="Run evaluation/setup_lse.sh before LSE",
    )

    # Output
    parser.add_argument(
        "--work-dir",
        default=os.path.join(_project_root(), "evaluation", "_work"),
        help="Working directory for extracted frames",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional path to write a JSON summary (best-effort)",
    )

    args = parser.parse_args()

    # Resolve what to run
    run_frame = args.frame
    run_niqe = args.niqe
    run_fid = args.fid
    run_lse = args.lse

    if args.all or (not (run_frame or run_niqe or run_fid or run_lse)):
        # If --all OR nothing specified: run whatever makes sense with inputs
        run_frame = args.pred_video is not None and args.gt_video is not None
        run_niqe = args.pred_video is not None
        run_fid = args.pred_video is not None and args.gt_video is not None
        run_lse = args.gen_videos_dir is not None

    root = _project_root()
    py = sys.executable

    results = {}
    _ensure_dir(args.work_dir)

    # 1) Frame metrics
    if run_frame:
        if not args.pred_video or not args.gt_video:
            raise SystemExit("--frame requires --pred-video and --gt-video")
        cmd = [
            py,
            os.path.join(root, "evaluation", "eval_frame_metrics.py"),
            args.pred_video,
            args.gt_video,
        ]
        if args.lpips:
            cmd += ["--lpips", "--lpips-net", args.lpips_net]
        _run(cmd)
        results["frame"] = {"lpips": bool(args.lpips), "lpips_net": args.lpips_net}

    # 2) NIQE (extract frames from pred)
    pred_frames_dir = None
    if run_niqe or run_fid:
        if not args.pred_video:
            raise SystemExit("--niqe/--fid require --pred-video")
        pred_frames_dir = os.path.join(args.work_dir, "pred_frames")
        if os.path.exists(pred_frames_dir):
            shutil.rmtree(pred_frames_dir)
        _extract_frames(py, args.pred_video, pred_frames_dir, fps=args.fps)

    if run_niqe:
        cmd = [py, os.path.join(root, "evaluation", "eval_niqe.py"), pred_frames_dir]
        ret = _run(cmd, allow_fail=True)
        results["niqe"] = {"frames_dir": pred_frames_dir, "ok": ret == 0}
        if ret != 0:
            print(
                "[WARN] NIQE failed. Please ensure 'pyiqa' is installed (pip install pyiqa). "
                "Continuing with remaining metrics.",
                file=sys.stderr,
            )

    # 3) FID (extract frames for gt too)
    if run_fid:
        if not args.gt_video:
            raise SystemExit("--fid requires --gt-video")
        gt_frames_dir = os.path.join(args.work_dir, "gt_frames")
        if os.path.exists(gt_frames_dir):
            shutil.rmtree(gt_frames_dir)
        _extract_frames(py, args.gt_video, gt_frames_dir, fps=args.fps)

        cmd = [
            py,
            os.path.join(root, "evaluation", "eval_fid.py"),
            pred_frames_dir,
            gt_frames_dir,
            "--backend",
            args.fid_backend,
        ]
        _run(cmd, allow_fail=False)
        results["fid"] = {
            "backend": args.fid_backend,
            "gen_frames": pred_frames_dir,
            "gt_frames": gt_frames_dir,
        }

    # 4) LSE
    if run_lse:
        if not args.gen_videos_dir:
            raise SystemExit("--lse requires --gen-videos-dir")
        if args.setup_lse:
            _run(["bash", os.path.join(root, "evaluation", "setup_lse.sh")], cwd=root)

        cmd = [
            py,
            os.path.join(root, "evaluation", "eval_lse.py"),
            args.gen_videos_dir,
            "--preset",
            args.lse_preset,
            "--syncnet-dir",
            args.syncnet_dir,
            "--tmp-dir",
            args.tmp_dir,
        ]
        _run(cmd, allow_fail=False)
        results["lse"] = {
            "preset": args.lse_preset,
            "gen_videos_dir": args.gen_videos_dir,
            "syncnet_dir": args.syncnet_dir,
        }

    if args.json_out:
        _ensure_dir(os.path.dirname(os.path.abspath(args.json_out)) or ".")
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n[WROTE] {args.json_out}")


if __name__ == "__main__":
    main()
