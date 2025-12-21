import argparse
import os
import sys

import cv2
import torch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from metrics import PSNRMeter, SSIMMeter


def _read_video_frames(video_path: str):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Failed to open video: {video_path}")
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            yield frame
    finally:
        cap.release()


def main():
    parser = argparse.ArgumentParser(
        description="Frame metrics between two videos (PSNR/SSIM, optional LPIPS)."
    )
    parser.add_argument("pred", help="Pred/generated video path")
    parser.add_argument("gt", help="GT/reference video path")
    parser.add_argument(
        "--lpips",
        action="store_true",
        help="Also compute LPIPS (requires lpips package)",
    )
    parser.add_argument(
        "--lpips-net",
        default="alex",
        choices=["alex", "vgg", "squeeze"],
        help="LPIPS backbone (only used when --lpips)",
    )
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    psnr_meter = PSNRMeter()
    ssim_meter = SSIMMeter()
    psnr_meter.clear()
    ssim_meter.clear()

    lpips_meter = None
    if args.lpips:
        from metrics import LPIPSMeter

        lpips_meter = LPIPSMeter(net=args.lpips_net, device=device)
        lpips_meter.clear()

    pred_iter = _read_video_frames(args.pred)
    gt_iter = _read_video_frames(args.gt)

    n = 0
    for pred_bgr, gt_bgr in zip(pred_iter, gt_iter):
        # BGR -> RGB, [0,1]
        pred = torch.from_numpy(pred_bgr[..., ::-1].copy()).float() / 255.0
        gt = torch.from_numpy(gt_bgr[..., ::-1].copy()).float() / 255.0

        pred = pred.unsqueeze(0).to(device)
        gt = gt.unsqueeze(0).to(device)

        psnr_meter.update(pred, gt)
        ssim_meter.update(pred, gt)
        if lpips_meter is not None:
            lpips_meter.update(pred, gt)

        n += 1
        if n % 100 == 0:
            print(n)

    if n == 0:
        print("No paired frames read; check video paths.", file=sys.stderr)
        sys.exit(2)

    print(psnr_meter.report())
    print(ssim_meter.report())
    if lpips_meter is not None:
        print(lpips_meter.report())


if __name__ == "__main__":
    main()
