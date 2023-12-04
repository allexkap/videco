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
        logging.FileHandler('helper.log'),
        logging.StreamHandler(),
    ),
)


# global
exe_path = 'ffmpeg'
ifilename = 'res/in.mp4'
odir = 'out/'

# convert
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
ocrs = [20, 24, 27, 30]

# shot
shot_ts = '00:00:02'
shot_pos = '433:336:647:280'  # out_w:out_h:x:y


def ffmpeg_vmaf(filename):
    # fmt:off
    res = run_ffmpeg(
        '-i', filename,
        '-i', ifilename,
        '-lavfi', 'libvmaf',
        '-f', 'null',
        '-',
    )
    # fmt:off
    vmaf = search('VMAF score: ([.\d]+)', res)[1]
    return vmaf


def run_ffmpeg(*args):
    res = run((exe_path, '-hide_banner') + args, capture_output=True, text=True)
    assert not res.returncode, res
    return res.stderr


def ffmpeg_convert(filename, codec, preset, ocr):
    # fmt:off
    res = run_ffmpeg(
        '-i', ifilename,
        '-c:a', 'copy',
        '-c:v', codec,
        '-preset', preset,
        '-crf', str(ocr),
        filename
    )
    # fmt:on
    fps = search('([\d]+).+ fps[^\n]+\n$', res)[1]
    size = os.path.getsize(filename)
    vmaf = ffmpeg_vmaf(filename)
    logging.info(
        f'{codec} {preset:9} {ocr} : {fps:3} fps x{isize/size:.2f} vmaf {vmaf}'
    )


def ffmpeg_shot(filename):
    # fmt:off
    run_ffmpeg(
        '-i', filename,
        '-ss', shot_ts,
        '-vframes', '1',
        '-filter:v', f'crop={shot_pos}',
        filename.replace('.mp4', '.png'),
    )


isize = os.path.getsize(ifilename)
for codec, preset, ocr in product(codecs, presets, ocrs):
    try:
        filename = f'{odir}/{codec}_{preset}_{ocr}.mp4'
        ffmpeg_convert(filename, codec, preset, ocr)
        ffmpeg_shot(filename)
    except Exception as ex:
        logging.error(ex)
