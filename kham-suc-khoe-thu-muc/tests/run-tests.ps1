<#
  Kiểm thử skill kham-suc-khoe-thu-muc trên dữ liệu mẫu tự sinh (trong %TEMP%).
  Xác minh: kết quả quét đúng, phân loại nhóm trùng đúng, từ chối ghi vào thư mục quét,
  script không chứa lệnh ghi/xóa, và dữ liệu mẫu không đổi một byte sau khi chạy.
  Chạy: powershell -NoProfile -ExecutionPolicy Bypass -File run-tests.ps1 [-Keep]
#>
param([switch]$Keep)
$ErrorActionPreference = 'Stop'
$skill = Split-Path -Parent $PSScriptRoot
$scan = Join-Path $skill 'scripts\scan.ps1'
$build = Join-Path $skill 'scripts\build-report.ps1'
$work = Join-Path $env:TEMP ("khsk-test-" + [guid]::NewGuid().ToString('N').Substring(0,8))
$root = Join-Path $work 'sample'
$pass = 0; $fail = 0
function Check($name, $cond) { if ($cond) { $script:pass++; "  PASS  $name" } else { $script:fail++; "  FAIL  $name" } }

# ---------- 1. Dữ liệu mẫu ----------
$rng = New-Object Random 42
function Bytes([int]$n) { $b = New-Object byte[] $n; $rng.NextBytes($b); $b }
function Put($rel, [byte[]]$data, $date = '2025-06-15') {
  $p = Join-Path $root $rel; $d = Split-Path -Parent $p
  if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
  [IO.File]::WriteAllBytes($p, $data); (Get-Item -LiteralPath $p).LastWriteTime = [datetime]$date
}
New-Item -ItemType Directory -Path $root -Force | Out-Null
$trec = Bytes 3MB;  Put 'Camtasia\rec1.trec' $trec;  Put 'Camtasia\P1.tscproj\rec1.trec' $trec          # outside
$clip = Bytes 2MB;  Put 'Camtasia\P2.tscproj\clip.mp4' $clip; Put 'Camtasia\P2.tscproj\P2.tscproj\clip.mp4' $clip  # nested
$mus = Bytes 1MB;   Put 'Camtasia\P1.tscproj\music.mp3' $mus; Put 'Camtasia\P3.tscproj\music.mp3' $mus      # multi
$cfa = Bytes 512KB; Put 'Adobe\Audio Previews\X.PRV\a.cfa' $cfa; Put 'Adobe\Audio Previews\X.PRV\b.cfa' $cfa  # cache
$prj = Bytes 40KB;  Put 'Adobe\proj.prproj' $prj; Put 'Adobe\Auto-Save\proj.prproj' $prj                 # autosave
$doc = Bytes 80KB;  Put 'Docs\report.docx' $doc '2019-03-01'; Put 'Downloads\report (1).docx' $doc '2019-03-01'  # other
$ini = [Text.Encoding]::ASCII.GetBytes("[.ShellClassInfo]`r`nIconResource=x`r`n")
Put 'Camtasia\P1.tscproj\desktop.ini' $ini; Put 'Camtasia\P3.tscproj\desktop.ini' $ini                     # sys
Put 'Wireshark\ssl-keys.log' (Bytes 2MB) '2024-12-23'
Put 'Videos\big.mp4' (Bytes 5MB) '2026-01-07'
Put 'same-size-A.bin' (Bytes 64KB); Put 'same-size-B.bin' (Bytes 64KB)    # cùng cỡ, khác nội dung
Put 'Pass.txt' ([Text.Encoding]::ASCII.GetBytes('placeholder')) '2018-05-05'
Put 'Docs\~$report.docx' (Bytes 162)
Put 'zero.vssx' ([byte[]]@())
New-Item -ItemType Directory -Path (Join-Path $root 'Empty\Nested') -Force | Out-Null

