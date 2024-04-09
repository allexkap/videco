import argparse
from pathlib import Path
from subprocess import run


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f',
        '--ffmpeg',
        default='ffmpeg',
        type=Path,
        help='path to the ffmpeg binary file',
    )
    parser.add_argument(
        '-i',
        '--in_dir',
        default='./new/',
        type=Path,
        required=True,
        help='path to the directory with raw files',
    )
    parser.add_argument(
        '-o',
        '--out_dir',
        type=Path,
        required=True,
        help='path to the directory with future results',
    )
    parser.add_argument(
        '-v',
        '--video_args',
        default='-c:v copy',
        type=str,
        help='video args for ffmpeg',
    )
    return parser.parse_args()


def run_ffmpeg(ffmpeg, file_in, file_out, video_args, app_volume=1, voice_volume=1):
    # fmt: off
    cmd = (
        ffmpeg, '-hide_banner', '-y',
        '-i', file_in,
        '-map', '0:v',
        *video_args,
        '-filter_complex',
        f'[0:a:0]volume={app_volume}[a0]; [0:a:1]volume={voice_volume}[a1]; [a0][a1]amix[a]',
        '-map', '[a]',
        '-map', '0:a',
        '-c:a:0', 'aac',
        '-disposition:a', 'none',
        '-disposition:a:0', 'default',
        '-metadata:s:a:0', 'title=Merged',
        '-metadata:s:a:1', 'title=App',
        '-metadata:s:a:2', 'title=Voice',
        file_out,
    )
    return run(cmd).returncode


if __name__ == '__main__':
    args = parse_args()
    for path in args.in_dir.glob('*'):
        if not path.is_file():
            continue
        res = run_ffmpeg(
            args.ffmpeg,
            path,
            args.out_dir / path.name,
            args.video_args.split(),
        )