import argparse
import sys


def run_clean_fid(gen_dir: str, gt_dir: str):
    try:
        from cleanfid import fid as cleanfid_fid
    except Exception as e:
        raise ImportError(
            "clean-fid backend requires clean-fid. Install with: pip install clean-fid"
        ) from e

    score = float(cleanfid_fid.compute_fid(gen_dir, gt_dir))
    print(f"FID (clean-fid) = {score:.6f}")
    return 0


def run_torch_fidelity(gen_dir: str, gt_dir: str):
    try:
        from torch_fidelity import calculate_metrics
    except Exception as e:
        raise ImportError(
            "torch-fidelity backend requires torch-fidelity. Install with: pip install torch-fidelity"
        ) from e

    metrics = calculate_metrics(input1=gen_dir, input2=gt_dir, fid=True)
    fid = metrics.get("frechet_inception_distance")
    if fid is None:
        raise RuntimeError(f"Unexpected torch-fidelity output keys: {list(metrics.keys())}")
    print(f"FID = {float(fid):.6f}")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Compute FID between two frame directories.")
    parser.add_argument("gen_dir", help="Generated frames directory")
    parser.add_argument("gt_dir", help="GT frames directory")
    parser.add_argument(
        "--backend",
        default="clean-fid",
        choices=["clean-fid", "torch-fidelity"],
        help="FID backend (recommended: clean-fid)",
    )
    args = parser.parse_args()

    if args.backend == "clean-fid":
        return run_clean_fid(args.gen_dir, args.gt_dir)
    return run_torch_fidelity(args.gen_dir, args.gt_dir)


if __name__ == "__main__":
    raise SystemExit(main())
