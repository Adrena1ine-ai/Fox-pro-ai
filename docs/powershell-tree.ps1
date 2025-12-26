# Простой вывод структуры проекта
Get-ChildItem -Recurse -Depth 2 | 
    Where-Object {$_.PSIsContainer -or $_.Extension} | 
    Select-Object @{N='Type';E={if($_.PSIsContainer){'📁'}else{'📄'}}}, 
        @{N='Name';E={if($_.PSIsContainer){$_.Name}else{"$($_.Name)$($_.Extension)"}}}, 
        @{N='Path';E={$_.FullName.Replace((Get-Location).Path + '\', '')}} | 
    Format-Table -AutoSize

