<#
.SYNOPSIS
    Git Sync Tool - Backup to GitHub
.EXAMPLE
    .\git_sync.ps1 push "message"     # Commit and push
    .\git_sync.ps1 pull               # Pull latest
    .\git_sync.ps1 status             # Check status
    .\git_sync.ps1 setup              # First-time setup
#>

param(
    [Parameter(Position=0)]
    [ValidateSet("push", "pull", "status", "setup", "backup")]
    [string]$Action = "status",
    
    [Parameter(Position=1)]
    [string]$Message = ""
)

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

function Write-Status($Msg, $Type = "INFO") {
    $color = switch ($Type) {
        "INFO" { "Cyan" }
        "OK" { "Green" }
        "WARN" { "Yellow" }
        "ERR" { "Red" }
        default { "White" }
    }
    Write-Host "[$Type] $Msg" -ForegroundColor $color
}

Push-Location $RepoRoot

switch ($Action) {
    "status" {
        Write-Host "`n=== GIT STATUS ===" -ForegroundColor Cyan
        git status --short
        Write-Host ""
        
        $remote = git remote -v 2>$null
        if ($remote) {
            Write-Host "Remote:" -ForegroundColor Yellow
            Write-Host $remote
        } else {
            Write-Status "No remote configured. Run: .\git_sync.ps1 setup" "WARN"
        }
    }
    
    "setup" {
        Write-Host "`n=== GITHUB SETUP ===" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Steps to connect to GitHub:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "1. Create a new repository on GitHub:" -ForegroundColor White
        Write-Host "   https://github.com/new" -ForegroundColor Gray
        Write-Host "   Name: EA-Development (or your choice)" -ForegroundColor Gray
        Write-Host "   Private: Yes (recommended for trading code)" -ForegroundColor Gray
        Write-Host ""
        Write-Host "2. Copy the repository URL and run:" -ForegroundColor White
        Write-Host "   git remote add origin https://github.com/YOUR_USERNAME/EA-Development.git" -ForegroundColor Gray
        Write-Host ""
        Write-Host "3. Push to GitHub:" -ForegroundColor White
        Write-Host "   git push -u origin main" -ForegroundColor Gray
        Write-Host ""
        Write-Host "Or use SSH (if configured):" -ForegroundColor Yellow
        Write-Host "   git remote add origin git@github.com:YOUR_USERNAME/EA-Development.git" -ForegroundColor Gray
        Write-Host ""
        
        $repoUrl = Read-Host "Enter GitHub repo URL (or press Enter to skip)"
        if ($repoUrl) {
            git remote add origin $repoUrl
            Write-Status "Remote added: $repoUrl" "OK"
            Write-Host ""
            Write-Host "Now run: .\git_sync.ps1 push `"Initial push`"" -ForegroundColor Yellow
        }
    }
    
    "push" {
        if (-not $Message) {
            $Message = "Auto backup: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
        }
        
        Write-Status "Adding changes..."
        git add -A
        
        $changes = git status --porcelain
        if (-not $changes) {
            Write-Status "No changes to commit" "WARN"
            Pop-Location
            return
        }
        
        Write-Status "Committing: $Message"
        git commit -m $Message
        
        $remote = git remote -v 2>$null
        if ($remote) {
            Write-Status "Pushing to GitHub..."
            git push origin main 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Status "Pushed successfully!" "OK"
            } else {
                Write-Status "Push failed. Try: git push -u origin main" "ERR"
            }
        } else {
            Write-Status "No remote. Run: .\git_sync.ps1 setup" "WARN"
        }
    }
    
    "pull" {
        Write-Status "Pulling from GitHub..."
        git pull origin main
        if ($LASTEXITCODE -eq 0) {
            Write-Status "Pull successful!" "OK"
        }
    }
    
    "backup" {
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
        Write-Status "Creating backup: $timestamp"
        git add -A
        git commit -m "Backup: $timestamp"
        
        $remote = git remote -v 2>$null
        if ($remote) {
            git push origin main
            Write-Status "Backup pushed to GitHub!" "OK"
        } else {
            Write-Status "Local backup created. No remote configured." "WARN"
        }
    }
}

Pop-Location
