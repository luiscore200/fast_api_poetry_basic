usar en el directorio de los archivos... por ejemplo mock/articles.json, abrir powershell alli y ejecutar

$articles = Get-Content .\articles.json -Encoding UTF8 | Out-String | ConvertFrom-Json
$counter = 1

foreach ($article in $articles) {
    $json = $article | ConvertTo-Json -Depth 5
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)

    Write-Host ""
    Write-Host "Enviando artículo #$($counter): $($article.title)"

    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/articles" `
                                      -Method POST `
                                      -Body $bytes `
                                      -ContentType "application/json"

        $numChunks = $response.data.chunks.Count
        Write-Host "✅ Procesado correctamente. Chunks generados: $numChunks"
    }
    catch {
        Write-Host "❌ Error al enviar artículo #$($counter):"
        Write-Host $_.Exception.Message
    }

    Write-Host "⏳ Esperando 5 segundos..."
    Start-Sleep -Seconds 5
    $counter++
}
