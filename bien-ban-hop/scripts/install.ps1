# Cài đặt Agent biên bản họp: Python (qua uv), thư viện, ffmpeg đóng gói, mô hình Whisper và mô hình tách giọng.
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Skill = Split-Path -Parent $PSScriptRoot
$R = Join-Path $env:LOCALAPPDATA "BienBanHop"
New-Item -ItemType Directory -Force -Path "$R\models" | Out-Null

function Step($t) { Write-Host ""; Write-Host ">> $t" -ForegroundColor Cyan }

Step "1/5 Kiểm tra uv (trình quản lý Python)"
$uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
if (-not $uv) {
  Write-Host "Chưa có uv → đang cài từ astral.sh ..."
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
  $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
  $uv = (Get-Command uv -ErrorAction SilentlyContinue).Source
  if (-not $uv) { throw "Không cài được uv. Hãy kiểm tra Internet rồi chạy lại." }
}
Write-Host "uv: $uv"

Step "2/5 Tạo môi trường Python 3.12"
if (-not (Test-Path "$R\venv\Scripts\python.exe")) { & $uv venv --python 3.12 "$R\venv" }
$Py = "$R\venv\Scripts\python.exe"

Step "3/5 Cài thư viện (Whisper, ffmpeg, Excel, PDF...)"
& $uv pip install --python $Py -r "$Skill\requirements.txt"

Step "4/5 Tải mô hình tách giọng (~40 MB)"
$spk = "$R\models\speaker-embedding.onnx"
if (-not (Test-Path $spk)) {
  Invoke-WebRequest -UseBasicParsing -OutFile $spk "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"
}

Step "5/5 Tải mô hình phiên âm Whisper (~1,6 GB, chỉ tải lần đầu)"
$model = (Get-Content "$Skill\config.json" -Raw -Encoding UTF8 | ConvertFrom-Json).phien_am.mo_hinh_whisper
& $Py -c "from faster_whisper import download_model; print(download_model('$model', cache_dir=r'$R\models\whisper'))"

& $Py "$Skill\scripts\run.py" --help | Out-Null
Write-Host ""
Write-Host "CÀI ĐẶT XONG. Mở Claude Code trong thư mục dự án và nói: 'Lập biên bản cuộc họp từ file ...'" -ForegroundColor Green
