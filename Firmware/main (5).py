#!/usr/bin/env python3
import os
import sys
import time
import queue
import threading
import subprocess
from datetime import datetime
from pathlib import Path
import pytz
import serial
import pynmea2
import RPi.GPIO as GPIO
from PIL import Image, ImageDraw, ImageFont
try:
    import st7789
    HAS_DISPLAY = True
except ImportError:
    HAS_DISPLAY = False
    print("display library not found")
try:
    from picamera2 import Picamera2, MappedArray
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FileOutput
    HAS_CAMERA = True
except ImportError:
    HAS_CAMERA = False
    print("camera library not found")
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print("openCV not found")
TZ          = pytz.timezone("Europe/Prague")   # change to your region and place
STORAGE_DIR = Path("/home/pi/dashcam")
CHUNKS_DIR  = STORAGE_DIR / "chunks"
HOURS_DIR   = STORAGE_DIR / "hours"
VIDEOS_DIR  = STORAGE_DIR / "videos"
TEMP_DIR    = STORAGE_DIR / "temp"
for _d in (CHUNKS_DIR, HOURS_DIR, VIDEOS_DIR, TEMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)
DISP_W, DISP_H   = 320, 240
CAM_REC_W         = 640
CAM_REC_H         = 480
CAM_PRV_W         = 320
CAM_PRV_H         = 240
REC_FPS           = 15    # change to more if u need to but RP Pi might overheat or have not enough memory
REC_BITRATE       = 4_000_000
AUDIO_DEVICE      = "hw:1,0"
AUDIO_RATE        = 44100
GPS_PORT          = "/dev/ttyS0"
GPS_BAUD          = 9600
CHUNK_SECS        = 60
BTN_RECORD   = 23
BTN_SCREEN   = 22
BTN_SHUTDOWN = 3
BTN_PLAYBACK = 5
BTN_BACK     = 6
BTN_STOPLAY  = 12
BTN_FORWARD  = 13
PIN_BL       = 24
ALL_BTNS = [BTN_RECORD, BTN_SCREEN, BTN_SHUTDOWN,
            BTN_PLAYBACK, BTN_BACK, BTN_STOPLAY, BTN_FORWARD]
_FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
try:
    FONT_LG = ImageFont.truetype(_FONT_PATH, 18)
    FONT_MD = ImageFont.truetype(_FONT_PATH, 14)
    FONT_SM = ImageFont.truetype(_FONT_PATH, 11)
except OSError:
    FONT_LG = FONT_MD = FONT_SM = ImageFont.load_default()
_lock = threading.Lock()
st = {
    "recording":  False,
    "screen_on":  True,
    "pb_active":  False,
    "pb_paused":  False,
    "pb_pos":     0.0,
    "pb_speed":   1.0,
    "pb_file":    None,
    "chunk_num":  0,
}
_gps      = {"lat": 0.0, "lon": 0.0, "speed_kmh": 0.0, "fix": False}
_gps_lock = threading.Lock()
_pipeline_trigger = threading.Event()

def gps_thread():
    while True:
        try:
            ser = serial.Serial(GPS_PORT, GPS_BAUD, timeout=2)
            print("GPS connected, sucesfuly")
            while True:
                try:
                    raw = ser.readline().decode("ascii", errors="replace").strip()
                    if raw.startswith(("$GPRMC", "$GNRMC")):
                        msg = pynmea2.parse(raw)
                        with _gps_lock:
                            if msg.status == "A":
                                _gps["lat"]       = msg.latitude
                                _gps["lon"]       = msg.longitude
                                _gps["speed_kmh"] = msg.spd_over_grnd * 1.852
                                _gps["fix"]       = True
                            else:
                                _gps["fix"] = False
                except (pynmea2.ParseError, AttributeError, ValueError):
                    pass
        except Exception as e:
            print(f"GPS error: {e}")
            time.sleep(5)

def gps_snap():
    with _gps_lock:
        return dict(_gps)

_disp       = None
_disp_lock  = threading.Lock()
_disp_dirty = threading.Event()
_disp_frame = [None]

