import logging
import os
from itertools import product
from re import search
from subprocess import run

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=(
        logging.FileHandler('iter.log'),
        logging.StreamHandler(),
    ),
)


ifilename = 'res/in.mp4'
codecs = ['libx265']
presets = [
    'ultrafast',
    'superfast',
    'veryfast',
    'faster',
    'fast',
    'medium',
    'slow',
    'veryslow',
    'placebo',
]
ocrs = ['20', '24', '27', '30']


def run_ffmpeg(*args):
    res = run(args, capture_output=True, text=True)
    assert not res.returncode, res
    return res.stderr


def step(codec, preset, ocr):
    filename = f'out/{codec}_{preset}_{ocr}.mp4'
    # fmt:off
    res = run_ffmpeg(
        'ffmpeg',
        '-hide_banner',
        '-i', 'res/in.mp4',
        '-c:a', 'copy',
        '-c:v', codec,
        '-preset', preset,
        '-crf', ocr,
        filename
    )
    # fmt:on
    fps = search('([.\d]+) fps[^\n]+\n$', res)[1]
    size = os.path.getsize(filename)
    logging.info(f'{codec} {preset} {ocr} : {fps} fps x{isize/size:.2f}')


isize = os.path.getsize(ifilename)
for codec, preset, ocr in product(codecs, presets, ocrs):
    try:
        step(codec, preset, ocr)
    except Exception as ex:
        logging.error(ex)
