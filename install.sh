#!/usr/bin/env bash
if [[ "$1" == "" ]]; then
  echo "Usage: ./install.sh [install_directory]"
  exit 1
fi

rm -rf "$1/gimp-videoplayer"
mkdir "$1/gimp-videoplayer"

cp plugin.py "$1/gimp-videoplayer/gimp-videoplayer.py"
cp -r .venv/lib/python3.*/site-packages "$1/gimp-videoplayer/packages"

if [ -d ".venv/lib64" ]; then
  cp -r .venv/lib64/python3.*/site-packages "$1/gimp-videoplayer/packages64"
fi

if [ -f "video-ba.mp4" ]; then
  cp video-ba.mp4 "$1/gimp-videoplayer/video.mp4"
fi