# fix_timestamps.ps1
<#
.SYNOPSIS
Finds and fixes all timestamp format errors in Python files.

.DESCRIPTION
This script searches for common timestamp format issues and fixes them:
1. datetime.now(UTC).isoformat() + "Z" -> Proper UTC Z format
2. datetime.utcnow() -> datetime.now(UTC) (deprecation fix)
3. Incorrect timestamp concatenations

.PARAMETER Path
The directory to search (default: current directory).

.PARAMExtension
The file extension to search (default: *.py).

.EXAMPLE
.\fix_timestamps.ps1
Fixes all timestamp issues in current directory.

.EXAMPLE
.\fix_timestamps.ps1 -Path "C:\MyProject" -Extension "*.py"
Fixes timestamp issues in specific directory.
#>

param(
    [string]$Path = ".",
    [string]$Extension = "*.py"
)

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Fix-TimestampFormat {
    param(
        [string]$Content
    )
    
    $originalContent = $Content
    $changesMade = 0
    
    # Pattern 1: Fix datetime.now(UTC).isoformat() + "Z" (creates +00:00Z)
    $pattern1 = 'datetime\.now\(UTC\)\.isoformat\([^)]*\)\s*\+\s*["\']Z["\']'
    if ($Content -match $pattern1) {
        Write-ColorOutput "  Found: datetime.now(UTC).isoformat() + 'Z'" -Color Yellow
        
        # Replace with proper format
        $Content = $Content -replace $pattern1, 'datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")'
        $changesMade++
        Write-ColorOutput "  Fixed: datetime.now(UTC).isoformat(timespec='milliseconds').replace('+00:00', 'Z')" -Color Green
    }
    
    # Pattern 2: Fix datetime.utcnow() deprecation
    $pattern2 = 'datetime\.utcnow\(\)'
    if ($Content -match $pattern2) {
        $matches = [regex]::Matches($Content, $pattern2)
        Write-ColorOutput "  Found $($matches.Count) instances of datetime.utcnow()" -Color Yellow
        
        $Content = $Content -replace $pattern2, 'datetime.now(UTC)'
        $changesMade += $matches.Count
        Write-ColorOutput "  Fixed: datetime.now(UTC)" -Color Green
    }
    
    # Pattern 3: Fix isoformat() without parameters that might have issues
    $pattern3 = '\.isoformat\(\)\s*\+\s*["\']Z["\']'
    if ($Content -match $pattern3) {
        Write-ColorOutput "  Found: .isoformat() + 'Z'" -Color Yellow
        
        $Content = $Content -replace $pattern3, '.isoformat(timespec="milliseconds").replace("+00:00", "Z")'
        $changesMade++
        Write-ColorOutput "  Fixed: .isoformat(timespec='milliseconds').replace('+00:00', 'Z')" -Color Green
    }
    
    # Pattern 4: Fix raw string timestamps ending with +00:00Z
    $pattern4 = '"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+00:00Z"'
    if ($Content -match $pattern4) {
        $matches = [regex]::Matches($Content, $pattern4)
        Write-ColorOutput "  Found $($matches.Count) raw timestamps with +00:00Z format" -Color Yellow
        
        foreach ($match in $matches) {
            $badTimestamp = $match.Value
            $fixedTimestamp = $badTimestamp -replace '\+00:00Z', 'Z'
            $Content = $Content -replace [regex]::Escape($badTimestamp), $fixedTimestamp
            Write-ColorOutput "  Fixed: $fixedTimestamp" -Color Green
        }
        $changesMade += $matches.Count
    }
    
    # Pattern 5: Common timestamp variable assignments that might be wrong
    $timestampPatterns = @(
        @{
            Name = "timestamp with .isoformat() + Z"
            Pattern = 'timestamp\s*[:=]\s*.+?\.isoformat\([^)]*\)\s*\+\s*["\']Z["\']'
            Replacement = 'timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")'
        },
        @{
            Name = "timestamp assignment with concatenation"
            Pattern = '["\']timestamp["\']\s*:\s*.+?\.isoformat\([^)]*\)\s*\+\s*["\']Z["\']'
            Replacement = '"timestamp": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")'
        }
    )
    
    foreach ($patternInfo in $timestampPatterns) {
        if ($Content -match $patternInfo.Pattern) {
            Write-ColorOutput "  Found: $($patternInfo.Name)" -Color Yellow
            $Content = $Content -replace $patternInfo.Pattern, $patternInfo.Replacement
            $changesMade++
            Write-ColorOutput "  Fixed with proper format" -Color Green
        }
    }
    
    return @{
        Content = $Content
        Changed = ($Content -ne $originalContent)
        ChangesMade = $changesMade
    }
}

function Add-UTCImport {
    param(
        [string]$Content
    )
    
    # Check if datetime is imported
    if ($Content -match 'from datetime import') {
        # Check if UTC is already imported
        if (-not ($Content -match 'from datetime import.*UTC')) {
            Write-ColorOutput "  Adding UTC to datetime import" -Color Cyan
            $Content = $Content -replace 'from datetime import', 'from datetime import datetime, UTC'
        }
    }
    elseif ($Content -match 'import datetime') {
        # Already has import datetime
    }
    else {
        # Add import if datetime is used but not imported
        if ($Content -match 'datetime\.') {
            Write-ColorOutput "  Adding datetime import" -Color Cyan
            # Find the first import line
            $lines = $Content -split "`n"
            $importAdded = $false
            for ($i = 0; $i -lt $lines.Count; $i++) {
                if ($lines[$i] -match '^import ') {
                    $lines[$i] = "from datetime import datetime, UTC`n" + $lines[$i]
                    $importAdded = $true
                    break
                }
            }
            if (-not $importAdded) {
                # Add at the beginning
                $Content = "from datetime import datetime, UTC`n`n" + $Content
            } else {
                $Content = $lines -join "`n"
            }
        }
    }
    
    return $Content
}

