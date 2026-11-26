<#
  Dựng báo cáo HTML tự chứa từ JSON do scan.ps1 tạo.
  -Out bắt buộc nằm NGOÀI thư mục đã quét. -Open: mở bằng trình duyệt mặc định.

  Ví dụ: powershell -NoProfile -ExecutionPolicy Bypass -File build-report.ps1 -Data "$env:TEMP\scan.json" -Out ".\bao-cao.html" -Open
#>
param(
  [Parameter(Mandatory)][string]$Data,
  [Parameter(Mandatory)][string]$Out,
  [switch]$Open
)
$ErrorActionPreference = 'Stop'
$tpl = Join-Path $PSScriptRoot '..\assets\template.html'
$json = [IO.File]::ReadAllText((Resolve-Path -LiteralPath $Data).ProviderPath).Trim([char]0xFEFF)
$root = ($json | ConvertFrom-Json).root
$outFull = [IO.Path]::GetFullPath($Out)
if ($outFull.StartsWith($root.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) {
  throw "Từ chối: báo cáo '$outFull' nằm trong thư mục đã quét '$root'. Hãy ghi ra ngoài (chế độ chỉ đọc)."
}
$html = [IO.File]::ReadAllText((Resolve-Path $tpl).ProviderPath).Replace('/*DATA*/', $json.Replace('</', '<\/'))
[IO.File]::WriteAllText($outFull, $html, (New-Object Text.UTF8Encoding $false))
"Đã tạo báo cáo: $outFull ({0:N0} KB)" -f ((Get-Item -LiteralPath $outFull).Length / 1KB)
if ($Open) { Start-Process -FilePath $outFull }
