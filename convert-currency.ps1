# Currency Replacement Script - Dollar to Euro
# Run this in your project root directory

Write-Host "Starting currency replacement from $ to €..." -ForegroundColor Cyan

# Define files to update
$templates = @(
    "order\templates\order\create.html",
    "order\templates\order\created.html", 
    "order\templates\order\payment.html",
    "shop\templates\shop\home.html",
    "shop\templates\shop\product\list.html",
    "shop\templates\shop\product\detail.html",
    "accounts\templates\accounts\admin\dashboard.html",
    "accounts\templates\accounts\admin\orders\detail.html",
    "accounts\templates\accounts\admin\orders\list.html",
    "accounts\templates\accounts\admin\products\list.html",
    "accounts\templates\accounts\admin\products\form.html",
    "accounts\templates\accounts\admin\customers\list.html"
)

$replacements = @{
    '\$\{\{' = '{{'
    '\$\{' = '{'
}

$count = 0

foreach ($file in $templates) {
    if (Test-Path $file) {
        Write-Host "Processing: $file" -ForegroundColor Yellow
        
        $content = Get-Content $file -Raw
        $original = $content
        
        # Replace dollar signs
        foreach ($pattern in $replacements.Keys) {
            $content = $content -replace $pattern, $replacements[$pattern]
        }
        
        # Replace USD references
        $content = $content -replace 'USD', 'EUR'
        $content = $content -replace '\$', '€'
        
        if ($content -ne $original) {
            Set-Content $file -Value $content -NoNewline
            $count++
            Write-Host "  ✓ Updated" -ForegroundColor Green
        } else {
            Write-Host "  - No changes needed" -ForegroundColor Gray
        }
    } else {
        Write-Host "  ✗ File not found: $file" -ForegroundColor Red
    }
}

Write-Host "`n✓ Processed $count files" -ForegroundColor Green
Write-Host "`nIMPORTANT: Manual review required!" -ForegroundColor Yellow
Write-Host "- Check that prices display correctly: 49.99€ (not €49.99)" -ForegroundColor Yellow
Write-Host "- Verify all templates render properly" -ForegroundColor Yellow
Write-Host "- Test the shop to ensure no broken layouts" -ForegroundColor Yellow