def init_display():
    global _disp
    if not HAS_DISPLAY:
        return
    _disp = st7789.ST7789(
        port=0, cs=0, dc=25, rst=27,
        backlight=PIN_BL,
        width=DISP_W, height=DISP_H,
        rotation=90,
        spi_speed_hz=40_000_000,
    )
    _disp.begin()

def set_screen(on: bool):
    st["screen_on"] = on
    try:
        GPIO.output(PIN_BL, GPIO.HIGH if on else GPIO.LOW)
    except Exception:
        pass

def push_frame(img: "Image.Image"):
    _disp_frame[0] = img
    _disp_dirty.set()

def display_driver_thread():
    while True:
        _disp_dirty.wait()
        _disp_dirty.clear()
        img = _disp_frame[0]
        if img and _disp and st["screen_on"]:
            try:
                with _disp_lock:
                    _disp.display(img.convert("RGB"))
            except Exception as e:
                print(f"Display error: {e}")

def msg_screen(*lines, bg=(0, 0, 0), fg=(255, 255, 255)):
    img = Image.new("RGB", (DISP_W, DISP_H), bg)
    d   = ImageDraw.Draw(img)
    y   = DISP_H // 2 - len(lines) * 14
    for line in lines:
        d.text((DISP_W // 2, y), line, fill=fg, anchor="mt", font=FONT_MD)
        y += 26
    push_frame(img)

OVL_GREEN  = (100, 255, 100)
OVL_WHITE  = (255, 255, 255)
OVL_YELLOW = (255, 240,  80)
OVL_RED    = (255,  60,  60)

def _overlay_numpy(arr):
    if not HAS_CV2:
        return
    gps = gps_snap()
    now = datetime.now(TZ)
    h, w = arr.shape[:2]
    bar_h = 40
    arr[h - bar_h:h] = (arr[h - bar_h:h].astype("float32") * 0.25).astype(arr.dtype)
    spd = f"{gps['speed_kmh']:5.1f} km/h" if gps["fix"] else " ??.? km/h"
    cv2.putText(arr, spd, (6, h - bar_h + 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, OVL_GREEN, 1, cv2.LINE_AA)
    cv2.putText(arr, now.strftime("%H:%M:%S"), (w // 2 - 42, h - bar_h + 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, OVL_WHITE, 1, cv2.LINE_AA)
    cv2.putText(arr, now.strftime("%d.%m.%Y"), (w - 108, h - bar_h + 16),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, OVL_WHITE, 1, cv2.LINE_AA)
    coord = (f"{gps['lat']:.5f}N  {gps['lon']:.5f}E"
             if gps["fix"] else "GPS: finding signal..")
    cv2.putText(arr, coord, (6, h - 6),
                cv2.FONT_HERSHEY_SIMPLEX, 0.40, OVL_YELLOW, 1, cv2.LINE_AA)
    cv2.circle(arr, (w - 14, h - bar_h + 12), 7, OVL_RED, -1)

def _overlay_pil(img: "Image.Image") -> "Image.Image":
    gps  = gps_snap()
    now  = datetime.now(TZ)
    draw = ImageDraw.Draw(img)
    w, h = img.size
    bar_h = 40
    draw.rectangle([(0, h - bar_h), (w, h)], fill=(0, 0, 0, 210))
    y1, y2 = h - bar_h + 3, h - 13
    spd = f"{gps['speed_kmh']:.1f} km/h" if gps["fix"] else "?? km/h"
    draw.text((4, y1), spd, font=FONT_MD, fill=(100, 255, 100))
    draw.text((w // 2, y1),      now.strftime("%H:%M:%S"),
              font=FONT_MD, fill=(255, 255, 255), anchor="mt")
    draw.text((w // 2, y1 + 17), now.strftime("%d.%m.%Y"),
              font=FONT_SM, fill=(200, 200, 200), anchor="mt")
    coord = (f"{gps['lat']:.5f}N  {gps['lon']:.5f}E"
             if gps["fix"] else "GPS: finding..")
    draw.text((4, y2), coord, font=FONT_SM, fill=(255, 240, 80))
    draw.ellipse([(w - 22, y1), (w - 8, y1 + 14)], fill=(255, 50, 50))
    return img

_cam        : "Picamera2 | None" = None
_audio_proc : "subprocess.Popen | None" = None
_cur_base   : "str | None" = None
_rotate_tmr : "threading.Timer | None" = None

def _rec_overlay_callback(request):
    with MappedArray(request, "main") as m:
        _overlay_numpy(m.array)

def _rec_preview_thread():
    global _cam
    while st["recording"] and _cam:
        try:
            arr_yuv = _cam.capture_array("lores")
            if HAS_CV2:
                rgb = cv2.cvtColor(arr_yuv, cv2.COLOR_YUV420p2RGB)
                img = Image.fromarray(rgb)
            else:
                img = Image.fromarray(arr_yuv[:CAM_PRV_H, :CAM_PRV_W])
            img = _overlay_pil(img)
            push_frame(img)
        except Exception as e:
            print(f"preview error: {e}")
        time.sleep(1 / 12)

def _start_audio_to(wav_path: str) -> "subprocess.Popen":
    return subprocess.Popen(
        ["arecord", "-D", AUDIO_DEVICE,
         "-c", "1", "-r", str(AUDIO_RATE), "-f", "S16_LE", wav_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

def _mux_chunk(base: str):
    h264    = base + ".h264"
    wav     = base + ".wav"
    tmp_mp4 = base + "_tmp.mp4"
    ts      = Path(base).name
    out     = str(CHUNKS_DIR / f"{ts}.mp4")
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-framerate", str(REC_FPS),
             "-i", h264, "-c:v", "copy", tmp_mp4],
            check=True, capture_output=True, timeout=60,
        )
        subprocess.run(
            ["ffmpeg", "-y",
             "-i", tmp_mp4, "-i", wav,
             "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
             "-shortest", out],
            check=True, capture_output=True, timeout=120,
        )
        print(f"chunk saved: {Path(out).name}")
        _pipeline_trigger.set()
    except subprocess.CalledProcessError as e:
        print(f"chunk mux failed ({Path(base).name}): {e.stderr.decode(errors='replace')[:100]}")
    except Exception as e:
        print(f"chunk error: {e}")
    finally:
        for f in (h264, wav, tmp_mp4):
            try:
                os.remove(f)
            except FileNotFoundError:
                pass

def _rotate_chunk():
    global _cam, _audio_proc, _cur_base, _rotate_tmr
    if not st["recording"]:
        return
    old_base  = _cur_base
    old_audio = _audio_proc
    ts        = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
    new_base  = str(TEMP_DIR / ts)
    if _cam:
        try:
            _cam.stop_recording()
        except Exception as e:
            print(f"Encoder stop error: {e}")
        try:
            _cam.start_recording(
                H264Encoder(bitrate=REC_BITRATE),
                FileOutput(new_base + ".h264"),
            )
        except Exception as e:
            print(f"encoder start error: {e}")
    _audio_proc = _start_audio_to(new_base + ".wav")
    if old_audio:
        old_audio.terminate()
        try:
            old_audio.wait(timeout=4)
        except subprocess.TimeoutExpired:
            old_audio.kill()
    _cur_base   = new_base
    _rotate_tmr = threading.Timer(CHUNK_SECS, _rotate_chunk)
    _rotate_tmr.daemon = True
    _rotate_tmr.start()
    if old_base:
        threading.Thread(target=_mux_chunk, args=(old_base,), daemon=True).start()
    with _lock:
        st["chunk_num"] += 1
    print(f"Chunk total this session: {st['chunk_num']}")

def start_recording():
    global _cam, _audio_proc, _cur_base, _rotate_tmr
    with _lock:
        if st["recording"]:
            return
    if not HAS_CAMERA:
        msg_screen("camera", "unavalible!", bg=(60, 0, 0), fg=(255, 100, 100))
        return
    ts        = datetime.now(TZ).strftime("%Y%m%d_%H%M%S")
    _cur_base = str(TEMP_DIR / ts)
    _cam = Picamera2()
    cfg  = _cam.create_video_configuration(
        main  = {"size": (CAM_REC_W, CAM_REC_H), "format": "RGB888"},
        lores = {"size": (CAM_PRV_W, CAM_PRV_H), "format": "YUV420"},
    )
    _cam.configure(cfg)
    _cam.pre_callback = _rec_overlay_callback
    _cam.start_recording(
        H264Encoder(bitrate=REC_BITRATE),
        FileOutput(_cur_base + ".h264"),
    )
    _audio_proc = _start_audio_to(_cur_base + ".wav")
    with _lock:
        st["recording"] = True
        st["chunk_num"] = 0
    threading.Thread(target=_rec_preview_thread, daemon=True).start()
    _rotate_tmr = threading.Timer(CHUNK_SECS, _rotate_chunk)
    _rotate_tmr.daemon = True
    _rotate_tmr.start()
    print("Rrcording start")

def stop_recording(save: bool = True):
    global _cam, _audio_proc, _cur_base, _rotate_tmr
    with _lock:
        if not st["recording"]:
            return
        st["recordin"] = False
    if _rotate_tmr:
        _rotate_tmr.cancel()
        _rotate_tmr = None
    old_cam   = _cam
    old_audio = _audio_proc
    old_base  = _cur_base
    _cam = _audio_proc = _cur_base = None
    if old_audio:
        old_audio.terminate()
        try:
            old_audio.wait(timeout=4)
        except subprocess.TimeoutExpired:
            old_audio.kill()
    if old_cam:
        try:
            old_cam.stop_recording()
            old_cam.close()
        except Exception as e:
            print(f"cam stop error: {e}")
    if save and old_base:
        msg_screen("savin..", "please wait", bg=(0, 0, 60))
        threading.Thread(target=_mux_chunk, args=(old_base,), daemon=True).start()
    else:
        if old_base:
            for ext in (".h264", ".wav"):
                try:
                    os.remove(old_base + ext)
                except FileNotFoundError:
                    pass
        msg_screen("cancelled")

def _is_valid(path: Path) -> bool:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error",
             "-select_streams", "v:0",
             "-show_entries", "stream=codec_type",
             "-of", "default=noprint_wrappers=1:nokey=1",
             str(path)],
            capture_output=True, timeout=15,
        )
        return r.returncode == 0 and b"video" in r.stdout
    except Exception:
        return False

def _ffmpeg_concat(sources: list, output: Path) -> bool:
    concat_txt = TEMP_DIR / "_concat_list.txt"
    try:
        with open(concat_txt, "w") as f:
            for p in sources:
                f.write(f"file '{p}'\n")
        r = subprocess.run(
            ["ffmpeg", "-y",
             "-f", "concat", "-safe", "0",
             "-i", str(concat_txt),
             "-c", "copy", str(output)],
            capture_output=True, timeout=600,
        )
        return r.returncode == 0
    except Exception as e:
        print(f"concat error: {e}")
        return False
    finally:
        try:
            concat_txt.unlink()
        except FileNotFoundError:
            pass

def _assemble_hour(hour_key: str):
    out = HOURS_DIR / f"{hour_key}.mp4"
    if out.exists():
        return
    date_part = hour_key[:8]
    hh_part   = hour_key[9:11]
    candidates = sorted(
        c for c in CHUNKS_DIR.glob(f"{date_part}_{hh_part}*.mp4")
        if c.stem[9:11] == hh_part
    )
    if not candidates:
        return
    valid   = [c for c in candidates if _is_valid(c)]
    corrupt = set(candidates) - set(valid)
    for c in corrupt:
        print(f"skipping corrupt chunk: {c.name}")
        try:
            c.rename(c.with_suffix(".corrupt"))
        except Exception:
            pass
    if not valid:
        print(f"no valid chunks for the hour {hour_key}, skiping")
        return
    print(f"assembling hour {hour_key}: {len(valid)} of {len(candidates)} chunks")
    if _ffmpeg_concat(valid, out):
        print(f"hour file ready: {out.name}")
        for c in valid:
            try:
                c.unlink()
            except Exception:
                pass
    else:
        print(f"hour asembly failed: {hour_key}")
        try:
            out.unlink()
        except FileNotFoundError:
            pass

def _assemble_day(date_key: str):
    try:
        d = datetime.strptime(date_key, "%Y%m%d")
        friendly = f"{d.day}.{d.month}.{d.year}"
    except ValueError:
        friendly = date_key
    out = VIDEOS_DIR / f"{friendly}.mp4"
    if out.exists():
        return
    candidates = sorted(HOURS_DIR.glob(f"{date_key}_*.mp4"))
    if not candidates:
        return
    valid   = [c for c in candidates if _is_valid(c)]
    corrupt = set(candidates) - set(valid)
    for c in corrupt:
        print(f"skipping corupted hour file: {c.name}")
        try:
            c.rename(c.with_suffix(".corrupt"))
        except Exception:
            pass
    if not valid:
        print(f"no valid hour files for {friendly}, skipping")
        return
    print(f"asembling day {friendly}: {len(valid)} of {len(candidates)} hours")
    if _ffmpeg_concat(valid, out):
        print(f"day file ready: {out.name}")
        for c in valid:
            try:
                c.unlink()
            except Exception:
                pass
    else:
        print(f"day asembly failed: {friendly}")
        try:
            out.unlink()
        except FileNotFoundError:
            pass

def assembly_pipeline_thread():
    print("asembly pipeline started")
    while True:
        now              = datetime.now(TZ)
        current_hour_key = now.strftime("%Y%m%d_") + now.strftime("%H")
        today_key        = now.strftime("%Y%m%d")
        chunk_hour_keys: set[str] = set()
        for c in CHUNKS_DIR.glob("*.mp4"):
            stem = c.stem
            if len(stem) >= 11:
                hk = stem[:8] + "_" + stem[9:11]
                chunk_hour_keys.add(hk)
        for hk in sorted(chunk_hour_keys):
            if st["recording"] and hk >= current_hour_key:
                continue
            if not st["recording"] and hk > current_hour_key:
                continue
            _assemble_hour(hk)
        hour_day_keys: set[str] = set()
        for h in HOURS_DIR.glob("*.mp4"):
            if len(h.stem) >= 8:
                hour_day_keys.add(h.stem[:8])
        for dk in sorted(hour_day_keys):
            if st["recording"] and dk >= today_key:
                continue
            if not st["recording"] and dk > today_key:
                continue
            _assemble_day(dk)
        _pipeline_trigger.wait(timeout=60)
        _pipeline_trigger.clear()

_pb_cmds   : "queue.Queue" = queue.Queue()
_pb_thread : "threading.Thread | None" = None

def _list_videos():
    return sorted(VIDEOS_DIR.glob("*.mp4"), reverse=True)

def start_playback():
    global _pb_thread
    if st["recording"]:
        msg_screen("stop soon", "recording")
        time.sleep(1)
        return
    files = _list_videos()
    if not files:
        msg_screen("none", "recordings", bg=(0, 0, 0), fg=(255, 200, 0))
        time.sleep(2)
        return
    with _lock:
        if st["pb_active"]:
            return
        st.update(pb_active=True, pb_paused=False,
                  pb_pos=0.0, pb_speed=1.0, pb_file=str(files[0]))
    while not _pb_cmds.empty():
        _pb_cmds.get_nowait()
    _pb_thread = threading.Thread(target=_pb_loop, daemon=True)
    _pb_thread.start()

def stop_playback():
    with _lock:
        if not st["pb_active"]:
            return
        st["pb_active"] = False
    _pb_cmds.put(("stop", 0))
    if _pb_thread:
        _pb_thread.join(timeout=3)
    msg_screen("ready")

def _pb_loop():
    if not HAS_CV2:
        msg_screen("OpenCV", "mising", bg=(60, 0, 0))
        st["pb_active"] = False
        return
    cap = cv2.VideoCapture(st["pb_file"])
    if not cap.isOpened():
        msg_screen("couldnt open", "file", bg=(60, 0, 0))
        st["pb_active"] = False
        return
    fps_nat      = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration     = total_frames / fps_nat
    frame_dt     = 1.0 / fps_nat
    last_t       = time.time()
    cap.set(cv2.CAP_PROP_POS_MSEC, st["pb_pos"] * 1000)
    while st["pb_active"]:
        while not _pb_cmds.empty():
            cmd, val = _pb_cmds.get_nowait()
            if cmd == "stop":
                st["pb_active"] = False
            elif cmd == "pause":
                st["pb_paused"] = not st["pb_paused"]
            elif cmd == "seek":
                new_pos = max(0.0, min(st["pb_pos"] + val, duration - 0.1))
                st["pb_pos"] = new_pos
                cap.set(cv2.CAP_PROP_POS_MSEC, new_pos * 1000)
                last_t = time.time()
        if not st["pb_active"]:
            break
        if st["pb_paused"]:
            time.sleep(0.05)
            continue
        now = time.time()
        if now - last_t < frame_dt / max(st["pb_speed"], 0.1):
            time.sleep(0.005)
            continue
        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            st["pb_pos"] = 0.0
            last_t = time.time()
            continue
        st["pb_pos"] = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        last_t = now
        vid_h = DISP_H - 22
        frame = cv2.resize(frame, (DISP_W, vid_h))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img   = Image.new("RGB", (DISP_W, DISP_H), (0, 0, 0))
        img.paste(Image.fromarray(frame), (0, 0))
        draw = ImageDraw.Draw(img)
        pct  = st["pb_pos"] / duration if duration > 0 else 0
        draw.rectangle([(0, vid_h), (DISP_W, vid_h + 4)], fill=(40, 40, 40))
        draw.rectangle([(0, vid_h), (int(DISP_W * pct), vid_h + 4)],
                       fill=(0, 180, 255))
        el_s  = int(st["pb_pos"])
        tot_s = int(duration)
        draw.text((4, vid_h + 6),
                  f"{el_s // 60:02d}:{el_s % 60:02d} / "
                  f"{tot_s // 60:02d}:{tot_s % 60:02d}",
                  font=FONT_SM, fill=(220, 220, 220))
        spd = st["pb_speed"]
        if abs(spd - 1.0) > 0.05:
            draw.text((DISP_W - 4, vid_h + 6), f"{spd:.1f}×",
                      font=FONT_SM, fill=(255, 220, 50), anchor="rt")
        if st["pb_paused"]:
            draw.text((DISP_W // 2, 10), "||  stopped",
                      font=FONT_MD, fill=(255, 200, 0), anchor="mt")
        push_frame(img)
    cap.release()
    st["pb_active"] = False

def idle_screen_thread():
    while True:
        if not st["recording"] and not st["pb_active"] and st["screen_on"]:
            gps = gps_snap()
            now = datetime.now(TZ)
            img  = Image.new("RGB", (DISP_W, DISP_H), (8, 8, 24))
            draw = ImageDraw.Draw(img)
            draw.rectangle([(0, 0), (DISP_W, 28)], fill=(0, 60, 120))
            draw.text((DISP_W // 2, 14), "DASHCAM",
                      font=FONT_LG, fill=(0, 220, 255), anchor="mm")
            draw.text((DISP_W // 2, 50), now.strftime("%H:%M:%S"),
                      font=FONT_LG, fill=(255, 255, 255), anchor="mt")
            draw.text((DISP_W // 2, 72), now.strftime("%A  %d.%m.%Y"),
                      font=FONT_SM, fill=(160, 160, 180), anchor="mt")
            if gps["fix"]:
                draw.text((DISP_W // 2, 95),
                          f"<> GPS  {gps['speed_kmh']:.1f} km/h",
                          font=FONT_MD, fill=(80, 255, 80), anchor="mt")
                draw.text((DISP_W // 2, 115),
                          f"{gps['lat']:.5f}- N",
                          font=FONT_SM, fill=(255, 240, 80), anchor="mt")
                draw.text((DISP_W // 2, 130),
                          f"{gps['lon']:.5f}- E",
                          font=FONT_SM, fill=(255, 240, 80), anchor="mt")
            else:
                draw.text((DISP_W // 2, 95), "- GPS: finding..",
                          font=FONT_MD, fill=(200, 200, 0), anchor="mt")
            n_days   = len(list(VIDEOS_DIR.glob("*.mp4")))
            n_chunks = len(list(CHUNKS_DIR.glob("*.mp4")))
            draw.text((DISP_W // 2, 152),
                      f"days: {n_days}  |  chunks: {n_chunks}",
                      font=FONT_SM, fill=(140, 140, 160), anchor="mt")
            draw.line([(0, DISP_H - 52), (DISP_W, DISP_H - 52)], fill=(30, 30, 60))
            draw.text((4, DISP_H - 49), "BTN1 recording  BTN2 Display",
                      font=FONT_SM, fill=(100, 100, 120))
            draw.text((4, DISP_H - 34), "BTN3 turn off   BTN4 play",
                      font=FONT_SM, fill=(100, 100, 120))
            draw.text((4, DISP_H - 19), "BTN5 <<  BTN6 P/S  BTN7 >>",
                      font=FONT_SM, fill=(100, 100, 120))
            draw.text((4, DISP_H - 5),  "BTN5/7 hold = speed",
                      font=FONT_SM, fill=(80, 80, 100))
            push_frame(img)
        time.sleep(1)

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    for btn in ALL_BTNS:
        GPIO.setup(btn, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(PIN_BL, GPIO.OUT, initial=GPIO.HIGH)

def button_poll_thread():
    DEBOUNCE   = 0.08
    HOLD_DELAY = 0.40
    prev    = {b: False for b in ALL_BTNS}
    last_dn = {b: 0.0   for b in ALL_BTNS}
    dn_at   = {b: None  for b in [BTN_BACK, BTN_FORWARD]}
    hlast   = {b: 0.0   for b in [BTN_BACK, BTN_FORWARD]}
    while True:
        now = time.time()
        for btn in ALL_BTNS:
            pressed = (GPIO.input(btn) == GPIO.LOW)
            was     = prev[btn]
            prev[btn] = pressed
            if pressed and not was:
                if now - last_dn[btn] > DEBOUNCE:
                    last_dn[btn] = now
                    _on_press(btn)
                    if btn in dn_at:
                        dn_at[btn] = now
                        hlast[btn] = now
            elif not pressed and was:
                if btn in dn_at:
                    dn_at[btn] = None
            elif pressed and was and btn in dn_at:
                if dn_at[btn] and (now - dn_at[btn]) > HOLD_DELAY:
                    dt         = now - hlast[btn]
                    hlast[btn] = now
                    hold_dur   = now - dn_at[btn]
                    speed      = min(10.0 + hold_dur ** 2 * 14.0, 120.0)
                    direction  = 1 if btn == BTN_FORWARD else -1
                    _pb_cmds.put(("seek", direction * speed * dt))
        time.sleep(0.05)

def _on_press(btn: int):
    if btn == BTN_RECORD:
        if st["recording"]:
            threading.Thread(target=stop_recording, args=(True,), daemon=True).start()
        else:
            threading.Thread(target=start_recording, daemon=True).start()
    elif btn == BTN_SCREEN:
        set_screen(not st["screen_on"])
    elif btn == BTN_SHUTDOWN:
        threading.Thread(target=_shutdown_sequence, daemon=True).start()
    elif btn == BTN_PLAYBACK:
        if st["pb_active"]:
            threading.Thread(target=stop_playback, daemon=True).start()
        else:
            threading.Thread(target=start_playback, daemon=True).start()
    elif btn == BTN_STOPLAY:
        if st["pb_active"]:
            _pb_cmds.put(("pause", 0))
    elif btn in (BTN_BACK, BTN_FORWARD):
        if st["pb_active"]:
            direction = 5.0 if btn == BTN_FORWARD else -5.0
            _pb_cmds.put(("seek", direction))

def _shutdown_sequence():
    msg_screen("savin..", "wait", bg=(50, 0, 0), fg=(255, 200, 200))
    if st["recording"]:
        stop_recording(save=True)
        time.sleep(8)
    if st["pb_active"]:
        stop_playback()
    time.sleep(0.5)
    msg_screen("Byeee", bg=(0, 0, 0), fg=(80, 80, 80))
    time.sleep(1)
    GPIO.cleanup()
    os.system("sudo shutdown -h now")

def main():
    print("DashCam starting")
    setup_gpio()
    init_display()
    msg_screen("starting..", bg=(0, 0, 40))
    for target in (gps_thread, display_driver_thread, button_poll_thread,
                   idle_screen_thread, assembly_pipeline_thread):
        threading.Thread(target=target, daemon=True, name=target.__name__).start()
    print("Started without any problems")
    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        print("Shutting down")
        if st["recording"]:
            stop_recording(save=True)
        GPIO.cleanup()
        sys.exit(0)

if __name__ == "__main__":
    main()