#!/usr/bin/env python3

from distutils.util import strtobool
from os.path import exists as file_exists
from sys import exit

def dj(_dict):
    '''Dumps a dict object into a formatted JSON string.'''
    from json import dumps
    return dumps(
        _dict,
        ### replace dict entries that aren't JSON-compatible with an error string
        default=lambda o: 'ERROR: Item not JSON serializable',
        sort_keys=True,
        indent=3)


### Parse arguments
try:
  from argparse import ArgumentParser
  parser = ArgumentParser(
    description = '''
      Convert video to gif (requires ffmpeg and ffmpeg-python)
    '''
  )
  parser.add_argument('-i', '--input',
    action='store', dest='input', type=str, required=True,
    help='Input file path',
  )
  parser.add_argument('-o', '--output',
    action='store', dest='output', type=str, required=True,
    help='Output file path',
  )
  parser.add_argument('-s', '--start',
    action='store', dest='start', type=int, default=None,
    help='Start time of input video',
  )
  parser.add_argument('-d', '--duration',
    action='store', dest='duration', type=int, default=None,
    help='Duration from start time of input video to select for gif',
  )
  parser.add_argument('-l', '--last',
    action='store', dest='last', type=int, default=None,
    help='Select last N seconds of video',
  )
  parser.add_argument('-W', '--width',
    action='store', dest='width', type=int, default=None,
    help='Max width',
  )
  parser.add_argument('-H', '--height',
    action='store', dest='height', type=int, default=None,
    help='Max height',
  )
  parser.add_argument('-m', '--maxdimension',
    action='store', dest='maxdimension', type=int, default=None,
    help='Max pixels for width and height',
  )
  parser.add_argument('-a', '--autocrop',
    action='store_true', dest='autocrop',
    help='Automatically crop black bars',
  )
  parser.add_argument('--crop-w',
    action='store', dest='crop_w', type=int,
    help='Crop width',
  )
  parser.add_argument('--crop-h',
    action='store', dest='crop_h', type=int,
    help='Crop height',
  )
  parser.add_argument('--crop-x',
    action='store', dest='crop_x', type=int,
    help='Crop X position',
  )
  parser.add_argument('--crop-y',
    action='store', dest='crop_y', type=int,
    help='Crop Y position',
  )
  parser.add_argument('-r', '--fps',
    action='store', dest='fps', type=int, default=12,
    help='Number of frames per second (default: 12)',
  )
  parser.add_argument('-S', '--speed',
    action='store', dest='speed', type=float, default=1.0,
    help='Playback speed of gif as a decimal value of input video',
  )
  parser.add_argument('-t', '--text',
    action='store', dest='text', type=str, default=None,
    help='Add text overlay in lower third',
  )
  parser.add_argument('--text-x',
    action='store', dest='text_x', type=str, default='w*0.05',
    help='Add text at horizontal offset (default: w*0.05)',
  )
  parser.add_argument('--text-y',
    action='store', dest='text_y', type=str, default='h*0.9',
    help='Add text at vertical offset (default: h*0.9)',
  )
  parser.add_argument('--text-size',
    action='store', dest='text_size', type=int, default=76,
    help='Text overlay font size',
  )
  parser.add_argument('--sharpen',
    action='store', dest='sharpen', type=float, choices=[
      0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 0.9, 1.0 ],
    help='Sharpen video in contrast-aware fashion. Takes a decimal value between 0 and 1 to represent percentage of strength',
  )
  parser.add_argument('--denoise',
    action='store_true', dest='denoise',
    help='Denoise in temproally-aware fashion',
  )
  parser.add_argument('-f', '--extravf',
    action='append', dest='extravf', default=[],
    help='Extra video filters to pass to ffmpeg, can be specified more than once',
  )
  parser.add_argument('-p', '--palette',
    action='store', dest='palette', type=str, default='full', choices=['diff', 'full'],
    help='Stats mode for palettegen (default: full)',
  )
  parser.add_argument('-D', '--dither',
    action='store', dest='dither', type=str, default='none', choices=['none', 'floyd_steinberg', 'sierra2'],
    help='Dithering mode (default: none)',
  )
  parser.add_argument('-O', '--overwrite',
    action='store_true', dest='overwrite',
    help='Overwrite destination file if exists',
  )
  parser.add_argument('-L', '--loglevel',
    action='store', dest='loglevel', type=str, default='INFO',
    help='Logging level. (Default: INFO)',
  )
  parser.add_argument('--dry',
    action='store_true', dest='dry', help='Dry run',
  )
  args = parser.parse_args()
except Exception as e:
  print(f'Unable to parse arguments.\n{e}')
  exit(1)

### Set up logger
try:
  import logging
  from functools import partial, partialmethod
  logging.TRACE = 5
  logging.addLevelName(logging.TRACE, 'TRACE')
  logging.Logger.trace = partialmethod(logging.Logger.log, logging.TRACE)
  logging.trace = partial(logging.log, logging.TRACE)
  logging.basicConfig(
      format='%(asctime)s %(levelname)s %(funcName)s:%(lineno)d %(message)s',
      level=args.loglevel.upper())
  log = logging.getLogger(parser.prog)
