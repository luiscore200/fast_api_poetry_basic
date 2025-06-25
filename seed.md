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







Instrucciones para Generación de Artículos por Grupos de Tres Categorías
Para futuras solicitudes, por favor, utiliza el siguiente formato:

"Genera 12 artículos por cada bloque de 3 categorías consecutivas, siguiendo este patrón:

1 artículo individual por cada categoría del bloque.

2 artículos que combinen la categoría actual con su siguiente vecina.

2 artículos que combinen la categoría siguiente con la tercera categoría del bloque.

2 artículos que combinen la categoría actual con la tercera categoría del bloque.

3 artículos que combinen las tres categorías del bloque.

Cada artículo debe tener un título, un contenido de 300 palabras, y el campo categories: [] con las categorías correspondientes. Continúa con los siguientes 3 hasta completar la lista, eliminando del prompt las categorías ya procesadas."



