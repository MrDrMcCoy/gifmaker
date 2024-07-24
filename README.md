# Tools and procedures for making better GIFs

## About

There are many tools out there for turning videos into GIFs, but the quality for most of them is quite lacking in my opinion. It is possible to produce GIFs that look like a video that's been a bit overly compressed, as opposed to the banded, splotchy, seen-through-a-screen-door images that most tools produce.

The downside to this is that I have yet to make a standalone GUI for my script. The command-line tools are easy to use, but do require a terminal environment. This makes Mac and Linux use easy, but Windows users will probably need WSL. `gifski` (linked below) has some 3rd-party GUI tools for Mac and Windows, but I am a Linux user and have no idea if they're any good.

## Prerequisites

1. Python 3.10+
2. [ffmpeg](https://ffmpeg.org/download.html)
3. [gifski](https://gif.ski/)
4. `ffgif.py` from this repo.
5. [yt-dlp](https://github.com/yt-dlp/yt-dlp) (optional)
6. [Kdenlive](https://kdenlive.org) (optional)
7. [LosslessCut](https://www.mifi.no/losslesscut/) (optional)

## General tips and tricks

- Your GIF should probably not exceed 8MB in size, as most chat platforms don't allow attachments larger than this.
- Frame rates and resolution are two of the biggest contributors to GIFs being too large for various chat platforms. In modern video codecs, each frame is stored as a difference of the frame that came before it, allowing the unchanged bits to not take up space. GIFs store each frame fully, and with a pretty rudimentary algorithm. The only surefire way to keep the file size small is to reduce the resolution and frame rates. **12 frames per second (FPS)**, which is about half the speed of most movies, is a pretty good balance. A resolution that **fits within 640x480**, and *<= 25% smaller than the source* is a good starting point. Resolution is the thing that you should focus most on for keeping the file size small.
- Be aware of dithering methods. Dithering is the process of taking a sample of a large set of colors/shades, making a smaller palette of them, and spreading those colors around in a way that makes your brain infer other colors that ought to be between them. GIFs only support 256 colors, so dithering is pretty necessary. Some dithering algorithms may introduce banding, noise, and inflate the file size, and sometimes the palette generation process is good enough that the result looks better without additional dithering. Experiment with this for each video to see what works best and yields the smallest file. You only need to worry about this with the `ffgif.py` method, as `gifsky` has its own engine for palette generation that covers dithering.
- Every time you convert or do anything to re-compress a video (excepting the specific use of lossless encoding), you noticeably hurt the quality. Do whatever you can to reduce steps that result in lossy re-compressing. A good lossless codec you can use for intermediate editing, etc is `ffv1`. You can also use `huffyuv` or the lossless profiles for other codecs if you know what you're doing. Lossless video is quite large on disk, but you can delete these files when you're done.

## Acquire your source

Almost any input video will do. If you want to grab the highest-quality source from most video sites, `yt-dlp` (linked above) will help you download it.

## Edit/trim source

If your video needs no trimming, you can skip this step. Most of the time, you will probably want to cut a smaller section of the video to be your GIF.

- The easiest way to trim your video without quality loss is to use `LosslessCut` to spit out the section you want to turn into a GIF.
- If you just need basic trimming, you can just make a note of the start time and how long the clip should be from the start time, which you can pass to the command-line tools for lossless trimming (instructions below).
- If you need to do more complex editing, want extra precision, or need to add text, I recommend using `Kdenlive`. You may need to make some custom resolution profiles if you want to have an easier time cropping the video, and I recommend always exporting to an MKV file with the `ffv1` codec, which is lossless. Audio can be discarded on the timeline or at export, since GIFs don't support that anyway.

## Generate your GIF

### Method 1: `ffmpeg` -> `gifski`

This is the easiest method, requiring the least knowledge and often has the best results.

```shell
ffmpeg -i <INPUT_VIDEO> -r <FRAMES_PER_SECOND> -f yuv4mpegpipe - | gifski --width=<WIDTH> --height=<HEIGHT> --output=<OUTPUT_GIF> -
```

#### Additional `ffmpeg` options

- If you are trimming the source video by timestamp instead of one of the graphical tools, you can add `-ss <START_TIME> -t <DURATION>` between `ffmpeg` and `-i`.
- If you want to add video filters, you add them as a comma-separated list after `-vf`, which should be placed between the frames per second and `-f` options shown above. Here are some common useful ones:
  - `cas=0.8`: This adds contrast-adaptive sharpening to boost detail for a slight increase in file size. The decimal number between `0` and `1` controls its strength.
  - `hqdn3d`: This applies a high-quality temporal de-noiser. This will often make files smaller, at a slight cost to detail.
  - More filters can be found on the [ffmpeg website](https://ffmpeg.org/ffmpeg-filters.html)

#### Additional `gifski` options

Some additional options for `gifski` can be found by running `gifski --help`.

Most of the time, you should just set the `<FRAMES_PER_SECOND>` to `12` on the `ffmpeg`-side and play with the resolution on the `gifski`-side until you get the best quality that is under 8MB in file size.

### Method 2: `ffgif.py`

This is a script I wrote that wraps `ffmpeg` using the `ffmpeg-python` library to simplify much of the arcane incantations required for `ffmpeg` to make a quality GIF. It also has some rudimentary options for cropping, adding text, denoising, etc. Here's the most basic usage:

```shell
python3 ffgif.py --input=<INPUT_VIDEO> --output=<OUTPUT_GIF> --width=<WIDTH> --height=<HEIGHT>
```

The defaults will typically generate a good quality GIF, but this is where experimentation really starts to pay off. Adding a sharpening and/or denoising filter, enabling one of the dithering options, and telling the palette generator to use full colors or a diff will all affect the file size and quality of the output GIF. As always, the biggest determining factor for file size is the resolution, so focus on that once you have the best visual quality from the other options.

Here is the full set of options that it provides, which can be found by running `python3 ffgif.py --help`:

```
  -i INPUT, --input INPUT
                        Input file path
  -o OUTPUT, --output OUTPUT
                        Output file path
  -s START, --start START
                        Start time of input video
  -d DURATION, --duration DURATION
                        Duration from start time of input video to select for gif
  -l LAST, --last LAST  Select last N seconds of video
  -W WIDTH, --width WIDTH
                        Max width
  -H HEIGHT, --height HEIGHT
                        Max height
  -m MAXDIMENSION, --maxdimension MAXDIMENSION
                        Max pixels for width and height
  -a, --autocrop        Automatically crop black bars
  --crop-w CROP_W       Crop width
  --crop-h CROP_H       Crop height
  --crop-x CROP_X       Crop X position
  --crop-y CROP_Y       Crop Y position
  -r FPS, --fps FPS     Number of frames per second (default: 12)
  -S SPEED, --speed SPEED
                        Playback speed of gif as a decimal value of input video
  -t TEXT, --text TEXT  Add text overlay in lower third
  --text-x TEXT_X       Add text at horizontal offset (default: w*0.05)
  --text-y TEXT_Y       Add text at vertical offset (default: h*0.9)
  --text-size TEXT_SIZE
                        Text overlay font size
  --sharpen {0.1,0.2,0.3,0.4,0.5,0.6,0.8,0.9,1.0}
                        Sharpen video in contrast-aware fashion. Takes a decimal value between 0 and 1 to represent percentage of strength
  --denoise             Denoise in temproally-aware fashion
  -f EXTRAVF, --extravf EXTRAVF
                        Extra video filters to pass to ffmpeg, can be specified more than once
  -p {diff,full}, --palette {diff,full}
                        Stats mode for palettegen (default: full)
  -D {none,floyd_steinberg,sierra2}, --dither {none,floyd_steinberg,sierra2}
                        Dithering mode (default: none)
  -O, --overwrite       Overwrite destination file if exists
  -L LOGLEVEL, --loglevel LOGLEVEL
                        Logging level. (Default: INFO)
  --dry                 Dry run
```
