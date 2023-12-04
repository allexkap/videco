import argparse
import json
import logging
import os
from subprocess import run

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=(
        logging.FileHandler('videco.log', 'a'),
        logging.StreamHandler(),
    ),
)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', required=True)
    parser.add_argument('-o', '--output', required=True)
    parser.add_argument('-m', '--move')
    parser.add_argument('-c', '--codec', default='libx265')
    parser.add_argument('-p', '--preset', default='medium')
    parser.add_argument('--crf', default='27')
    parser.add_argument('--exe', default='')
    return parser.parse_args()


def get_timestamp(path, args):
    out = run(
        (args.exe + 'ffprobe', '-v', 'error', '-of', 'json', '-show_format', path),
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(out)['format']['tags']['creation_time']


def convert(src, dst, args):
    try:
        timestamp = ('-metadata', 'creation_time=' + get_timestamp(src, args))
    except:
        logging.warning(f'{src}: no metadata timestamp')
        timestamp = ()

    # fmt:off
    result = run((
        args.exe + 'ffmpeg',
        '-hide_banner',
        '-nostdin',
        '-i', src,
        '-c:a', 'copy',
        '-c:v', args.codec,
        '-preset', args.preset,
        '-crf', args.crf,
        *timestamp,
        dst,
    ))
    assert result.returncode == 0, result
    # fmt:off

    try:
        modify_time = os.path.getmtime(src)
        os.utime(dst, (modify_time, modify_time))
    except:
        logging.warning(f'{src}: no filesystem timestamp')


if __name__ == '__main__':
    args = parse_args()

    for entry in os.scandir(args.input):
        if not entry.is_file():
            continue

        logging.info(f'{entry.path}: in progress')
        dst_path = f'{args.output}/{entry.name}'
        try:
            convert(entry.path, dst_path, args)
        except Exception as ex:
            logging.error(f'{entry.path}: {ex}')
            if os.path.exists(dst_path):
                os.remove(dst_path)
        else:
            if args.move:
                os.rename(entry.path, f'{args.move}/{entry.name}')
            logging.info(f'{entry.path}: success')
