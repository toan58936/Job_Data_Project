[CmdletBinding()]
param(
    [string]$BatchDate = (Get-Date -Format "yyyy-MM-dd")
)

Set-Location -LiteralPath $PSScriptRoot

Write-Host "=== Running all spiders | batch_date=$BatchDate ==="

$spiders = @(
    @{ Name = "topcv_listing"; Args = @("-a", "batch_date=$BatchDate") },
    @{ Name = "topcv_detail"; Args = @("-a", "batch_date=$BatchDate") },
    @{ Name = "itviec_listing"; Args = @("-a", "batch_date=$BatchDate") },
    @{ Name = "itviec_detail"; Args = @("-a", "batch_date=$BatchDate") }
)

foreach ($s in $spiders) {
    Write-Host "`n--- scrapy crawl $($s.Name) ---"
    $argList = @("crawl", $s.Name) + $s.Args
    & scrapy @argList
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Spider $($s.Name) failed with exit code $LASTEXITCODE"
        exit $LASTEXITCODE
    }
}

Write-Host "`n=== All spiders completed successfully ==="
