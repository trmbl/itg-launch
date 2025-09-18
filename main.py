import logging
import signal
import subprocess
from sys import stdout
import time
import psutil
import mouse  # type: ignore

logging.basicConfig(level="INFO", stream=stdout)

logger = logging.getLogger(__name__)

signaled: bool = False


def main() -> None:
    camostudio_proc: psutil.Process | None = None
    itgmania_proc: psutil.Process | None = None
    obs_proc: psutil.Process | None = None

    def on_signal(signum, frame):
        global signaled
        signaled = True

    signal.signal(signal.SIGINT, on_signal)
    signal.signal(signal.SIGTERM, on_signal)

    for proc in psutil.process_iter():
        if is_camostudio(proc):
            camostudio_proc = proc
        elif is_itgmania(proc):
            itgmania_proc = proc
        elif is_obs_recording(proc):
            obs_proc = proc

    if itgmania_proc:
        logger.info("itgmania is already started, exiting...")
        return

    if obs_proc:
        logger.info("obs is already recording, exiting...")
        return

    try:
        if not camostudio_proc:
            logger.info("camostudio process not found, starting it")
            camostudio_proc = psutil.Popen(
                ["C:/Users/Vincent/AppData/Local/Microsoft/WindowsApps/camostudio.exe"]
            )

        if signaled:
            return

        logger.info("starting itgmania")
        itgmania_proc = psutil.Popen(["C:/Games/ITGMania/Program/ITGmania.exe"])

        if signaled:
            return

        logger.info("waiting 5 seconds...")
        time.sleep(5)

        if signaled:
            return

        logger.info("sending focus to itgmania")
        focus_process("itgmania.exe")

        logger.info("sending mouse click to ensure app is focused")
        mouse.click()

        if signaled:
            return

        logger.info("waiting 1 second...")
        time.sleep(1)

        if signaled:
            return

        logger.info("starting new obs process in recording mode")
        obs_proc = start_obs()

        obs_dead_start: float | None = None

        logger.info("waiting for itgmania to close...")
        while not signaled and itgmania_proc.is_running():
            if obs_proc.is_running():
                obs_dead_start = None
            elif obs_dead_start is None:
                obs_dead_start = time.time()
            elif time.time() - obs_dead_start > 5:
                logger.info("obs exited, restarting it")
                obs_proc = start_obs()

            time.sleep(1)
            focus_process("itgmania.exe")
    finally:
        if signaled:
            logger.info("process signaled to stop, exiting...")
        elif itgmania_proc and not itgmania_proc.is_running():
            logger.info("itgmania exited, exiting...")

        if obs_proc and obs_proc.is_running():
            logger.info("closing obs process")
            close_proc_by_pid(obs_proc.pid)


def close_proc_by_pid(pid: int):
    subprocess.run(["C:/tools/nircmdc.exe", "closeprocess", f"/{pid}"])


def start_obs() -> psutil.Process:
    for proc in psutil.process_iter():
        if is_obs_recording(proc):
            logger.info("obs is already recording, no new instance will be started")
            return proc

    # See https://obsproject.com/kb/launch-parameters
    return psutil.Popen(
        [
            "C:/Program Files/obs-studio/bin/64bit/obs64.exe",
            "--startrecording",
            "--studio-mode",
            "--scene",
            "itgmania",
            "-m",
        ],
        cwd="C:/Program Files/obs-studio/bin/64bit",
    )


def is_obs(proc: psutil.Process):
    return proc.name().endswith("obs64.exe")


def is_obs_recording(proc: psutil.Process):
    return is_obs(proc) and any(c.find("--startrecording") >= 0 for c in proc.cmdline())


def is_camostudio(proc: psutil.Process):
    return proc.name().endswith("camostudio.exe")


def is_itgmania(proc: psutil.Process):
    return proc.name().endswith("itgmania.exe")


def focus_process(name: str):
    # See https://www.nirsoft.net/utils/nircmd2.html#using
    subprocess.run(["C:/tools/nircmdc.exe", "win", "activate", "process", name])
    subprocess.run(
        [
            "C:/tools/nircmdc.exe",
            "win",
            "settopmost",
            "process",
            name,
            "1",
        ]
    )


if __name__ == "__main__":
    main()
