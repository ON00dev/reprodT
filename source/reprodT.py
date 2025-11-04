import sys, os, subprocess, threading, time, tempfile, atexit, signal, math, json, shutil, wave, struct
import numpy as np
from PIL import Image
import colorama
from colorama import Fore, Style
import time

# Inicializa Colorama para garantir cores no Windows e outros ambientes
try:
    colorama.just_fix_windows_console()
    # convert=True força conversão dos códigos ANSI para consoles que não suportam VT
    # strip=False mantém os códigos quando o console já suporta VT (Windows Terminal, VSCode, etc.)
    colorama.init(autoreset=True, convert=True, strip=False)
except Exception:
    pass

# Preferência de backend: no Windows, usar winsound nativo (sem instalação)
if os.name == 'nt':
    try:
        import winsound
        AUDIO_BACKEND = 'winsound'
    except ImportError:
        AUDIO_BACKEND = None
else:
    AUDIO_BACKEND = None

# Se não houver backend ainda, tentar third-party em ordem de robustez
if AUDIO_BACKEND is None:
    try:
        import pygame
        AUDIO_BACKEND = 'pygame'
    except ImportError:
        try:
            import pyaudio
            AUDIO_BACKEND = 'pyaudio'
        except ImportError:
            try:
                import sounddevice as sd
                import soundfile as sf
                AUDIO_BACKEND = 'sounddevice'
            except ImportError:
                AUDIO_BACKEND = None

SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