function Snapshot {
  $f = Get-ChildItem -LiteralPath $root -Recurse -Force | Sort-Object FullName | ForEach-Object {
    $h = if ($_.PSIsContainer) { '<dir>' } else { (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
    "{0}|{1}|{2}|{3}|{4}" -f $_.FullName.Substring($root.Length), $(if ($_.PSIsContainer) { '' } else { $_.Length }), $_.LastWriteTimeUtc.Ticks, $_.Attributes, $h }
  ($f -join "`n")
}
# NTFS cập nhật thời gian thư mục trễ sau khi tạo file: chờ đến khi hai ảnh chụp liên tiếp trùng nhau
$before = Snapshot
for ($i = 0; $i -lt 15; $i++) { Start-Sleep -Milliseconds 1000; $again = Snapshot; if ($again -eq $before) { break }; $before = $again }
"Dữ liệu mẫu: $root (ổn định sau $($i+1)s)"

# ---------- 2. Kiểm tra tĩnh: script quét không có lệnh ghi/xóa ----------
"[Tĩnh] scan.ps1 chỉ đọc"
$src = Get-Content -LiteralPath $scan -Raw
$bad = 'Remove-Item','Move-Item','Rename-Item','Set-Content','Add-Content','Clear-Content','Out-File','Copy-Item','Set-ItemProperty','Set-Acl','\.Delete\(','\.MoveTo\(','DeleteFile','WriteAllBytes','\.LastWriteTime\s*='
Check 'không chứa cmdlet/API ghi, xóa, đổi tên' (-not ($bad | Where-Object { $src -match $_ }))
Check 'chỉ ghi duy nhất file kết quả $outFull' ((([regex]::Matches($src, 'WriteAllText\(')).Count -eq 1) -and ($src -match 'WriteAllText\(\$outFull'))

# ---------- 3. Từ chối ghi kết quả vào trong thư mục quét ----------
"[Bảo vệ] từ chối ghi vào thư mục quét"
$refused = $false
try { & $scan -Root $root -Out (Join-Path $root 'scan.json') | Out-Null } catch { $refused = $_.Exception.Message -match 'Từ chối' }
Check 'scan.ps1 từ chối -Out nằm trong -Root' ($refused -and -not (Test-Path (Join-Path $root 'scan.json')))

# ---------- 4. Quét và kiểm tra kết quả ----------
"[Quét]"
$json = Join-Path $work 'scan.json'
& $scan -Root $root -Out $json | ForEach-Object { "  $_" }
$d = Get-Content -LiteralPath $json -Raw -Encoding UTF8 | ConvertFrom-Json
$expectFiles = @(Get-ChildItem -LiteralPath $root -Recurse -File -Force).Count
Check "đếm đủ $expectFiles file" ($d.files.Count -eq $expectFiles)
Check 'tổng dung lượng khớp' (($d.files | Measure-Object s -Sum).Sum -eq (Get-ChildItem -LiteralPath $root -Recurse -File -Force | Measure-Object Length -Sum).Sum)
$groups = @($d.files | Where-Object h | Group-Object h | Where-Object Count -gt 1)
Check '7 nhóm trùng (outside, nested, multi, cache, autosave, other, sys)' ($groups.Count -eq 7)
Check 'file cùng cỡ khác nội dung không bị coi là trùng' (-not ($groups | Where-Object { $_.Group.p -contains 'same-size-A.bin' }))
Check 'phát hiện thư mục rỗng Empty\Nested' ($d.emptyDirs -contains 'Empty\Nested')
Check 'năm sửa được ghi nhận (2018, 2019, 2024, 2025, 2026)' ((@($d.files.y | Sort-Object -Unique) -join ',') -eq '2018,2019,2024,2025,2026')
Check 'phần dư trùng = 3MB+2MB+1MB+512KB+40KB+80KB+ini' ((($groups | ForEach-Object { $_.Group[0].s * ($_.Count - 1) }) | Measure-Object -Sum).Sum -eq (3MB+2MB+1MB+512KB+40KB+80KB+$ini.Length))

# ---------- 5. Dựng báo cáo ----------
"[Báo cáo]"
$refused = $false
try { & $build -Data $json -Out (Join-Path $root 'r.html') | Out-Null } catch { $refused = $_.Exception.Message -match 'Từ chối' }
Check 'build-report.ps1 từ chối ghi báo cáo vào thư mục quét' ($refused -and -not (Test-Path (Join-Path $root 'r.html')))
$html = Join-Path $work 'bao-cao-mau.html'
& $build -Data $json -Out $html | ForEach-Object { "  $_" }
$h = [IO.File]::ReadAllText($html)
Check 'dữ liệu được nhúng vào HTML' (($h -notmatch '/\*DATA\*/') -and ($h -match 'ssl-keys\.log'))

# ---------- 6. Dữ liệu gốc không đổi ----------
"[Chỉ đọc] so sánh ảnh chụp trước/sau (đường dẫn, kích thước, ngày sửa, thuộc tính, SHA-256)"
$after = Snapshot
Check 'dữ liệu mẫu giữ nguyên từng byte, không thêm/bớt file' ($before -eq $after)
if ($before -ne $after) { Compare-Object ($before -split "`n") ($after -split "`n") | ForEach-Object { "    {0} {1}" -f $_.SideIndicator, $_.InputObject } }

""
"Kết quả: $pass PASS, $fail FAIL"
"Báo cáo mẫu: $html"
if (-not $Keep -and $fail -eq 0) { Remove-Item -LiteralPath $root -Recurse -Force; "(Đã xóa dữ liệu mẫu tạm; giữ lại báo cáo và scan.json trong $work)" }
if ($fail) { exit 1 }
