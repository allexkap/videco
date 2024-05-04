import argparse
import json
import logging
import os
import shlex
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=(
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).with_suffix('.log')),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-i',
        '--in_dir',
        type=Path,
        required=True,
        help='path to the input directory',
    )
    parser.add_argument(
        '-o',
        '--out_dir',
        type=Path,
        required=True,
        help='path to the output directory',
    )
    parser.add_argument(
        '-t',
        '--tmp_dir',
        type=Path,
        help='path to the directory to which the raw files will be moved',
    )
    parser.add_argument(
        '-v',
        '--video_args',
        type=str,
        help='video args for ffmpeg',
    )
    parser.add_argument(
        '-a',
        '--audio_args',
        type=str,
        help='audio args for ffmpeg',
    )
    parser.add_argument(
        '-m',
        '--merge_args',
        nargs='?',
        const='1.0,1.0',
        type=str,
        help='special mode for nvidia replay; [app_volume,voice_volume]',
    )
    parser.add_argument(
        '-w',
        '--wildcard',
        default='*',
        type=str,
        help='wildcard pattern in input directory',
    )
    parser.add_argument(
        '-j',
        '--threads',
        default=1,
        type=int,
        help='number of files processed simultaneously',
    )
    return parser.parse_args()


def prepare_ffmpeg_args() -> tuple[str, ...]:
    parse = lambda args, default: shlex.split(args) if args is not None else default
    # fmt: off
    if ARGS.merge_args is not None:
        volumes = tuple(map(float, ARGS.merge_args.split(',')))
        return (
            '-map', 'v',
            *parse(ARGS.video_args, default=('-c:v', 'copy')),
            '-filter_complex',
            f'[0:a:0]volume={volumes[0]}[a0]; [0:a:1]volume={volumes[1]}[a1]; [a0][a1]amix[a]',
            '-map', '[a]', '-map', 'a',
            *parse(ARGS.audio_args, default=('-c:a:0', 'aac', '-c:a:1', 'copy', '-c:a:2', 'copy')),
            '-disposition:a', 'none',
            '-disposition:a:0', 'default',
            '-metadata:s:a:0', 'title=Merged',
            '-metadata:s:a:1', 'title=App',
            '-metadata:s:a:2', 'title=Voice',
        )
    return (
        '-map', 'v', *parse(ARGS.video_args, default=('-c:v', 'copy')),
        '-map', 'a', *parse(ARGS.audio_args, default=('-c:a', 'copy')),
    )


def prepare_metadata(file) -> list[str]:
    meta_args = []
    meta_json = run_ffprobe(file)
    try:
        creation_time = meta_json['format']['tags']['creation_time']
        meta_args.extend(('-metadata', f'creation_time={creation_time}'))
    except KeyError:
        logging.debug(f'creation_time not found for {repr(file)}')
    return meta_args


def run_ffmpeg(file_in, file_out):
    # fmt: off
    cmd = (
        'ffmpeg', '-hide_banner', '-v', 'warning', '-nostdin', '-y',
        '-i', file_in,
        *prepare_ffmpeg_args(),
        *prepare_metadata(file_in),
        file_out,
    )
    subprocess.run(cmd, stderr=subprocess.PIPE, check=True)


def run_ffprobe(file, args=('-show_format',)) -> dict:
    cmd = ('ffprobe', '-v', 'warning', '-of', 'json', *args, file)
    res = subprocess.run(cmd, capture_output=True, check=True)
    return json.loads(res.stdout.decode())


def copy_mtime(file_in, file_out) -> None:
    mtime = os.path.getmtime(file_in)
    os.utime(file_out, (mtime, mtime))


def process_file(path):
    name = repr(path.name)
    if not path.is_file():
        logging.info(f'skipped {name}')
        return
    start_time = time.monotonic()
    logging.info(f'starting {name}')

    path_out = ARGS.out_dir / path.name
    res = run_ffmpeg(path, path_out)
    if res:
        if path_out.exists():
            path_out.unlink()
        logging.error(f'finished {name} with non zero return code:\n{res}')
        return

    copy_mtime(path, path_out)
    if ARGS.tmp_dir is not None:
        path.rename(ARGS.tmp_dir / path.name)

    delta = time.monotonic() - start_time
    logging.info(f'finished {name} in {delta:.2f} seconds')


if __name__ == '__main__':
    ARGS = parse_args()
    logging.info(f'running with arguments {ARGS=}')

    with ThreadPoolExecutor(max_workers=ARGS.threads) as executor:
        executor.map(process_file, ARGS.in_dir.glob(ARGS.wildcard))