def load_settings():
    defaults = {"cols": 100, "fps_limit": 60, "max_rows": 0, "audio_enabled": True, "preset_auto": False}
    if os.path.isfile(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                # merge com defaults para garantir chaves novas
                for k in defaults:
                    if k not in data:
                        data[k] = defaults[k]
                return data
        except Exception:
            pass
    return defaults

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        try:
            print(Fore.YELLOW + "[AVISO] Não foi possível salvar configurações: " + str(e) + Style.RESET_ALL)
        except Exception:
            print(f"[AVISO] Não foi possível salvar configurações: {e}")

def _find_ffmpeg():
    # Override via variável de ambiente
    env = os.environ.get("TERMPLAYER_FFMPEG")
    if env and os.path.isfile(env):
        return env

    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)

    # Priorizar binários locais específicos por OS
    local_candidates = []
    if os.name == "nt":
        local_candidates += [
            os.path.join(script_dir, "ffmpeg-win", "ffmpeg.exe"),
            os.path.join(script_dir, "ffmpeg-win", "bin", "ffmpeg.exe"),
            os.path.join(script_dir, "ffmpeg-win", "ffmpeg-8.0-essentials_build", "bin", "ffmpeg.exe"),
            os.path.join(script_dir, "ffmpeg-8.0", "bin", "ffmpeg.exe"),
            os.path.join(script_dir, "bin", "ffmpeg.exe"),
            os.path.join(script_dir, "ffmpeg.exe"),
            # Também considerar diretórios na raiz do projeto (pai de source)
            os.path.join(parent_dir, "ffmpeg-win", "ffmpeg.exe"),
            os.path.join(parent_dir, "ffmpeg-win", "bin", "ffmpeg.exe"),
            os.path.join(parent_dir, "ffmpeg-win", "ffmpeg-8.0-essentials_build", "bin", "ffmpeg.exe"),
            os.path.join(parent_dir, "ffmpeg-8.0", "bin", "ffmpeg.exe"),
            os.path.join(parent_dir, "bin", "ffmpeg.exe"),
            os.path.join(parent_dir, "ffmpeg.exe"),
        ]
    elif sys.platform == "darwin":
        local_candidates += [
            os.path.join(script_dir, "ffmpeg-mac", "ffmpeg"),
            os.path.join(script_dir, "ffmpeg-mac", "bin", "ffmpeg"),
            os.path.join(script_dir, "bin", "ffmpeg"),
            os.path.join(script_dir, "ffmpeg"),
            os.path.join(parent_dir, "ffmpeg-mac", "ffmpeg"),
            os.path.join(parent_dir, "ffmpeg-mac", "bin", "ffmpeg"),
            os.path.join(parent_dir, "bin", "ffmpeg"),
            os.path.join(parent_dir, "ffmpeg"),
        ]
    else:
        # Linux e outros Unix
        local_candidates += [
            os.path.join(script_dir, "ffmpeg-linux", "ffmpeg"),
            os.path.join(script_dir, "ffmpeg-linux", "bin", "ffmpeg"),
            os.path.join(script_dir, "ffmpeg-linux", "ffmpeg-master-latest-linux64-lgpl", "ffmpeg"),
            os.path.join(script_dir, "bin", "ffmpeg"),
            os.path.join(script_dir, "ffmpeg"),
            os.path.join(parent_dir, "ffmpeg-linux", "ffmpeg"),
            os.path.join(parent_dir, "ffmpeg-linux", "bin", "ffmpeg"),
            os.path.join(parent_dir, "ffmpeg-linux", "ffmpeg-master-latest-linux64-lgpl", "ffmpeg"),
            os.path.join(parent_dir, "bin", "ffmpeg"),
            os.path.join(parent_dir, "ffmpeg"),
        ]

    # Verificar candidatos locais primeiro
    for c in local_candidates:
        if os.path.isfile(c):
            return c

    # PATH como fallback
    p = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if p:
        return p

    # Outros caminhos genéricos que possam existir no projeto
    generic = [
        os.path.join(script_dir, "ffmpeg-8.0", "bin", "ffmpeg"),
        os.path.join(script_dir, "ffmpeg-8.0", "bin", "ffmpeg.exe"),
        os.path.join(script_dir, "ffmpeg-8.0", "ffmpeg"),
        os.path.join(script_dir, "ffmpeg-8.0", "ffmpeg.exe"),
        os.path.join(script_dir, "ffmpeg", "bin", "ffmpeg"),
        os.path.join(script_dir, "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(script_dir, "ffmpeg", "ffmpeg"),
        os.path.join(script_dir, "ffmpeg", "ffmpeg.exe"),
        os.path.join(parent_dir, "ffmpeg-8.0", "bin", "ffmpeg"),
        os.path.join(parent_dir, "ffmpeg-8.0", "bin", "ffmpeg.exe"),
        os.path.join(parent_dir, "ffmpeg-8.0", "ffmpeg"),
        os.path.join(parent_dir, "ffmpeg-8.0", "ffmpeg.exe"),
        os.path.join(parent_dir, "ffmpeg", "bin", "ffmpeg"),
        os.path.join(parent_dir, "ffmpeg", "bin", "ffmpeg.exe"),
        os.path.join(parent_dir, "ffmpeg", "ffmpeg"),
        os.path.join(parent_dir, "ffmpeg", "ffmpeg.exe"),
    ]
    for c in generic:
        if os.path.isfile(c):
            return c
    return None

def _find_ffprobe():
    env = os.environ.get("TERMPLAYER_FFPROBE")
    if env and os.path.isfile(env):
        return env

    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(script_dir)

    # Priorizar binários locais específicos por OS
    local_candidates = []
    if os.name == "nt":
        local_candidates += [
            os.path.join(script_dir, "ffmpeg-win", "ffprobe.exe"),
            os.path.join(script_dir, "ffmpeg-win", "bin", "ffprobe.exe"),
            os.path.join(script_dir, "ffmpeg-win", "ffmpeg-8.0-essentials_build", "bin", "ffprobe.exe"),
            os.path.join(script_dir, "ffmpeg-8.0", "bin", "ffprobe.exe"),
            os.path.join(script_dir, "bin", "ffprobe.exe"),
            os.path.join(script_dir, "ffprobe.exe"),
            os.path.join(parent_dir, "ffmpeg-win", "ffprobe.exe"),
            os.path.join(parent_dir, "ffmpeg-win", "bin", "ffprobe.exe"),
            os.path.join(parent_dir, "ffmpeg-win", "ffmpeg-8.0-essentials_build", "bin", "ffprobe.exe"),
            os.path.join(parent_dir, "ffmpeg-8.0", "bin", "ffprobe.exe"),
            os.path.join(parent_dir, "bin", "ffprobe.exe"),
            os.path.join(parent_dir, "ffprobe.exe"),
        ]
    elif sys.platform == "darwin":
        local_candidates += [
            os.path.join(script_dir, "ffmpeg-mac", "ffprobe"),
            os.path.join(script_dir, "ffmpeg-mac", "bin", "ffprobe"),
            os.path.join(script_dir, "bin", "ffprobe"),
            os.path.join(script_dir, "ffprobe"),
            os.path.join(parent_dir, "ffmpeg-mac", "ffprobe"),
            os.path.join(parent_dir, "ffmpeg-mac", "bin", "ffprobe"),
            os.path.join(parent_dir, "bin", "ffprobe"),
            os.path.join(parent_dir, "ffprobe"),
        ]
    else:
        # Linux e outros Unix
        local_candidates += [
            os.path.join(script_dir, "ffmpeg-linux", "ffprobe"),
            os.path.join(script_dir, "ffmpeg-linux", "bin", "ffprobe"),
            os.path.join(script_dir, "ffmpeg-linux", "ffmpeg-master-latest-linux64-lgpl", "ffprobe"),
            os.path.join(script_dir, "bin", "ffprobe"),
            os.path.join(script_dir, "ffprobe"),
            os.path.join(parent_dir, "ffmpeg-linux", "ffprobe"),
            os.path.join(parent_dir, "ffmpeg-linux", "bin", "ffprobe"),
            os.path.join(parent_dir, "ffmpeg-linux", "ffmpeg-master-latest-linux64-lgpl", "ffprobe"),
            os.path.join(parent_dir, "bin", "ffprobe"),
            os.path.join(parent_dir, "ffprobe"),
        ]

    for c in local_candidates:
        if os.path.isfile(c):
            return c

    # PATH como fallback
    p = shutil.which("ffprobe") or shutil.which("ffprobe.exe")
    if p:
        return p

    # Outros caminhos genéricos no projeto
    generic = [
        os.path.join(script_dir, "ffmpeg-8.0", "bin", "ffprobe"),
        os.path.join(script_dir, "ffmpeg-8.0", "bin", "ffprobe.exe"),
        os.path.join(script_dir, "ffmpeg-8.0", "ffprobe"),
        os.path.join(script_dir, "ffmpeg-8.0", "ffprobe.exe"),
        os.path.join(script_dir, "ffmpeg", "bin", "ffprobe"),
        os.path.join(script_dir, "ffmpeg", "bin", "ffprobe.exe"),
        os.path.join(script_dir, "ffmpeg", "ffprobe"),
        os.path.join(script_dir, "ffmpeg", "ffprobe.exe"),
        os.path.join(parent_dir, "ffmpeg-8.0", "bin", "ffprobe"),
        os.path.join(parent_dir, "ffmpeg-8.0", "bin", "ffprobe.exe"),
        os.path.join(parent_dir, "ffmpeg-8.0", "ffprobe"),
        os.path.join(parent_dir, "ffmpeg-8.0", "ffprobe.exe"),
        os.path.join(parent_dir, "ffmpeg", "bin", "ffprobe"),
        os.path.join(parent_dir, "ffmpeg", "bin", "ffprobe.exe"),
        os.path.join(parent_dir, "ffmpeg", "ffprobe"),
        os.path.join(parent_dir, "ffmpeg", "ffprobe.exe"),
    ]
    for c in generic:
        if os.path.isfile(c):
            return c
    return None

def _enable_windows_ansi():
    # Usa Colorama para garantir suporte a ANSI no Windows
    try:
        colorama.just_fix_windows_console()
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def _truecolor_supported():
    if os.name == "nt":
        return True
    c = os.environ.get("COLORTERM", "").lower()
    t = os.environ.get("TERM", "").lower()
    if "truecolor" in c or "24bit" in c:
        return True
    if "-truecolor" in t or "xterm-truecolor" in t:
        return True
    return False

def _rgb_to_ansi256(r,g,b):
    if r==g==b:
        if r<8: return 16
        if r>248: return 231
        return 232 + int((r-8)/247*24+0.5)
    def to_6(x):
        return int((x/255)*5+0.5)
    rr,gg,bb = to_6(r),to_6(g),to_6(b)
    return 16 + 36*rr + 6*gg + bb

def _ansi_fg_true(r,g,b):
    return f"\x1b[38;2;{r};{g};{b}m"

def _ansi_bg_true(r,g,b):
    return f"\x1b[48;2;{r};{g};{b}m"

def _ansi_fg_256(c):
    return f"\x1b[38;5;{c}m"

def _ansi_bg_256(c):
    return f"\x1b[48;5;{c}m"

def _clear_screen():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()

def _hide_cursor():
    sys.stdout.write("\x1b[?25l")
    sys.stdout.flush()

def _show_cursor():
    sys.stdout.write("\x1b[?25h\x1b[0m")
    sys.stdout.flush()

def _ffprobe_info(path):
    try:
        fp = _find_ffprobe()
        if not fp:
            return None
        out = subprocess.check_output([
            fp,"-v","error","-select_streams","v:0","-show_entries","stream=width,height,avg_frame_rate","-of","json",path
        ], stderr=subprocess.DEVNULL)
        j = json.loads(out.decode("utf-8",errors="ignore"))
        streams = j.get("streams",[])
        if not streams:
            return None
        s = streams[0]
        w = int(s.get("width",0))
        h = int(s.get("height",0))
        fr = s.get("avg_frame_rate","0/1")
        try:
            num,den = fr.split("/")
            fps = float(num)/float(den) if float(den)!=0 else 0.0
        except Exception:
            fps = 0.0
        return {"width":w,"height":h,"fps":fps}
    except Exception:
        return None

def _probe_scaled_dimensions(path, cols):
    try:
        fff = _find_ffmpeg()
        if not fff:
            return None
        cmd = [
            fff,"-v","info","-i",path,
            "-vf",f"scale={int(cols)}:-2",
            "-f","rawvideo","-pix_fmt","rgb24","-frames:v","1","-y","-"
        ]
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        msg = r.stderr.decode("utf-8", errors="ignore")
        import re
        m = re.search(r"Video:\s*rawvideo.*?,\s*(\d+)x(\d+)", msg)
        if m:
            w = int(m.group(1)); h = int(m.group(2))
            if h % 2 == 1:
                h += 1
            return w, h
        return None
    except Exception:
        return None

def _normalize_path(p):
    if not p:
        return p
    q = p
    if os.name == "nt":
        if len(q) > 2 and q[0] == "/" and q[2] == ":":
            q = q[1:]
    return os.path.abspath(q)

def _compute_scaled_wh(src_w, src_h, cols):
    if src_w<=0 or src_h<=0:
        return cols, max(2, 2*((cols*9)//16//2))
    h = int(round(src_h * (cols/src_w)))
    if h<2: h=2
    if h%2==1: h+=1
    return cols, h

def _cap_dimensions_by_rows(w, h, max_rows):
    """Limita a altura (em linhas de terminal) mantendo proporção.
    h é altura em pixels; cada linha representa 2 pixels.
    """
    try:
        if max_rows and max_rows > 0:
            max_h = int(max_rows) * 2
            if h > max_h:
                scale = max_h / float(h)
                new_w = max(2, int(round(w * scale)))
                new_h = max_h
                # garantir altura par
                if new_h % 2 == 1:
                    new_h += 1
                return new_w, new_h
    except Exception:
        pass
    return w, h

def _build_ffmpeg_video_proc(path, w, h, fps_limit):
    fff = _find_ffmpeg()
    if not fff:
        return None
    args = [
        fff,"-loglevel","error","-i",path,
        "-f","rawvideo","-pix_fmt","rgb24",
        "-vf",f"scale={w}:{h}",
    ]
    if fps_limit>0:
        args += ["-r",str(int(fps_limit))]
    args += ["-"]
    return subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

def _convert_audio_to_wav(path):
    tmpdir = tempfile.mkdtemp(prefix="reprodT_")
    wav = os.path.join(tmpdir, "audio.wav")
    fff = _find_ffmpeg()
    if not fff:
        raise RuntimeError("ffmpeg não encontrado")
    cmd = [fff,"-loglevel","error","-y","-i",path,"-vn","-ac","2","-ar","44100","-f","wav",wav]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return wav, tmpdir

class KeyInput:
    def __init__(self):
        self.pause = False
        self.speed = 1.0
        self.quit = False
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._use_keyboard = False
        try:
            import keyboard as kb
            self._kb = kb
            self._use_keyboard = True
        except Exception:
            self._kb = None
        self._thread.start()

    def _run(self):
        if self._use_keyboard:
            def on_key(e):
                name = e.name
                if name == "space":
                    self.pause = not self.pause
                elif name in ("up","uparrow"):
                    self.speed = min(2.0, round(self.speed+0.1,2))
                elif name in ("down","downarrow"):
                    self.speed = max(0.5, round(self.speed-0.1,2))
                elif name == "q":
                    self.quit = True
            self._kb.on_press(on_key, suppress=False)
            while self._running and not self.quit:
                time.sleep(0.05)
        else:
            if os.name == "nt":
                import msvcrt
                while self._running and not self.quit:
                    if msvcrt.kbhit():
                        ch = msvcrt.getch()
                        if ch in (b" ",):
                            self.pause = not self.pause
                        elif ch == b"q":
                            self.quit = True
                        elif ch == b"H":
                            self.speed = min(2.0, round(self.speed+0.1,2))
                        elif ch == b"P":
                            self.speed = max(0.5, round(self.speed-0.1,2))
                    time.sleep(0.02)
            else:
                import termios, tty, sys, select
                fd = sys.stdin.fileno()
                old = termios.tcgetattr(fd)
                try:
                    tty.setcbreak(fd)
                    while self._running and not self.quit:
                        r,_,_ = select.select([sys.stdin], [], [], 0.05)
                        if r:
                            ch = sys.stdin.read(1)
                            if ch == " ":
                                self.pause = not self.pause
                            elif ch == "q":
                                self.quit = True
                            elif ch == "\x1b":
                                seq = sys.stdin.read(2)
                                if seq == "[A":
                                    self.speed = min(2.0, round(self.speed+0.1,2))
                                elif seq == "[B":
                                    self.speed = max(0.5, round(self.speed-0.1,2))
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old)

    def stop(self):
        self._running = False

class AudioPlayer:
    """Reprodutor de áudio com fallback para PyAudio ou sounddevice."""
    def __init__(self, wav_path):
        self.wav_path = wav_path
        self.paused = False
        # Alias de compatibilidade com código legado
        self._paused = self.paused
        self.stop_requested = False
        self.thread = None
        self.lock = threading.Lock()
        self.backend = AUDIO_BACKEND
        # PyAudio
        self.wf = None
        self.pa = None
        self.stream = None
        # SoundDevice
        self.sd_event = None
        self.sd_data = None
        # Pygame não usa thread própria

    # ---------- PyAudio ----------
    def _playback_thread_pyaudio(self):
        import pyaudio as pa
        self.wf = wave.open(self.wav_path, 'rb')
        self.pa = pa.PyAudio()
        self.stream = self.pa.open(
            format=self.pa.get_format_from_width(self.wf.getsampwidth()),
            channels=self.wf.getnchannels(),
            rate=self.wf.getframerate(),
            output=True
        )
        chunk = 1024
        while True:
            with self.lock:
                if self.stop_requested:
                    break
                if self.paused:
                    time.sleep(0.05)
                    continue
            data = self.wf.readframes(chunk)
            if not data:
                break
            self.stream.write(data)
        self.stream.stop_stream()
        self.stream.close()
        self.pa.terminate()
        self.wf.close()

    # ---------- SoundDevice ----------
    def _playback_thread_sounddevice(self):
        import sounddevice as sd, soundfile as sf
        data, sr = sf.read(self.wav_path, dtype='float32')
        self.sd_data = data
        self.sd_event = threading.Event()
        current_frame = 0
        chunk_samples = 1024
        def callback(outdata, frames, time_info, status):
            nonlocal current_frame
            if status:
                try:
                    print(Fore.CYAN + f'[sounddevice] {status}' + Style.RESET_ALL)
                except Exception:
                    print(f'[sounddevice] {status}')
            with self.lock:
                if self.stop_requested:
                    raise sd.CallbackStop
                if self.paused:
                    outdata[:] = 0
                    return
            end = current_frame + frames
            if end > len(data):
                outdata[:len(data)-current_frame] = data[current_frame:].reshape(-1,1)
                outdata[len(data)-current_frame:] = 0
                raise sd.CallbackStop
            else:
                outdata[:] = data[current_frame:end].reshape(-1,1)
            current_frame = end
        with sd.OutputStream(samplerate=sr, channels=1, callback=callback, finished_callback=self.sd_event.set):
            self.sd_event.wait()

    # ---------- Interface comum ----------
    def start(self):
        if self.thread is not None:
            return
        if self.backend == 'pygame':
            try:
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(self.wav_path)
                pygame.mixer.music.play()
                with self.lock:
                    self.paused = False
                    self._paused = self.paused
            except Exception as e:
                try:
                    print(Fore.RED + f"[AudioPlayer] Falha ao iniciar pygame: {e}" + Style.RESET_ALL)
                except Exception:
                    print(f"[AudioPlayer] Falha ao iniciar pygame: {e}")
            return
        if self.backend == 'pyaudio':
            target = self._playback_thread_pyaudio
        elif self.backend == 'sounddevice':
            target = self._playback_thread_sounddevice
        elif self.backend == 'winsound':
            try:
                import winsound
                winsound.PlaySound(self.wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                with self.lock:
                    self.paused = False
                    self._paused = self.paused
            except Exception as e:
                try:
                    print(Fore.RED + f"[AudioPlayer] Falha ao iniciar winsound: {e}" + Style.RESET_ALL)
                except Exception:
                    print(f"[AudioPlayer] Falha ao iniciar winsound: {e}")
            return
        else:
            try:
                print(Fore.YELLOW + '[AudioPlayer] Nenhum backend disponível (instale pygame, pyaudio ou sounddevice).' + Style.RESET_ALL)
            except Exception:
                print('[AudioPlayer] Nenhum backend disponível (instale pygame, pyaudio ou sounddevice).')
            return
        self.thread = threading.Thread(target=target, daemon=True)
        self.thread.start()

    def pause(self):
        with self.lock:
            if self.backend == 'pygame':
                try:
                    import pygame
                    if not self.paused:
                        pygame.mixer.music.pause()
                        self.paused = True
                        self._paused = True
                    else:
                        pygame.mixer.music.unpause()
                        self.paused = False
                        self._paused = False
                    return
                except Exception:
                    pass
            elif self.backend == 'winsound':
                try:
                    import winsound
                    if not self.paused:
                        winsound.PlaySound(None, winsound.SND_PURGE)
                        self.paused = True
                        self._paused = True
                    else:
                        winsound.PlaySound(self.wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                        self.paused = False
                        self._paused = False
                    return
                except Exception:
                    pass
            # Toggle para backends com thread (pyaudio/sounddevice)
            self.paused = not self.paused
            self._paused = self.paused

    # Compatibilidade com código que chama resume()
    def resume(self):
        with self.lock:
            if self.backend == 'pygame':
                try:
                    import pygame
                    pygame.mixer.music.unpause()
                except Exception:
                    pass
            elif self.backend == 'winsound':
                try:
                    import winsound
                    winsound.PlaySound(self.wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                except Exception:
                    pass
            self.paused = False
            self._paused = self.paused

    def stop(self):
        with self.lock:
            self.stop_requested = True
        if self.backend == 'pygame':
            try:
                import pygame
                pygame.mixer.music.stop()
                pygame.mixer.quit()
            except Exception:
                pass
            return
        if self.backend == 'winsound':
            try:
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
            return
        if self.backend == 'sounddevice' and self.sd_event:
            self.sd_event.set()
        if self.thread:
            self.thread.join()
            self.thread = None

def _render_frame(rgb, width, height, truecolor, prev_lines_cache, left_pad=0, top_pad=0):
    rows = height//2
    lines = []
    for y in range(rows):
        y0 = y*2
        y1 = y*2+1
        row_top = rgb[y0]
        row_bot = rgb[y1] if y1<height else np.zeros_like(row_top)
        sb = []
        last_fg = None
        last_bg = None
        for x in range(width):
            rt = row_top[x]
            rb = row_bot[x]
            if truecolor:
                fg = (int(rt[0]), int(rt[1]), int(rt[2]))
                bg = (int(rb[0]), int(rb[1]), int(rb[2]))
                if fg != last_fg:
                    sb.append(_ansi_fg_true(*fg))
                    last_fg = fg
                if bg != last_bg:
                    sb.append(_ansi_bg_true(*bg))
                    last_bg = bg
            else:
                fgc = _rgb_to_ansi256(int(rt[0]),int(rt[1]),int(rt[2]))
                bgc = _rgb_to_ansi256(int(rb[0]),int(rb[1]),int(rb[2]))
                if fgc != last_fg:
                    sb.append(_ansi_fg_256(fgc))
                    last_fg = fgc
                if bgc != last_bg:
                    sb.append(_ansi_bg_256(bgc))
                    last_bg = bgc
            sb.append("\u2584")
        line = "".join(sb)
        lines.append(line)
    out = []
    out.append("\x1b[H")
    if top_pad and top_pad > 0:
        out.append(f"\x1b[{int(top_pad)}B")
    for i, line in enumerate(lines):
        if prev_lines_cache is not None and i < len(prev_lines_cache) and prev_lines_cache[i] == line:
            out.append("\x1b[E")
        else:
            if left_pad and left_pad > 0:
                # Move para a coluna desejada (1-indexed)
                out.append(f"\x1b[{int(left_pad)+1}G")
            out.append(line)
            out.append("\n")
    out.append("\x1b[0m")
    return "".join(out), lines

def _read_exact(proc, size):
    buf = bytearray()
    while len(buf) < size:
        chunk = proc.stdout.read(size - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)

def select_file_for_upload():
    try:
        p = input("Digite o caminho do arquivo (mp4/png/jpg/webp): ").strip()
        return p if p else None
    except Exception:
        return None

def upload_file(file_path):
    """Faz upload do arquivo para a pasta correta"""
    if not file_path or not os.path.exists(file_path):
        return None
    
    # Criar diretórios se não existirem
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.join(script_dir, "uploads")
    img_dir = os.path.join(base_dir, "img")
    mp4_dir = os.path.join(base_dir, "video")
    
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(mp4_dir, exist_ok=True)
    
    # Determinar tipo de arquivo
    file_ext = os.path.splitext(file_path)[1].lower()
    filename = os.path.basename(file_path)
    
    if file_ext == '.mp4':
        dest_path = os.path.join(mp4_dir, filename)
    elif file_ext in ['.png', '.jpg', '.jpeg', '.webp']:
        dest_path = os.path.join(img_dir, filename)
    else:
        print(f"Tipo de arquivo não suportado: {file_ext}")
        return None
    
    # Copiar arquivo
    try:
        shutil.copy2(file_path, dest_path)
        print(f"Upload concluído: {dest_path}")
        return dest_path
    except Exception as e:
        print(f"Erro no upload: {e}")
        return None

def display_image(image_path, cols, max_rows):
    """Exibe imagem estática no terminal"""
    try:
        img = Image.open(image_path)

        # Redimensionar mantendo proporção
        width = max(2, int(cols))
        height = max(1, int((img.height * width) / img.width / 2))
        if max_rows and max_rows > 0:
            height = min(height, int(max_rows))
        if (height*2) % 2 != 0:
            height += 1
        img = img.resize((width, height * 2), Image.Resampling.LANCZOS)
        img = img.convert('RGB')

        # Detectar suporte a cores
        truecolor = _truecolor_supported()
        
        # Calcular padding para centralização e usar renderer unificado
        try:
            ts = shutil.get_terminal_size(fallback=(80, 24))
            term_cols, term_rows = ts.columns, ts.lines
        except Exception:
            term_cols, term_rows = 80, 24
        left_pad = max(0, (term_cols - width)//2)
        top_pad = max(0, (term_rows - height)//2)

        _clear_screen()
        _hide_cursor()

        arr = np.array(img, dtype=np.uint8)
        out, _ = _render_frame(arr, width, height*2, truecolor, prev_lines_cache=None, left_pad=left_pad, top_pad=top_pad)
        sys.stdout.write(out)
        sys.stdout.flush()
        _show_cursor()
        print(f"\nImagem: {os.path.basename(image_path)}")
        print("Pressione Enter para continuar...")
        input()
        
    except Exception as e:
        print(f"Erro ao exibir imagem: {e}")

def _list_files(dir_path, exts):
    try:
        files = []
        for name in sorted(os.listdir(dir_path)):
            p = os.path.join(dir_path, name)
            if os.path.isfile(p) and os.path.splitext(name)[1].lower() in exts:
                files.append(p)
        return files
    except Exception:
        return []

def choose_from_directory(dir_path, exts):
    files = _list_files(dir_path, exts)
    if not files:
        print("Nenhum arquivo disponível.")
        return None
    print("\nArquivos disponíveis:")
    for i, f in enumerate(files, start=1):
        print(f"  {i}. {os.path.basename(f)}")
    while True:
        sel = input("Escolha o número do arquivo (ou Enter para cancelar): ").strip()
        if sel == "":
            return None
        if sel.isdigit():
            idx = int(sel)
            if 1 <= idx <= len(files):
                return files[idx-1]
        print("Seleção inválida.")

def settings_menu(settings):
    while True:
        print("\nConfigurações atuais:")
        print(f"  Colunas: {settings['cols']}")
        print(f"  Altura máxima (linhas): {settings['max_rows']}")
        print(f"  FPS limite: {settings['fps_limit']}")
        print(f"  Áudio: {'Ativado' if settings['audio_enabled'] else 'Desativado'}")
        print(f"  Preset automático: {'Ativado' if settings.get('preset_auto') else 'Desativado'}")
        print("\n1. Alterar colunas\n2. Alterar altura máxima (linhas)\n3. Alterar FPS limite\n4. Alternar áudio\n5. Alternar preset automático\n6. Voltar")
        ch = input(Fore.BLUE+"Escolha: ").strip()
        if ch == '1':
            v = input(Fore.BLUE+"Novo valor de colunas (>=20): ").strip()
            try:
                iv = int(v)
                settings['cols'] = max(20, iv)
            except Exception:
                print("Valor inválido.")

        elif ch == '2':
            v = input(Fore.BLUE+"Nova altura máxima em linhas (0 = ilimitado): ").strip()
            try:
                iv = int(v)
                settings['max_rows'] = max(0, iv)
            except Exception:
                print("Valor inválido.")

        elif ch == '3':
            v = input(Fore.BLUE+"Novo FPS limite (>=1): ").strip()
            try:
                iv = int(v)
                settings['fps_limit'] = max(1, iv)
            except Exception:
                print("Valor inválido.")
                
        elif ch == '4':
            settings['audio_enabled'] = not settings['audio_enabled']
        
        elif ch == '5':
            settings['preset_auto'] = not settings.get('preset_auto', False)
        
        elif ch == '6':
            save_settings(settings)
            return
        else:
            print("Opção inválida.")

def terminal_ui_loop():
    settings = load_settings()
    script_dir = os.path.dirname(os.path.abspath(__file__))
    uploads_dir = os.path.join(script_dir, 'uploads')
    img_dir = os.path.join(uploads_dir, 'img')
    video_dir = os.path.join(uploads_dir, 'video')
    os.makedirs(img_dir, exist_ok=True)
    os.makedirs(video_dir, exist_ok=True)

    while True:
        _clear_screen()
        print("\n" + "="*50)
        print("REPROD-T")
        print("="*50)
        print("1. Selecionar caminho e fazer upload")
        print("2. Reproduzir vídeo de uploads/video")
        print("3. Exibir imagem de uploads/img")
        print("4. Configurações")
        print("5. Sobre")
        print("6. Sair")
        choice = input(Fore.BLUE+"\nEscolha uma opção (1-6): ").strip()

        if choice == '1':
            file_path = select_file_for_upload()
            if not file_path:
                print("Nenhum arquivo informado.")
                continue
            uploaded_path = upload_file(file_path)
            if not uploaded_path:
                print("Falha no upload.")
                continue
            file_ext = os.path.splitext(uploaded_path)[1].lower()
            ephemeral = True
            try:
                if file_ext == '.mp4':
                    print(f"\nReproduzindo vídeo: {os.path.basename(uploaded_path)}")
                    # Aplicar preset automático se habilitado
                    cols = settings['cols']
                    fps = settings['fps_limit']
                    rows = settings['max_rows']
                    if settings.get('preset_auto'):
                        info = _ffprobe_info(uploaded_path)
                        if info:
                            if info['height'] > info['width']:
                                cols, rows, fps = 80, 0, 30
                            else:
                                cols, rows, fps = 120, 0, 30
                    play_video_file(uploaded_path, cols, fps, settings['audio_enabled'], rows)
                elif file_ext in ['.png', '.jpg', '.jpeg', '.webp']:
                    cols = settings['cols']
                    rows = settings['max_rows']
                    if settings.get('preset_auto'):
                        try:
                            im = Image.open(uploaded_path)
                            w, h = im.size
                            im.close()
                            if h > w:
                                cols, rows = 80, 0
                            else:
                                cols, rows = 120, 0
                        except Exception:
                            pass
                    display_image(uploaded_path, cols, rows)
                else:
                    print("Tipo de arquivo não suportado.")
            finally:
                # Descartar upload efêmero
                if ephemeral and os.path.isfile(uploaded_path):
                    try:
                        os.remove(uploaded_path)
                        print("Arquivo descartado após reprodução.")
                    except Exception:
                        pass

        elif choice == '2':
            sel = choose_from_directory(video_dir, {'.mp4'})
            if sel:
                cols = settings['cols']
                fps = settings['fps_limit']
                rows = settings['max_rows']
                if settings.get('preset_auto'):
                    info = _ffprobe_info(sel)
                    if info:
                        if info['height'] > info['width']:
                            cols, rows, fps = 80, 0, 30
                        else:
                            cols, rows, fps = 120, 0, 30
                play_video_file(sel, cols, fps, settings['audio_enabled'], rows)

        elif choice == '3':
            sel = choose_from_directory(img_dir, {'.png', '.jpg', '.jpeg', '.webp'})
            if sel:
                cols = settings['cols']
                rows = settings['max_rows']
                if settings.get('preset_auto'):
                    try:
                        im = Image.open(sel)
                        w, h = im.size
                        im.close()
                        if h > w:
                            cols, rows = 80, 0
                        else:
                            cols, rows = 120, 0
                    except Exception:
                        pass
                display_image(sel, cols, rows)

        elif choice == '4':
            settings_menu(settings)

        elif choice == '5':
            print(Fore.GREEN+"\n" + ABOUT_TEXT + "\n")
            time.sleep(10)

        elif choice == '6':
            print(Fore.YELLOW+"Saindo...")
            break
        else:
            print("Opção inválida.")

def play_video_file(path, cols, fps_limit, audio_enabled, max_rows):
    """Reproduz um arquivo de vídeo com fallback robusto de resolução."""
    npath = _normalize_path(path)
    if not _find_ffmpeg():
        sys.stderr.write(Fore.RED+"ffmpeg não encontrado para reproduzir vídeo. Instale ou coloque o binário ao lado do script.\n")
        return

    info = _ffprobe_info(npath)
    dims = _probe_scaled_dimensions(npath, cols) if not info else None
    if dims:
        w, h = dims
    elif info:
        w, h = _compute_scaled_wh(info.get("width", 0), info.get("height", 0), cols)
    else:
        # Fallback 16:9 via _compute_scaled_wh (que já lida com src inválido)
        w, h = _compute_scaled_wh(0, 0, cols)

    # Limitar altura por linhas de terminal
    w, h = _cap_dimensions_by_rows(w, h, max_rows)

    truecolor = _truecolor_supported()

    # Calcular padding para centralização
    try:
        ts = shutil.get_terminal_size(fallback=(80, 24))
        term_cols, term_rows = ts.columns, ts.lines
    except Exception:
        term_cols, term_rows = 80, 24
    left_pad = max(0, (term_cols - w)//2)
    top_pad = max(0, (term_rows - (h//2))//2)

    signal.signal(signal.SIGINT, lambda s, f: (_show_cursor(), sys.exit(0)))
    atexit.register(_show_cursor)

    _clear_screen()
    _hide_cursor()

    ki = KeyInput()

    audio_tmp_dir = None
    audio = None
    if audio_enabled:
        try:
            wav, audio_tmp_dir = _convert_audio_to_wav(npath)
            audio = AudioPlayer(wav)
            audio.start()
        except Exception as e:
            print(f"[AVISO] Áudio desativado: {e}")
            audio = None

    prev_lines = None
    # Ajustar FPS alvo considerando FPS da fonte para evitar duplicação lenta
    src_fps = (info.get("fps", 0.0) if info else 0.0)
    try:
        sfps = int(round(src_fps))
    except Exception:
        sfps = 0
    if sfps > 0:
        fps_limit = min(max(1, int(fps_limit)), sfps)
    else:
        fps_limit = max(1, int(fps_limit))
    base_frame_time = 1.0 / fps_limit
    next_frame_time = time.perf_counter()

    proc = _build_ffmpeg_video_proc(npath, w, h, fps_limit)
    if proc is None:
        sys.stderr.write(Fore.RED+"Não foi possível iniciar decodificação de vídeo (ffmpeg).\n")
        ki.stop()
        if audio:
            audio.stop()
        _show_cursor()
        if audio_tmp_dir and os.path.isdir(audio_tmp_dir):
            try:
                shutil.rmtree(audio_tmp_dir)
            except Exception:
                pass
        return

    frame_bytes = w * h * 3
    frame_index = 0
    try:
        while True:
            if ki.quit:
                break
            if ki.pause:
                if audio:
                    audio.pause()
                time.sleep(0.02)
                # Resetar agendamento para evitar acúmulo de atraso
                next_frame_time = time.perf_counter()
                continue
            else:
                if audio and audio._paused:
                    audio.resume()

            target_dt = base_frame_time / ki.speed
            now = time.perf_counter()
            if now < next_frame_time:
                time.sleep(max(0, next_frame_time - now))
                now = time.perf_counter()
            else:
                behind = now - next_frame_time
                if behind > target_dt:
                    # Pular frames para alcançar o tempo alvo
                    skip_n = int(behind / target_dt)
                    if skip_n > 0:
                        skip_n = min(skip_n, 5)
                        for _ in range(skip_n):
                            raw_skip = _read_exact(proc, frame_bytes)
                            if raw_skip is None:
                                skip_n = 0
                                break
                        next_frame_time += target_dt * skip_n

            raw = _read_exact(proc, frame_bytes)
            if raw is None:
                break
            next_frame_time += target_dt
            arr = np.frombuffer(raw, dtype=np.uint8)
            arr = arr.reshape((h, w, 3))
            rgb = arr
            out, lines = _render_frame(rgb, w, h, truecolor, prev_lines, left_pad=left_pad, top_pad=top_pad)
            sys.stdout.write(out)
            sys.stdout.flush()
            prev_lines = lines
            frame_index += 1
    finally:
        try:
            proc.kill()
        except Exception:
            pass

    # Se nenhum quadro foi renderizado e não há áudio, informe falha mais clara
    if frame_index == 0 and audio is None:
        sys.stderr.write(Fore.RED+"Falha ao decodificar vídeo. Verifique se o arquivo é válido e se o FFmpeg suporta o codec.\n")

    ki.stop()
    if audio:
        audio.stop()
    _show_cursor()
    if audio_tmp_dir and os.path.isdir(audio_tmp_dir):
        try:
            shutil.rmtree(audio_tmp_dir)
        except Exception:
            pass

def main():
    _enable_windows_ansi()
    _clear_screen()
    if not _find_ffmpeg():
        sys.stderr.write(Fore.YELLOW+"ffmpeg não encontrado. Instale e/ou adicione ao PATH, ou coloque o binário em ./bin/ffmpeg(.exe) ao lado do script.\n")
        sys.stderr.write(Fore.YELLOW+"Abra o programa mesmo assim para imagens estáticas e configuração.\n")
    terminal_ui_loop()
    return

ABOUT_TEXT = (
    "Resumo: cada par de pixels verticais é mapeado para o caractere '▄',\n"
    "usando a cor inferior como fundo e a superior como frente.\n"
    "As cores são emitidas como ANSI truecolor (24-bit) quando suportado,\n"
    "do contrário aproximadas para a paleta ANSI 256. O vídeo é decodificado\n"
    "via ffmpeg em rawvideo (pipe), o áudio é convertido para WAV e tocado\n"
    "com simpleaudio. A renderização minimiza códigos de escape reutilizando\n"
    "cores consecutivas e cacheando linhas idênticas.\n"
)

if __name__ == "__main__":
    main()