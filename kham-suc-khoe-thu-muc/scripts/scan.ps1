<#
  Quét CHỈ ĐỌC một thư mục: liệt kê file (đường dẫn tương đối, đuôi, kích thước, ngày sửa),
  băm SHA-256 các file có cùng kích thước để tìm trùng nội dung, liệt kê thư mục rỗng.
  Không ghi, đổi tên, di chuyển hay xóa bất cứ thứ gì trong -Root.
  Kết quả JSON ghi ra -Out, bắt buộc nằm NGOÀI -Root.

  Ví dụ: powershell -NoProfile -ExecutionPolicy Bypass -File scan.ps1 -Root "D:\Documents" -Out "$env:TEMP\scan.json"
#>
param(
  [Parameter(Mandatory)][string]$Root,
  [Parameter(Mandatory)][string]$Out
)
$ErrorActionPreference = 'Stop'

$rootFull = (Resolve-Path -LiteralPath $Root).ProviderPath.TrimEnd('\')
if (-not (Test-Path -LiteralPath $rootFull -PathType Container)) { throw "Không phải thư mục: $Root" }
$outFull = [IO.Path]::GetFullPath($Out)
if ($outFull.StartsWith($rootFull + '\', [StringComparison]::OrdinalIgnoreCase) -or $outFull -ieq $rootFull) {
  throw "Từ chối: file kết quả '$outFull' nằm trong thư mục đang quét. Hãy ghi ra ngoài '$rootFull' (chế độ chỉ đọc)."
}
$cut = $rootFull.Length + 1
$rel = { param($full) $full.Substring($cut) }

# 1. Liệt kê file (chỉ đọc siêu dữ liệu)
$enumErr = @()
$files = @(Get-ChildItem -LiteralPath $rootFull -Recurse -File -Force -ErrorAction SilentlyContinue -ErrorVariable +enumErr)
$items = foreach ($f in $files) {
  [pscustomobject]@{
    p = & $rel $f.FullName
    e = $f.Extension.ToLower().TrimStart('.')
    s = [int64]$f.Length
    y = $f.LastWriteTime.Year
    m = $f.LastWriteTime.ToString('yyyy-MM-dd')
    h = $null
  }
}
$items = @($items)

# 2. Băm nội dung các file trùng kích thước (Get-FileHash mở file ở chế độ đọc)
$hashErr = 0
$cand = $items | Where-Object { $_.s -gt 0 } | Group-Object s | Where-Object Count -gt 1
foreach ($g in $cand) {
  foreach ($it in $g.Group) {
    try { $it.h = (Get-FileHash -LiteralPath (Join-Path $rootFull $it.p) -Algorithm SHA256 -ErrorAction Stop).Hash }
    catch { $hashErr++ }
  }
}

# 3. Thư mục và thư mục rỗng
$dirs = @(Get-ChildItem -LiteralPath $rootFull -Recurse -Directory -Force -ErrorAction SilentlyContinue)
$empty = @($dirs | Where-Object { -not (Get-ChildItem -LiteralPath $_.FullName -Force -ErrorAction SilentlyContinue | Select-Object -First 1) } |
  ForEach-Object { & $rel $_.FullName })

$ssl = [bool](@('Process','User','Machine') | ForEach-Object { [Environment]::GetEnvironmentVariable('SSLKEYLOGFILE', $_) } | Where-Object { $_ })

$res = [pscustomobject]@{
  root      = $rootFull
  scanned   = (Get-Date).ToString('yyyy-MM-dd HH:mm')
  dirs      = $dirs.Count
  emptyDirs = $empty
  errors    = [pscustomobject]@{ enumerate = $enumErr.Count; hash = $hashErr }
  env       = [pscustomobject]@{ sslkeylog = $ssl }
  files     = $items
}
$json = $res | ConvertTo-Json -Depth 5 -Compress
$outDir = Split-Path -Parent $outFull
if ($outDir -and -not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
[IO.File]::WriteAllText($outFull, $json, (New-Object Text.UTF8Encoding $false))

$tot = ($items | Measure-Object s -Sum).Sum
"Đã quét {0}: {1} file, {2:N2} GB, {3} thư mục ({4} rỗng); băm {5} file; lỗi đọc {6}/{7}. Kết quả: {8}" -f `
  $rootFull, $items.Count, ($tot/1GB), $dirs.Count, $empty.Count, @($items | Where-Object h).Count, $enumErr.Count, $hashErr, $outFull
