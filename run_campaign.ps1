# Run Marketing-Creative Pipeline (Self-Execution Mode)
# Usage: .\run_campaign.ps1 -CampaignId "my-campaign" -Company "91astrology" -InputImage "C:\path\to\image.png"
param(
    [Parameter(Mandatory=$true)]
    [string]$CampaignId,

    [Parameter(Mandatory=$true)]
    [string]$Company,

    [string]$InputText,
    [string]$InputImage,
    [string]$InputUrl,
    [string]$IdeaId,

    [int]$NumImages = 1,
    [string]$Model = "auto",
    [switch]$Research,
    [string]$StopAfter
)

$ErrorActionPreference = "Stop"
$OMRoot = $PSScriptRoot

# Build input flag
$inputFlag = ""
if ($InputText) { $inputFlag = "--input-text `"$InputText`"" }
elseif ($InputImage) { $inputFlag = "--input-image `"$InputImage`"" }
elseif ($InputUrl) { $inputFlag = "--input-url `"$InputUrl`"" }
elseif ($IdeaId) { $inputFlag = "--idea-id `"$IdeaId`"" }
else {
    Write-Error "One of -InputText, -InputImage, -InputUrl, or -IdeaId is required"
    exit 1
}

$researchFlag = ""
if ($Research) { $researchFlag = "--research" }

$stopAfterFlag = ""
if ($StopAfter) { $stopAfterFlag = "--stop-after $StopAfter" }

Write-Host "=== Marketing-Creative Pipeline (Self-Execution) ===" -ForegroundColor Cyan
Write-Host "Campaign: $CampaignId" -ForegroundColor White
Write-Host "Company:  $Company" -ForegroundColor White
Write-Host "Images:   $NumImages" -ForegroundColor White
Write-Host "Model:    $Model" -ForegroundColor White
Write-Host "Mode:     Self-Execution (no subagents)" -ForegroundColor White
Write-Host ""

# Initial run
Write-Host "[1] Starting pipeline..." -ForegroundColor Yellow
$action = & python -m pipelines.marketing_creative `
    --campaign-id $CampaignId `
    --company $Company `
    $inputFlag `
    --auto `
    --self-execution `
    --num-images $NumImages `
    --model $Model `
    $researchFlag `
    $stopAfterFlag | ConvertFrom-Json

$stageCount = 1
$maxStages = 10

while ($action.action -ne "complete" -and $stageCount -lt $maxStages) {
    $stage = $action.stage
    Write-Host ""
    Write-Host "[$stageCount] Stage: $stage" -ForegroundColor Green

    if ($action.action -eq "execute_stage") {
        $skillPath = $action.instructions.skill_path
        Write-Host "      Skill: $skillPath" -ForegroundColor DarkGray
        Write-Host "      → Read the skill file and execute the stage yourself" -ForegroundColor Cyan
        Write-Host "      → Write all output files, then press Enter to resume" -ForegroundColor Cyan
        Write-Host ""

        # Save instructions to temp file for easy access
        $instructionsFile = "$env:TEMP\stage_instructions_$stage.json"
        $action.instructions | ConvertTo-Json -Depth 10 | Out-File -FilePath $instructionsFile -Encoding utf8
        Write-Host "      Instructions saved to: $instructionsFile" -ForegroundColor DarkGray

        # For assets stage, show Python tool examples
        if ($stage -eq "assets") {
            Write-Host "      === IMAGE GENERATION ===" -ForegroundColor Yellow
            Write-Host "      Run Python scripts to generate images." -ForegroundColor White
            Write-Host "      Example:" -ForegroundColor White
            Write-Host "      python -c \"from tools.tool_registry import registry; registry.discover(); selector = registry.get('image_selector'); result = selector.execute({'prompt': '...', 'width': 1024, 'height': 1024, 'output_path': 'assets/cr01.png'}); print(result)\"" -ForegroundColor DarkGray
            Write-Host ""
        }

        Write-Host "      After executing the stage, press Enter to continue..." -ForegroundColor Cyan
        Read-Host
    }
    elseif ($action.action -eq "await_human_approval") {
        Write-Host "      → Human approval required for stage: $stage" -ForegroundColor Magenta
        Write-Host "      Approve and press Enter to continue..." -ForegroundColor Cyan
        Read-Host
    }
    elseif ($action.action -eq "paused") {
        Write-Host "      → Pipeline paused: $($action.message)" -ForegroundColor Magenta
        Write-Host "      Resume command: $($action.next_command)" -ForegroundColor Cyan
        Write-Host "      Press Enter to resume..." -ForegroundColor Cyan
        Read-Host
    }
    elseif ($action.action -eq "error") {
        Write-Host "      ERROR: $($action.message)" -ForegroundColor Red
        exit 1
    }

    # Resume
    Write-Host "      Resuming pipeline..." -ForegroundColor Yellow
    $action = & python -m pipelines.marketing_creative `
        --campaign-id $CampaignId `
        --company $Company `
        --resume `
        --auto `
        --self-execution | ConvertFrom-Json

    $stageCount++
}

if ($action.action -eq "complete") {
    Write-Host ""
    Write-Host "=== PIPELINE COMPLETE ===" -ForegroundColor Green
    Write-Host "Campaign dir: $($action.campaign_dir)" -ForegroundColor White
    Write-Host "Stages: $($action.completed_stages -join ' -> ')" -ForegroundColor White
}
else {
    Write-Host ""
    Write-Host "=== PIPELINE STOPPED (max stages reached) ===" -ForegroundColor Red
}
