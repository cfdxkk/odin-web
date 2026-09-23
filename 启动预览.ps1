$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$bundledNode = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$siteNode = if (Test-Path -LiteralPath $bundledNode) { $bundledNode } else { (Get-Command node).Source }
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'node_modules\nuxt\bin\nuxt.mjs'))) {
  Write-Host '请先在项目文件夹执行 npm install。'
  exit 1
}
& $siteNode (Join-Path $PSScriptRoot 'node_modules\nuxt\bin\nuxt.mjs') dev --host 127.0.0.1 --port 3000
