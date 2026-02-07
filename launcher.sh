#!/bin/bash

# Pyxel ROM Launcher - Auto-restart script
# Automatically restarts the launcher after the game ends
export SDL_AUDIODRIVER=alsa
export SDL_GAMECONTROLLERCONFIG="19009b4d4b4800000111000000010000,retrogame_joypad,a:b0,b:b1,x:b2,y:b3,back:b8,guide:b10,start:b9,leftstick:b11,rightstick:b12,leftshoulder:b4,rightshoulder:b5,dpup:b13,dpdown:b14,dpleft:b15,dpright:b16,leftx:a0,lefty:a1,rightx:a2,righty:a3,lefttrigger:b6,righttrigger:b7,crc:4d9b,platform:Linux"

# Activate the virtual environment
source /home/ark/venv-pyxel/bin/activate

# Change to the launcher directory
cd /home/ark/pd

# Start the launcher in an infinite loop
# Automatically restart when the launcher exits (after ROM launch)
while true; do
    echo "Starting Pyxel ROM Launcher..."
    python3 main.py

    # Check the exit code
    EXIT_CODE=$?

    # If normal exit (e.g., exit with B button), break out of the loop
    # The default exit code for pyxel.quit() is 0
    # ROM launch also exits with 0, so the loop continues

    echo "Launcher exited with code $EXIT_CODE"

    # Add a short wait time (to prevent rapid restarts)
    sleep 0.5
done
