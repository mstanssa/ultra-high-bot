#!/usr/bin/env bash
# تثبيت ffmpeg وقت التشغيل فقط
if ! command -v ffmpeg &> /dev/null
then
  echo "Installing ffmpeg..."
  apt-get update -y && apt-get install -y ffmpeg
fi

python3 bot.py
