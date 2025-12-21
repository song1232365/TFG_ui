import argparse
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Compute LSE-C/LSE-D using SyncNet official implementation."
    )
    parser.add_argument("input", help="Directory containing generated .mp4 files.")
    parser.add_argument("--preset", default="wav2lip-real", choices=["wav2lip-real", "wav2lip-lrs", "custom"])
    parser.add_argument("--syncnet-dir", default=os.path.join("third_party", "syncnet_python"))
    parser.add_argument("--tmp-dir", default="tmp_dir/")
    parser.add_argument("--cmd", default=None)
    args = parser.parse_args()

    # 使用绝对路径，防止切换目录后失效
    syncnet_dir = os.path.abspath(args.syncnet_dir)
    input_value = os.path.abspath(args.input)
    tmp_dir = os.path.abspath(args.tmp_dir)
    
    cwd = None # 初始化工作目录变量

    if args.preset == "wav2lip-real":
        sh_path = os.path.join(syncnet_dir, "calculate_scores_real_videos.sh")
        if not os.path.exists(sh_path):
            print(f"Missing {sh_path}. Run: bash evaluation/setup_lse.sh", file=sys.stderr)
            return 2
        
        # 关键修改：设置工作目录为 syncnet_dir
        cwd = syncnet_dir
        cmd = ["bash", "calculate_scores_real_videos.sh", input_value]

    elif args.preset == "wav2lip-lrs":
        py_path = os.path.join(syncnet_dir, "calculate_scores_LRS.py")
        if not os.path.exists(py_path):
            print(f"Missing {py_path}. Run: bash evaluation/setup_lse.sh", file=sys.stderr)
            return 2
        
        cwd = syncnet_dir
        cmd = [sys.executable, "calculate_scores_LRS.py", "--data_root", input_value, "--tmp_dir", tmp_dir]

    else:
        if not args.cmd:
            print("--cmd is required when --preset custom", file=sys.stderr)
            return 2
        cmd = args.cmd.format(input=input_value, syncnet_dir=syncnet_dir, tmp_dir=args.tmp_dir)

    print(f"Running (cwd={cwd}):", cmd if isinstance(cmd, str) else " ".join(cmd))
    
    # 关键修改：传入 cwd 参数
    ret = subprocess.call(cmd, shell=isinstance(cmd, str), cwd=cwd)
    
    if ret != 0:
        print("SyncNet command failed.", file=sys.stderr)
    return ret


if __name__ == "__main__":
    sys.exit(main())
