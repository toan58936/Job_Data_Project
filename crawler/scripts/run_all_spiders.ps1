param(
    [Parameter(Mandatory=$false)]
    [string]$BatchDate = (Get-Date -Format "yyyy-MM-dd")
)

$ErrorActionPreference = "Stop"
# Lấy đường dẫn thư mục chứa script (thư mục scripts/)
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
# Lùi lại 1 cấp để lấy thư mục crawler/ (nơi chứa scrapy.cfg)
$CrawlerDir = (Get-Item $ScriptDir).Parent.FullName

# ÉP TERMINAL DI CHUYỂN VÀO THƯ MỤC CRAWLER
Set-Location $CrawlerDir

$Python = "E:\job-data-project\.venv\Scripts\python.exe"

Write-Host "=== Crawl Phase: Batch $BatchDate ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "[1/2] Crawling listings..." -ForegroundColor Yellow
& $Python -m scrapy crawl itviec_listing -a batch_date="$BatchDate" -s LOG_LEVEL=INFO
if ($LASTEXITCODE -ne 0) { Write-Warning "itviec_listing exited with code $LASTEXITCODE" }

& $Python -m scrapy crawl topcv_listing -a batch_date="$BatchDate" -s LOG_LEVEL=INFO
if ($LASTEXITCODE -ne 0) { Write-Warning "topcv_listing exited with code $LASTEXITCODE" }

Write-Host ""
Write-Host "[2/2] Crawling details..." -ForegroundColor Yellow
& $Python -m scrapy crawl itviec_detail -a batch_date="$BatchDate" -s LOG_LEVEL=INFO
if ($LASTEXITCODE -ne 0) { Write-Warning "itviec_detail exited with code $LASTEXITCODE" }

& $Python -m scrapy crawl topcv_detail -a batch_date="$BatchDate" -s LOG_LEVEL=INFO
if ($LASTEXITCODE -ne 0) { Write-Warning "topcv_detail exited with code $LASTEXITCODE" }

Write-Host ""
Write-Host "=== Crawl phase complete ===" -ForegroundColor Cyan