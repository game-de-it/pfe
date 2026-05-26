"""
Standalone pygame.mixer worker for PFE BGM playback.

Commands are JSON lines on stdin. Events are JSON lines on stdout.
"""

import json
import os
import select
import sys
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")


def emit(event: str, **payload):
    payload["event"] = event
    print(json.dumps(payload), flush=True)


def handle_command(mixer, command: dict, state: dict) -> bool:
    cmd = command.get("cmd")
    try:
        if cmd == "load":
            path = command.get("path", "")
            mixer.music.load(path)
            state["playing"] = False
            emit("loaded", ok=True, path=path)
        elif cmd == "load_play":
            path = command.get("path", "")
            volume = float(command.get("volume", 0.5))
            loops = int(command.get("loops", 0))
            mixer.music.load(path)
            mixer.music.set_volume(volume)
            mixer.music.play(loops=loops)
            state["playing"] = True
            emit("loaded", ok=True, path=path)
            emit("playing", ok=True)
        elif cmd == "play":
            loops = int(command.get("loops", 0))
            mixer.music.play(loops=loops)
            state["playing"] = True
            emit("playing", ok=True)
        elif cmd == "stop":
            mixer.music.stop()
            state["playing"] = False
            emit("stopped")
        elif cmd == "pause":
            mixer.music.pause()
            state["playing"] = False
            emit("paused")
        elif cmd == "unpause":
            mixer.music.unpause()
            state["playing"] = True
            emit("playing", ok=True)
        elif cmd == "volume":
            mixer.music.set_volume(float(command.get("value", 0.5)))
        elif cmd == "quit":
            mixer.music.stop()
            return False
    except Exception as e:
        emit("error", cmd=cmd, error=str(e))
        if cmd in ("load", "play", "unpause"):
            state["playing"] = False
    return True


def main():
    try:
        import pygame.mixer as mixer

        mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=8192)
        mixer.init(frequency=44100, size=-16, channels=2, buffer=8192)
        init_info = mixer.get_init()
        if init_info is None:
            emit("error", error="pygame.mixer.get_init() returned None")
            return 1
        emit("ready", frequency=init_info[0], format=init_info[1], channels=init_info[2])
    except Exception as e:
        emit("error", error=str(e))
        return 1

    state = {"playing": False}
    running = True
    try:
        while running:
            readable, _, _ = select.select([sys.stdin], [], [], 0.1)
            if readable:
                line = sys.stdin.readline()
                if not line:
                    break
                try:
                    command = json.loads(line)
                except Exception as e:
                    emit("error", error=f"invalid command: {e}")
                    continue
                running = handle_command(mixer, command, state)

            if state["playing"] and not mixer.music.get_busy():
                state["playing"] = False
                emit("ended")
    except KeyboardInterrupt:
        pass

    try:
        mixer.music.stop()
        mixer.quit()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
