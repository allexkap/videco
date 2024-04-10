import argparse
import json
import logging
import subprocess
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


def parse_args():
    parser = argparse.ArgumentParser()
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
        '-t',
        '--tmp_dir',
        default=None,
        type=Path,
        help='path to the directory with moved raw files',
    )
    parser.add_argument(
        '-v',
        '--video_args',
        default='-c:v copy',
        type=str,
        help='video args for ffmpeg',
    )
    parser.add_argument(
        '--ffmpeg',
        default='ffmpeg',
        type=Path,
        help='path to the ffmpeg binary file',
    )
    parser.add_argument(
        '--ffprobe',
        default='ffprobe',
        type=Path,
        help='path to the ffprobe binary file',
    )
    return parser.parse_args()


def run_ffmpeg(
    ffmpeg, file_in, file_out, video_args, meta_args=(), app_volume=1, voice_volume=1
):
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
        *meta_args,
        file_out,
    )
    res = subprocess.run(cmd, stderr=subprocess.PIPE)
    if res.returncode:
        return res.stderr.decode()
    return ''


def run_ffprobe(ffpbore, file, args=('-show_format',)):
    cmd = (ffpbore, '-v', 'quiet', '-of', 'json', *args, file)
    res = subprocess.run(cmd, capture_output=True)
    if res.returncode:
        raise ChildProcessError(res.stderr.decode())
    return json.loads(res.stdout.decode())


if __name__ == '__main__':
    args = parse_args()
    logging.info(f'running with arguments {args=}')

    for path in args.in_dir.glob('*'):
        name = repr(path.name)
        if not path.is_file():
            logging.info(f'skipped {name}')
            continue
        logging.info(f'starting {name}')

        meta_args = []
        meta_json = run_ffprobe(args.ffprobe, path)
        try:
            creation_time = meta_json['format']['tags']['creation_time']
            meta_args.extend(('-metadata', f'creation_time={creation_time}'))
        except KeyError:
            logging.debug(f'creation_time not found for {name}')

        res = run_ffmpeg(
            args.ffmpeg,
            path,
            args.out_dir / path.name,
            args.video_args.split(),
            meta_args,
        )

        if res:
            logging.error(f'finished {name} non zero return code:\n{res}')
            continue
        logging.info(f'finished {name}')

        if args.tmp_dir is not None:
            path.rename(args.tmp_dir / path.name)
