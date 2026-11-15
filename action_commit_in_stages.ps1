
param(
    [int]$BatchSize = 1000,
    [string]$Remote = "origin"
)

$ErrorActionPreference = "Stop"

# Confirm we're inside a Git repository
git rev-parse --is-inside-work-tree *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Not inside a Git repository."
}

# Identify the current branch
$Branch = (git branch --show-current).Trim()
if (-not $Branch) {
    throw "Cannot determine current branch."
}

# Check for unfinished merges/rebases
$GitDir = (git rev-parse --git-dir).Trim()
if ((Test-Path "$GitDir/MERGE_HEAD") -or
    (Test-Path "$GitDir/rebase-merge") -or
    (Test-Path "$GitDir/rebase-apply")) {
    throw "Finish the current merge or rebase first."
}

# Push existing commits first, so batching starts
# from a clean remote state.
Write-Host "Pushing existing commits..." -ForegroundColor Cyan
git push $Remote $Branch
if ($LASTEXITCODE -ne 0) {
    throw "Initial push failed. No files changed."
}

# Get all changed files as NUL-delimited names.
# Includes untracked files, modifications and deletions.
$Raw = & git -c core.quotepath=false ls-files `
    --modified --deleted --others --exclude-standard -z

if ($LASTEXITCODE -ne 0) {
    throw "Failed to list changed files."
}

$Files = @($Raw -split "`0" | Where-Object { $_ -ne "" })

# Include already-staged files, without duplicates.
$StagedRaw = & git -c core.quotepath=false diff `
    --cached --name-only -z

if ($LASTEXITCODE -ne 0) {
    throw "Failed to list staged files."
}

$Staged = @($StagedRaw -split "`0" | Where-Object { $_ -ne "" })
$Files = @($Files + $Staged | Sort-Object -Unique)

$Total = $Files.Count

if ($Total -eq 0) {
    Write-Host "Nothing to commit. All done!" -ForegroundColor Green
    exit 0
}

$TotalBatches = [math]::Ceiling($Total / $BatchSize)
$CommittedBatches = 0

Write-Host "Found $Total files." -ForegroundColor Cyan
Write-Host "Processing $TotalBatches batches of up to $BatchSize files (commit + push per batch)."

# Ensure batching is strict even if something was already staged before running.
# This only resets the index (staging area), not working-tree file contents.
git reset
if ($LASTEXITCODE -ne 0) {
    throw "Failed to reset index before batch processing."
}

for ($Start = 0; $Start -lt $Total; $Start += $BatchSize) {
    $End = [math]::Min($Start + $BatchSize, $Total)
    $BatchNumber = [int]($Start / $BatchSize) + 1
    $Batch = @($Files[$Start..($End - 1)])

    Write-Host ""
    Write-Host "========================================"
    Write-Host "Batch $BatchNumber / $TotalBatches"
    Write-Host "Files $($Start + 1) to $End of $Total"
    Write-Host "========================================" -ForegroundColor Yellow

    # Skip stale paths that no longer exist and are not tracked.
    $ValidBatch = @()
    foreach ($File in $Batch) {
        if (Test-Path -LiteralPath $File) {
            $ValidBatch += $File
            continue
        }

        git ls-files --error-unmatch -- "$File" *> $null
        if ($LASTEXITCODE -eq 0) {
            $ValidBatch += $File
        }
        else {
            Write-Host "Skipping stale path: $File" -ForegroundColor DarkYellow
        }
    }

    if ($ValidBatch.Count -eq 0) {
        Write-Host "No valid paths left in this batch."
        continue
    }

    $TempFile = [IO.Path]::GetTempFileName()
    try {
        $PathBytes = foreach ($File in $ValidBatch) {
            [Text.Encoding]::UTF8.GetBytes(
                ":(literal)$File"
            )
            [byte]0
        }

        [IO.File]::WriteAllBytes(
            $TempFile,
            [byte[]]@($PathBytes)
        )

        git add -A `
            --pathspec-from-file="$TempFile" `
            --pathspec-file-nul

        if ($LASTEXITCODE -ne 0) {
            throw "Git add failed while staging batch $BatchNumber of $TotalBatches."
        }
    }
    finally {
        Remove-Item $TempFile -ErrorAction SilentlyContinue
    }

    $StagedCount = @(
        git diff --cached --name-only | Where-Object { $_ -ne "" }
    ).Count

    if ($StagedCount -gt $ValidBatch.Count) {
        throw "Batch $BatchNumber staged $StagedCount files, expected at most $($ValidBatch.Count). Stopping to avoid oversized commit."
    }

    git diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "No staged changes in this batch."
        continue
    }

    $Message = "Batch $BatchNumber of $TotalBatches - $($ValidBatch.Count) files"
    git commit -m $Message

    if ($LASTEXITCODE -ne 0) {
        throw "Commit failed at batch $BatchNumber"
    }

    Write-Host "Pushing batch $BatchNumber..." -ForegroundColor Cyan
    git push $Remote $Branch

    if ($LASTEXITCODE -ne 0) {
        throw "Push failed at batch $BatchNumber. Stopping."
    }

    $CommittedBatches++
    $Percent = [math]::Round(($End / $Total) * 100, 1)
    Write-Host "Batch $BatchNumber pushed successfully. $Percent% complete." -ForegroundColor Green
}

Write-Host ""
Write-Host "ALL DONE! $Total files processed. $CommittedBatches batch commit(s) uploaded." -ForegroundColor Green
