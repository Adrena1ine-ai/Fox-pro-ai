# PowerShell команды для анализа проекта

## 1. Запуск Fox Pro AI Doctor (рекомендуется)

```powershell
# Показать диагностику проекта
python main.py doctor . --report

# Полная оптимизация
python main.py doctor . --full

# Только исправление проблем
python main.py doctor . --fix
```

## 2. Анализ файлов по типам (PowerShell)

```powershell
# Статистика по расширениям файлов
Get-ChildItem -Recurse -File | 
    Group-Object Extension | 
    Select-Object Name, Count, 
        @{Name="TotalSizeMB";Expression={($_.Group | Measure-Object -Property Length -Sum).Sum / 1MB}} |
    Sort-Object TotalSizeMB -Descending |
    Format-Table -AutoSize

# Топ-10 самых больших файлов
Get-ChildItem -Recurse -File | 
    Sort-Object Length -Descending | 
    Select-Object -First 10 Name, 
        @{Name="SizeMB";Expression={[math]::Round($_.Length / 1MB, 2)}}, 
        @{Name="SizeKB";Expression={[math]::Round($_.Length / 1KB, 2)}},
        FullName |
    Format-Table -AutoSize

# Файлы больше 1MB
Get-ChildItem -Recurse -File | 
    Where-Object {$_.Length -gt 1MB} | 
    Select-Object Name, 
        @{Name="SizeMB";Expression={[math]::Round($_.Length / 1MB, 2)}}, 
        FullName |
    Sort-Object SizeMB -Descending |
    Format-Table -AutoSize

# Подсчёт токенов (примерно: размер / 4)
Get-ChildItem -Recurse -File | 
    Where-Object {$_.Extension -notin @('.png','.jpg','.jpeg','.gif','.ico','.svg','.zip','.tar','.gz')} |
    Select-Object Name, Extension,
        @{Name="SizeBytes";Expression={$_.Length}},
        @{Name="EstTokens";Expression={[math]::Round($_.Length / 4)}},
        @{Name="EstTokensK";Expression={[math]::Round($_.Length / 4 / 1024, 1)}} |
    Where-Object {$_.EstTokens -gt 1000} |
    Sort-Object EstTokens -Descending |
    Format-Table -AutoSize
```

## 3. Детальная статистика проекта

```powershell
# Полная статистика проекта
$stats = @{
    TotalFiles = (Get-ChildItem -Recurse -File).Count
    TotalSizeMB = [math]::Round((Get-ChildItem -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
    TotalSizeGB = [math]::Round((Get-ChildItem -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1GB, 2)
    PythonFiles = (Get-ChildItem -Recurse -File -Filter "*.py").Count
    JsonFiles = (Get-ChildItem -Recurse -File -Filter "*.json").Count
    CsvFiles = (Get-ChildItem -Recurse -File -Filter "*.csv").Count
    LogFiles = (Get-ChildItem -Recurse -File -Filter "*.log").Count
}

Write-Host "📊 Project Statistics:" -ForegroundColor Cyan
$stats.GetEnumerator() | ForEach-Object {
    Write-Host "  $($_.Key): $($_.Value)" -ForegroundColor Yellow
}

# Оценка токенов
$totalTokens = [math]::Round((Get-ChildItem -Recurse -File | 
    Where-Object {$_.Extension -notin @('.png','.jpg','.jpeg','.gif','.ico','.svg','.zip','.tar','.gz')} | 
    Measure-Object -Property Length -Sum).Sum / 4 / 1024, 0)

Write-Host "  Estimated Tokens: $totalTokens K" -ForegroundColor Green
```

## 4. Поиск тяжёлых файлов (>1000 токенов)

```powershell
# Файлы с оценкой >1000 токенов (примерно >4KB)
Get-ChildItem -Recurse -File | 
    Where-Object {
        $_.Length -gt 4KB -and 
        $_.Extension -notin @('.png','.jpg','.jpeg','.gif','.ico','.svg','.zip','.tar','.gz','.pyc','.pyo')
    } |
    Select-Object Name, Extension,
        @{Name="SizeKB";Expression={[math]::Round($_.Length / 1KB, 2)}},
        @{Name="EstTokens";Expression={[math]::Round($_.Length / 4)}},
        @{Name="RelativePath";Expression={$_.FullName.Replace((Get-Location).Path + '\', '')}} |
    Sort-Object EstTokens -Descending |
    Format-Table -AutoSize
```

## 5. Экспорт в CSV для анализа

```powershell
# Экспорт всех файлов в CSV
Get-ChildItem -Recurse -File | 
    Select-Object Name, Extension, 
        @{Name="SizeBytes";Expression={$_.Length}},
        @{Name="SizeKB";Expression={[math]::Round($_.Length / 1KB, 2)}},
        @{Name="EstTokens";Expression={[math]::Round($_.Length / 4)}},
        @{Name="RelativePath";Expression={$_.FullName.Replace((Get-Location).Path + '\', '')}} |
    Export-Csv -Path "project_files.csv" -NoTypeInformation -Encoding UTF8

Write-Host "✅ Exported to project_files.csv" -ForegroundColor Green
```

## 6. Быстрая команда (всё в одном)

```powershell
# Однострочник для быстрой диагностики
Write-Host "`n📊 Project Analysis`n" -ForegroundColor Cyan; 
$files = Get-ChildItem -Recurse -File; 
$totalSize = ($files | Measure-Object -Property Length -Sum).Sum; 
Write-Host "Total Files: $($files.Count)" -ForegroundColor Yellow; 
Write-Host "Total Size: $([math]::Round($totalSize / 1MB, 2)) MB" -ForegroundColor Yellow; 
Write-Host "Est. Tokens: $([math]::Round($totalSize / 4 / 1024, 0)) K`n" -ForegroundColor Green; 
Write-Host "Top extensions by size:" -ForegroundColor Cyan; 
$files | Group-Object Extension | 
    Select-Object @{N='Ext';E={$_.Name}}, 
        @{N='Files';E={$_.Count}}, 
        @{N='SizeMB';E={[math]::Round(($_.Group | Measure-Object Length -Sum).Sum / 1MB, 2)}} | 
    Sort-Object SizeMB -Descending | 
    Select-Object -First 10 | 
    Format-Table -AutoSize
```

