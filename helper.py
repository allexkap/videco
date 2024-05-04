import logging
import os
import re
import subprocess
import time
from itertools import product
from pathlib import Path
from re import search
from time import monotonic

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=(
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).with_suffix('.log')),
    ),
)


in_file = Path('./res/loc.mp4')
out_dir = Path('./out/')

codecs = ('hevc_nvenc',)
presets = (
    'default',
    'fast',
)
quality = (20, 30)


def run_ffmpeg(in_file, out_file, args=()):
    # fmt: off
    cmd = (
        'ffmpeg', '-hide_banner', '-v', 'info', '-nostdin', '-y',
        '-i', in_file,
        *args,
        out_file,
    )
    start_ts = time.monotonic()
    out = subprocess.run(cmd, capture_output=True, check=True)
    delta = time.monotonic() - start_ts
    return delta, out


def run_vmaf(reference_file, distorted_file):
    _, out = run_ffmpeg(
        in_file=distorted_file,
        out_file='-',
        args=('-i', reference_file, '-lavfi', 'libvmaf', '-f', 'null'),
    )
    score = re.search(r'VMAF score: ([.\d]+)', out.stderr.decode())
    return score[1] if score else '?'


if __name__ == '__main__':
    original_filesize = os.path.getsize(in_file)
    for c, p, q in product(codecs, presets, quality):
        out_file = out_dir / f'{in_file.stem}_{c}_{p}_{q}{in_file.suffix}'
        name = repr(out_file.name)
        try:
            logging.debug(f'starting {name}')
            elapsed_time, _ = run_ffmpeg(
                in_file, out_file, ('-c:v', c, '-preset', p, '-crf', str(q))
            )
            filesize = os.path.getsize(out_file)
            logging.debug(f'finished {name} in {elapsed_time:.2f}s')
            score = run_vmaf(in_file, out_file)
            logging.info(
                f'{name} {elapsed_time:.2f}s {filesize/original_filesize*100:.2f}% {score}'
            )
        except subprocess.CalledProcessError as ex:
            logging.error(f'CalledProcessError {name}: {ex.stderr}')
