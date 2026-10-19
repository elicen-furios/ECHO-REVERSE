import os
import uuid
import subprocess
from flask import Flask, request, send_file, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='.')
CORS(app)

UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/process', methods=['POST'])
def process_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file uploaded'}), 400
    
    file = request.files['audio']
    tool = request.form.get('tool', 'bass-booster')
    param1 = float(request.form.get('param1', 5))
    param2 = float(request.form.get('param2', 1.0))
    start_time = request.form.get('start', '0')
    end_time = request.form.get('end', '30')
    out_format = request.form.get('format', 'mp3').lower()

    uid = str(uuid.uuid4())[:8]
    ext = os.path.splitext(file.filename)[1] or '.mp3'
    in_path = os.path.join(UPLOAD_FOLDER, f"{uid}_in{ext}")
    file.save(in_path)

    if tool in ['spectrogram', 'waveform']:
        out_ext = '.png'
    elif tool == 'converter':
        out_ext = f'.{out_format}'
    else:
        out_ext = '.mp3'

    out_path = os.path.join(OUTPUT_FOLDER, f"Akhil_{uid}_{tool}{out_ext}")

    if tool == 'bpm-detector':
        cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration,bit_rate:stream=sample_rate,channels', '-of', 'default=noprint_wrappers=1', in_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return jsonify({'status': 'info', 'info': res.stdout})

    af = []
    cmd = ['ffmpeg', '-y', '-i', in_path]

    # --- 1. EFFECTS ---
    if tool == '3d-audio':
        af.append("apulsator=mode=sine:hz=0.25:width=1,aecho=0.8:0.88:60:0.4")
    elif tool == 'autopanner':
        hz = max(0.05, min(5.0, param1))
        af.append(f"apulsator=mode=sine:hz={hz}")
    elif tool == 'bass-booster':
        af.append(f"bass=g={param1}:f=110:w=0.6")
    elif tool == 'equalizer':
        af.append(f"bass=g={param1}:f=100,treble=g={param2}:f=3500")
    elif tool == 'noise-reducer':
        af.append("highpass=f=120,lowpass=f=10000,afftdn=nf=-25")
    elif tool == 'pitch-shifter':
        factor = 2 ** (param1 / 12.0)
        inv = 1.0 / factor
        af.append(f"asetrate=44100*{factor:.4f},aresample=44100,atempo={max(0.5, min(2.0, inv)):.4f}")
    elif tool == 'reverb':
        delay = int(max(20, min(1000, param1 * 12)))
        af.append(f"aecho=0.8:0.9:{delay}:0.5")
    elif tool == 'reverse':
        af.append("areverse")
    elif tool == 'stereo-panner':
        pan = max(-1.0, min(1.0, param1 / 10.0))
        af.append(f"stereotools=mpan={pan}")
    elif tool == 'tempo':
        spd = max(0.5, min(2.0, param1))
        af.append(f"atempo={spd}")
    elif tool == 'trimmer':
        cmd = ['ffmpeg', '-y', '-ss', str(start_time), '-to', str(end_time), '-i', in_path]
    elif tool == 'vocal-remover':
        af.append("stereotools=mode=lr>ll,pan=stereo|c0=c0-c1|c1=c0-c1")
    elif tool == 'volume':
        af.append(f"volume={param1}dB")

    # --- 2. OTHER TOOLS ---
    elif tool == 'downmixer':
        cmd.extend(['-ac', '1'])
    elif tool == 'spectrogram':
        cmd.extend(['-lavfi', 'showspectrumpic=s=1024x512:color=fiery', out_path])
    elif tool == 'waveform':
        cmd.extend(['-lavfi', 'showwavespic=s=1024x320:colors=#D53F8C', out_path])

    # --- 3. PRESETS ---
    elif tool == 'preset-8d-audio':
        af.append("apulsator=mode=sine:hz=0.125:amount=1,aecho=0.8:0.88:60:0.4,bass=g=3:f=100")
    elif tool == 'preset-slowed-reverb':
        af.append("asetrate=44100*0.85,aresample=44100,aecho=0.8:0.88:75:0.45")
    elif tool == 'preset-432hz':
        af.append("asetrate=44100*0.981818,aresample=44100,atempo=1.018518")
    elif tool == 'preset-very-light-bass':
        af.append("bass=g=3:f=100")
    elif tool == 'preset-light-bass':
        af.append("bass=g=6:f=100")
    elif tool == 'preset-moderate-bass':
        af.append("bass=g=10:f=100")
    elif tool == 'preset-heavy-bass':
        af.append("bass=g=15:f=110")
    elif tool == 'preset-extreme-bass':
        af.append("bass=g=22:f=115")
    elif tool == 'preset-vocal-reverb':
        af.append("aecho=0.8:0.85:40:0.35")
    elif tool == 'preset-bathroom-reverb':
        af.append("aecho=0.8:0.85:25|45:0.4|0.3")
    elif tool == 'preset-small-room-reverb':
        af.append("aecho=0.8:0.88:50:0.35")
    elif tool == 'preset-medium-room-reverb':
        af.append("aecho=0.8:0.88:90:0.45")
    elif tool == 'preset-large-room-reverb':
        af.append("aecho=0.8:0.9:150:0.5")
    elif tool == 'preset-church-hall-reverb':
        af.append("aecho=0.8:0.9:250|400:0.55|0.4")
    elif tool == 'preset-cathedral-reverb':
        af.append("aecho=0.8:0.92:450|800:0.65|0.5")

    if tool not in ['spectrogram', 'waveform']:
        if af:
            cmd.extend(['-af', ','.join(af)])
        cmd.append(out_path)

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        return jsonify({'error': proc.stderr[-300:]}), 500

    return send_file(out_path, as_attachment=True, download_name=f"Akhil_Studio_{tool}{out_ext}")

if __name__ == '__main__':
    print("\n====================================================")
    print("🚀 AKHIL AUDIO STUDIO RUNNING ON PORT 5000")
    print("👉 Open Browser: http://127.0.0.1:5000")
    print("====================================================\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