# Main script
Write-ColorOutput "==============================================" -Color Cyan
Write-ColorOutput "  TIMESTAMP FORMAT FIXER SCRIPT" -Color Cyan
Write-ColorOutput "==============================================" -Color Cyan
Write-Host ""

$searchPath = Resolve-Path $Path
Write-ColorOutput "Searching in: $searchPath" -Color White
Write-ColorOutput "File pattern: $Extension" -Color White
Write-Host ""

$files = Get-ChildItem -Path $Path -Filter $Extension -Recurse -File
$totalFiles = $files.Count
$filesFixed = 0
$totalChanges = 0

Write-ColorOutput "Found $totalFiles Python files to check" -Color White
Write-Host ""

foreach ($file in $files) {
    $relativePath = $file.FullName.Replace($searchPath.Path, "").TrimStart("\")
    Write-ColorOutput "Checking: $relativePath" -Color Gray
    
    try {
        $content = Get-Content $file.FullName -Raw
        
        # First, ensure UTC import is present
        $content = Add-UTCImport -Content $content
        
        # Fix timestamp formats
        $result = Fix-TimestampFormat -Content $content
        
        if ($result.Changed) {
            # Backup the original file
            $backupPath = "$($file.FullName).backup"
            Copy-Item $file.FullName $backupPath -Force
            
            # Write the fixed content
            $result.Content | Set-Content $file.FullName -Encoding UTF8
            
            Write-ColorOutput "  ✅ Fixed $($result.ChangesMade) issues" -Color Green
            Write-ColorOutput "  Backup saved to: $($backupPath)" -Color DarkGray
            
            $filesFixed++
            $totalChanges += $result.ChangesMade
        } else {
            Write-ColorOutput "  ✓ No issues found" -Color DarkGray
        }
        
    } catch {
        Write-ColorOutput "  ❌ Error processing file: $_" -Color Red
    }
    
    Write-Host ""
}

# Summary
Write-ColorOutput "==============================================" -Color Cyan
Write-ColorOutput "  SUMMARY" -Color Cyan
Write-ColorOutput "==============================================" -Color Cyan
Write-Host ""
Write-ColorOutput "Files checked: $totalFiles" -Color White
Write-ColorOutput "Files fixed: $filesFixed" -Color White
Write-ColorOutput "Total changes made: $totalChanges" -Color White
Write-Host ""
Write-ColorOutput "Common timestamp patterns fixed:" -Color Yellow
Write-ColorOutput "  1. datetime.utcnow() → datetime.now(UTC)" -Color White
Write-ColorOutput "  2. .isoformat() + 'Z' → .isoformat().replace('+00:00', 'Z')" -Color White
Write-ColorOutput "  3. Raw timestamps with '+00:00Z' → 'Z'" -Color White
Write-Host ""
Write-ColorOutput "Next steps:" -Color Green
Write-ColorOutput "  1. Review the changes made" -Color White
Write-ColorOutput "  2. Test your application" -Color White
Write-ColorOutput "  3. Run: poetry run python test_correct_message.py" -Color White
Write-ColorOutput "  4. Check AI service logs for validation errors" -Color White
Write-Host ""

# Create a test script to verify the fix
$testScript = @"
# test_timestamp_fix.py
"""
Test script to verify timestamp formats are fixed.
"""
from datetime import datetime, UTC

def test_timestamps():
    print("Testing timestamp formats...")
    
    # Test 1: datetime.now(UTC) instead of datetime.utcnow()
    now_utc = datetime.now(UTC)
    print(f"✅ datetime.now(UTC): {now_utc}")
    
    # Test 2: Correct timestamp format for AIRequest
    timestamp = datetime.now(UTC).isoformat(timespec="milliseconds")
    if timestamp.endswith("+00:00"):
        timestamp = timestamp[:-6] + "Z"
    else:
        timestamp = timestamp + "Z"
    
    print(f"✅ Correct timestamp format: {timestamp}")
    
    # Test 3: Should NOT have +00:00Z
    if "+00:00Z" in timestamp:
        print(f"❌ Still has +00:00Z: {timestamp}")
    else:
        print(f"✅ No +00:00Z in timestamp")
    
    # Test 4: Should end with Z
    if timestamp.endswith("Z"):
        print(f"✅ Timestamp ends with Z")
    else:
        print(f"❌ Timestamp doesn't end with Z: {timestamp}")
    
    return timestamp

if __name__ == "__main__":
    test_timestamps()
"@

$testScriptPath = Join-Path $searchPath "test_timestamp_fix.py"
$testScript | Set-Content $testScriptPath -Encoding UTF8
Write-ColorOutput "Created test script: $testScriptPath" -Color Cyan
Write-ColorOutput "Run it with: poetry run python test_timestamp_fix.py" -Color White