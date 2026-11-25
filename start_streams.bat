@echo off
start "Main Publisher" cmd /k "ffmpeg -re -stream_loop -1 -i test.mp4 -an -vf scale=1920:1080 -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:8554/main"
start "Sub Publisher" cmd /k "ffmpeg -re -stream_loop -1 -i test.mp4 -an -vf scale=640:360,fps=10 -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p -g 10 -keyint_min 10 -sc_threshold 0 -f rtsp -rtsp_transport tcp rtsp://127.0.0.1:8554/sub"