except Exception as e:
  print(f'Unable to configure logger: {e}')
  exit(1)
finally:
  log.trace(dj({'args':vars(args)}))


try:
  import ffmpeg
except Exception:
  log.exception('Unable to import ffmpeg module. Please run: pip3 install --user --upgrade ffmpeg-python')
  exit(1)


def probe(input=args.input):
  try:
    info = ffmpeg.probe(input)
    log.debug(f'Source media info:\n{ dj(info) }')
  except Exception:
    log.exception(f'Unable to probe input file: {input}')
    exit(1)
  return info


def extravf(video):
  try:
    for filter in args.extravf:
      video = video.filter(filter)
  except Exception:
    log.exception('Error applying extra video filters')
    exit(1)
  return video


def speed(video):
  if args.speed:
    try:
      video = video.filter('setpts', f'{args.speed}*PTS')
    except Exception:
      log.exception('Unable to modify speed')
      exit(1)
  return video


def fps(video):
  if args.fps:
    try:
      video = video.filter('fps', args.fps)
    except Exception:
      log.exception('Unable to modify FPS')
      exit(1)
  return video


def scale(video, info):
  srcwidth = info['streams'][0]['coded_width']
  srcheight = info['streams'][0]['coded_height']
  dstwidth = srcwidth
  dstheight = srcheight
  if args.width: dstwidth = args.width
  if args.height: dstheight = args.height
  if args.width and not args.height: dstheight = -1
  if args.height and not args.width: dstwidth = -1
  if args.maxdimension:
    if srcwidth > srcheight:
      if srcwidth > args.maxdimension:
        dstwidth = args.maxdimension
        dstheight = -1
    else:
      if srcheight > args.maxdimension:
        dstheight = args.maxdimension
        dstwidth = -1
  try:
    video = video.filter(
      'scale', dstwidth, dstheight, flags='lanczos'
    )
  except Exception:
    log.exception('Unable to scale')
    exit(1)
  return video


def text(video):
  if args.text:
    try:
      video = video.drawtext(
        fix_bounds = True,
        fontcolor = 'white',
        fontsize = args.text_size,
        shadowx = 2,
        shadowy = 2,
        text = args.text,
        x = args.text_x,
        y = args.text_y,
      )
    except Exception:
      log.exception('Unable to overlay text')
      exit(1)
  return video


def palette(video):
  try:
    split = video.split()
    palette = split[0].filter('palettegen', stats_mode=args.palette)
    video = ffmpeg.filter([split[1],palette], 'paletteuse', dither=args.dither)
  except Exception:
    log.exception('Unable to generate palette')
    exit(1)
  return video


def trim(video, info):
  try:
    if args.last:
      video = video.trim(start = int(float(info['format']['duration'])) - args.last)
    elif args.start and not args.duration:
      video = video.trim(start = args.start)
    elif args.duration and not args.start:
      video = video.trim(duration = args.duration)
    elif args.duration and args.start:
      video = video.trim(start = args.start, duration = args.duration)
  except Exception:
    log.exception('Unable to cut to desired section')
    exit(1)
  return video


def denoise(video):
  if args.denoise:
    try:
      video = video.filter('hqdn3d')
    except Exception:
      log.exception('Unable to denoise')
      exit(1)
  return video


def sharpen(video):
  if args.sharpen:
    try:
      video = video.filter('cas', f'{args.sharpen}')
    except Exception:
      log.exception('Unable to sharpen')
      exit(1)
  return video


def autocrop(video):
  if args.autocrop:
    try:
      video = video.filter('cropdetect', limit=250, round=16, skip=0)
    except Exception:
      log.exception('Unable to automatically crop')
      exit(1)
  return video


def crop(video):
  if (args.crop_x and args.crop_y) or (args.crop_h and args.crop_w):
    cropargs = {}
    if args.crop_w: cropargs['w'] = args.crop_w
    if args.crop_h: cropargs['h'] = args.crop_h
    if args.crop_x: cropargs['x'] = args.crop_x
    if args.crop_y: cropargs['y'] = args.crop_y
    if len(cropargs) > 1 :
      try:
        video = video.filter('crop', **cropargs)
      except Exception:
        log.exception('Unable to automatically crop')
        exit(1)
  return video


def convert(input=args.input, info=probe()):
  video = ffmpeg.input(input)
  video = trim(video, info)
  video = autocrop(video)
  video = crop(video)
  video = scale(video, info)
  video = speed(video)
  video = fps(video)
  video = extravf(video)
  video = denoise(video)
  video = sharpen(video)
  video = text(video)
  video = palette(video)
  return video


def main():
  log.info(f'Converting "{args.input}" to gif...')
  video = convert()
  video = video.output(args.output, format='gif')
  if args.dry:
    log.info(f'ffmpeg command:\n{" ".join(video.compile())}')
    exit(0)
  elif args.overwrite:
    if args.overwrite and file_exists(args.output):
      log.info(f'Skipping existing file: {args.output}')
      exit(0)
    out, err = video.run(overwrite_output=args.overwrite)
  else:
    out, err = video.run()
  log.info(out)
  if err:
    log.error(err)
    exit(1)


main()

